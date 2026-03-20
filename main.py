import logging
import os
import shutil
import json
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Request, Form, Header, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, String, Integer, Boolean, Text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext
from authlib.integrations.starlette_client import OAuth

# Local Imports
from i18n import get_text

# --- 1. LOGGING & ENVIRONMENT SETUP ---
LOG_DIR = "logs"
ACTIVE_LOG = os.path.join(LOG_DIR, "RateEye.log")
SECRET_KEY = os.environ.get("SECRET_KEY", "a-very-secret-key-for-development")

# Check if we are running in a test environment
IS_TESTING = (
    "pytest" in os.environ.get("PYTEST_CURRENT_TEST", "")
    or "PYTEST_VERSION" in os.environ
)

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


def rotate_logs():
    """Rotates the production log file daily. Skipped during unit tests."""
    if IS_TESTING:
        return

    today_str = datetime.now().strftime("%Y%m%d")
    archive_name = os.path.join(LOG_DIR, f"{today_str}_RateEye.log")
    if os.path.exists(ACTIVE_LOG):
        if not os.path.exists(archive_name):
            shutil.copy(ACTIVE_LOG, archive_name)
            with open(ACTIVE_LOG, "w") as f:
                f.write(f"--- Log Rotated/Started at {datetime.now()} ---\n")


rotate_logs()

if not IS_TESTING:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(ACTIVE_LOG), logging.StreamHandler()],
    )

logger = logging.getLogger(__name__)

# --- 2. DATABASE SETUP ---
DATABASE_URL = "sqlite:///./rateeye.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Setting(Base):
    __tablename__ = "settings"
    name = Column(String, primary_key=True, index=True)
    value = Column(String)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True)
    is_authorized = Column(Boolean, default=False)
    provider = Column(String, default="local")
    profile_json = Column(Text, nullable=True)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_setting(name: str, default: str):
    db = SessionLocal()
    res = db.query(Setting).filter(Setting.name == name).first()
    db.close()
    return res.value if res else default


# --- 3. AUTH & SECURITY SETUP ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"Session user_id {user_id} not found in database. Clearing session.")
        request.session.clear()
        return None
    return user


def login_required(user: Optional[User] = Depends(get_current_user)):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Cookie"},
        )
    return user


# --- 4. APP SETUP ---
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=86400)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# --- 5. LOCALIZATION FILTERS ---
def format_num(value, lang_code="en"):
    """
    Format numbers based on locale.
    US: 1,234.56
    ES: 1.234,56
    """
    try:
        formatted = "{:,.2f}".format(float(value))
        if lang_code and lang_code.startswith("es"):
            # Swap comma and dot using temporary placeholder 'X'
            return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except (ValueError, TypeError) as e:
        logger.error(f"Formatting error: {e}")
        return value


templates.env.filters["format_num"] = format_num

# --- 6. ROUTES ---


@app.get("/", response_class=HTMLResponse)
async def read_root(
    request: Request,
    accept_language: str = Header(None),
    user: Optional[User] = Depends(get_current_user),
):
    if not user:
        logger.info("Unauthenticated user at root. Redirecting to /login.")
        return RedirectResponse(url="/login", status_code=303)
    t = get_text(accept_language)
    logger.info(f"Authenticated user {user.email} at root. Rendering home page.")
    return templates.TemplateResponse(request, "index.html", {"t": t, "user": user})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, accept_language: str = Header(None)):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "register.html", {"t": t})


@app.post("/register")
async def register_user(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    db_user = db.query(User).filter(User.email == email).first()
    if db_user:
        return "Email already registered"  # Simplified for now
    hashed_password = get_password_hash(password)
    new_user = User(email=email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    logger.info(f"New user registered: {email}")
    return RedirectResponse(url="/login", status_code=303)


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request, accept_language: str = Header(None)):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "forgot_password.html", {"t": t})


@app.post("/forgot-password")
async def forgot_password(email: str = Form(...)):
    logger.info(f"Password reset requested for: {email}")
    return "If an account exists with this email, you will receive a reset link shortly."


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, accept_language: str = Header(None)):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "login.html", {"t": t})


@app.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    remember_me: bool = Form(False),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return "Invalid email or password"  # Simplified for now
    request.session["user_id"] = user.id
    # Note: max_age is handled by middleware, but we could use remember_me 
    # logic here if we had dynamic max_age support.
    logger.info(f"User logged in: {email} (remember_me={remember_me})")
    return RedirectResponse(url="/", status_code=303)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    logger.info("User logged out")
    return RedirectResponse(url="/", status_code=303)


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    accept_language: str = Header(None),
    user: User = Depends(login_required),
):
    t = get_text(accept_language)
    line_count = get_setting("log_lines", "100")
    logger.info("Settings page accessed.")
    return templates.TemplateResponse(
        request, "settings.html", {"t": t, "line_count": line_count, "user": user}
    )


@app.post("/settings")
async def save_settings(
    log_lines: str = Form(...), user: User = Depends(login_required)
):
    db = SessionLocal()
    setting = db.query(Setting).filter(Setting.name == "log_lines").first()
    if setting:
        setting.value = log_lines
    else:
        db.add(Setting(name="log_lines", value=log_lines))
    db.commit()
    db.close()
    logger.info(f"Settings saved. New log_lines limit: {log_lines}")
    return RedirectResponse(url="/", status_code=303)


@app.get("/show-log", response_class=PlainTextResponse)
async def show_log(user: User = Depends(login_required)):
    line_limit = int(get_setting("log_lines", "100"))
    if os.path.exists(ACTIVE_LOG):
        with open(ACTIVE_LOG, "r") as f:
            lines = f.readlines()
            content = "".join(lines[-line_limit:])
        return content
    return "No log file found."


# --- 7. OAUTH2 SETUP ---
oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID", "google-client-id"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", "google-client-secret"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

oauth.register(
    name="github",
    client_id=os.environ.get("GITHUB_CLIENT_ID", "github-client-id"),
    client_secret=os.environ.get("GITHUB_CLIENT_SECRET", "github-client-secret"),
    access_token_url="https://github.com/login/oauth/access_token",
    access_token_params=None,
    authorize_url="https://github.com/login/oauth/authorize",
    authorize_params=None,
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "user:email"},
)


@app.get("/auth/login/{provider}")
async def auth_login(provider: str, request: Request):
    # Determine protocol based on request, handle local dev
    scheme = "https" if request.url.scheme == "https" else "http"
    redirect_uri = request.url_for("auth_callback", provider=provider)
    # Force use of http for local development if not behind proxy
    if "127.0.0.1" in str(redirect_uri) or "localhost" in str(redirect_uri):
         redirect_uri = str(redirect_uri).replace("https://", "http://")
    
    return await oauth.create_client(provider).authorize_redirect(request, redirect_uri)


@app.get("/auth/callback/{provider}")
async def auth_callback(provider: str, request: Request, db: Session = Depends(get_db)):
    client = oauth.create_client(provider)
    try:
        token = await client.authorize_access_token(request)
    except Exception as e:
        logger.error(f"OAuth error: {e}")
        return RedirectResponse(url="/login")
        
    user_data = token.get("userinfo")
    if not user_data:
        # For GitHub, we might need a separate call
        resp = await client.get("user", token=token)
        user_data = resp.json()

    email = user_data.get("email")
    if not email and provider == "github":
        # GitHub might not return email in basic profile
        resp = await client.get("user/emails", token=token)
        emails = resp.json()
        email = next(e["email"] for e in emails if e["primary"])["email"]

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            provider=provider,
            profile_json=json.dumps(user_data),
            is_authorized=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    request.session["user_id"] = user.id
    logger.info(f"User logged in via {provider}: {email}")
    return RedirectResponse(url="/", status_code=303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
