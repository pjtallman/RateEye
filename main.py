import logging
import os
import shutil
import json
from datetime import datetime
from typing import Optional
from enum import Enum

# Check if we are running in a test environment
IS_TESTING = (
    "pytest" in os.environ.get("PYTEST_CURRENT_TEST", "")
    or "PYTEST_VERSION" in os.environ
)

SECRET_KEY = os.environ.get("SECRET_KEY", "a-very-secret-key-for-development")
if IS_TESTING:
    SECRET_KEY = "a-very-secret-key-for-development"

from fastapi import FastAPI, Request, Form, Header, Depends, HTTPException, status, File, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext
from authlib.integrations.starlette_client import OAuth

# Local Imports
from i18n import get_text
from database import User, UserSetting, SystemSetting, Role, user_roles, engine, SessionLocal, get_db, init_db, get_system_setting, PageType, Permission, PermissionLevel, get_pages

# --- 1. LOGGING & ENVIRONMENT SETUP ---
LOG_DIR = "logs"
ACTIVE_LOG = os.path.join(LOG_DIR, "RateEye.log")

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
else:
    # During tests, conftest handles most logging, but let's ensure this logger can output
    logging.getLogger(__name__).setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

# Initialize database
if not IS_TESTING:
    init_db()

# --- 3. AUTH & SECURITY SETUP ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def get_current_user(request: Request, db: Session = Depends(get_db)):
    logger.debug(f"Session content: {dict(request.session)}")
    user_id = request.session.get("user_id")
    if not user_id:
        logger.debug("No user_id in session")
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
    # Ensure user is authorized
    if not user.is_authorized:
        t = get_text(request.headers.get("accept-language"))
        logger.warning(f"User {user.email} is not authorized.")
        raise HTTPException(status_code=403, detail=t.get("err_user_not_authorized"))
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


@app.get("/", response_class=HTMLResponse, tags=[PageType.INFO])
async def read_root(
    request: Request,
    accept_language: str = Header(None),
    user: Optional[User] = Depends(get_current_user),
):
    if not user:
        logger.info("Unauthenticated user at root. Redirecting to /login.")
        return RedirectResponse(url="/login", status_code=303)
    
    if user.force_password_change:
        logger.info(f"User {user.email} must change password. Redirecting to /change-password.")
        return RedirectResponse(url="/change-password", status_code=303)

    t = get_text(accept_language)
    logger.info(f"Authenticated user {user.email} at root. Rendering home page.")
    return templates.TemplateResponse(request, "index.html", {"t": t, "user": user})


@app.get("/register", response_class=HTMLResponse, tags=[PageType.INFO])
async def register_page(request: Request, accept_language: str = Header(None)):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "register.html", {"t": t})


@app.post("/register", tags=[PageType.INFO])
async def register_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    accept_language: str = Header(None),
    db: Session = Depends(get_db),
):
    # Check if username exists
    if db.query(User).filter(User.username == username).first():
        t = get_text(accept_language)
        return templates.TemplateResponse(
            request, "register.html", {"t": t, "error": t.get("err_username_taken")}
        )
    # Check if email exists
    if db.query(User).filter(User.email == email).first():
        t = get_text(accept_language)
        return templates.TemplateResponse(
            request, "register.html", {"t": t, "error": t.get("err_email_registered")}
        )
    hashed_password = get_password_hash(password)
    new_user = User(username=username, email=email, hashed_password=hashed_password, is_authorized=True)
    db.add(new_user)
    db.commit()
    logger.info(f"New user registered: {username} ({email})")
    return RedirectResponse(url="/login", status_code=303)


@app.get("/forgot-password", response_class=HTMLResponse, tags=[PageType.INFO])
async def forgot_password_page(request: Request, accept_language: str = Header(None)):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "forgot_password.html", {"t": t})


@app.post("/forgot-password", tags=[PageType.INFO])
async def forgot_password(request: Request, email: str = Form(...), accept_language: str = Header(None)):
    t = get_text(accept_language)
    logger.info(f"Password reset requested for: {email}")
    return HTMLResponse(content=f"<p>{t.get('msg_forgot_pw_sent')}</p><a href='/login'>{t.get('btn_back')}</a>")


@app.get("/login", response_class=HTMLResponse, tags=[PageType.INFO])
async def login_page(request: Request, accept_language: str = Header(None), error: str = None):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "login.html", {"t": t, "error": error})


@app.post("/login", tags=[PageType.INFO])
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    remember_me: bool = Form(False),
    accept_language: str = Header(None),
    db: Session = Depends(get_db),
):
    # Try to find by email or username
    user = db.query(User).filter((User.email == email) | (User.username == email)).first()
    if not user or not verify_password(password, user.hashed_password):
        t = get_text(accept_language)
        return templates.TemplateResponse(
            request, "login.html", {"t": t, "error": t.get("err_invalid_login")}
        )
    request.session["user_id"] = user.id
    logger.info("Login successful. Setting session.")
    db.commit() # Ensure session or changes are saved
    logger.info(f"User logged in: {user.email} (ID: {user.id}, Session: {dict(request.session)})")
    
    if user.force_password_change:
        logger.info(f"User {user.email} must change password. Redirecting to /change-password.")
        return RedirectResponse(url="/change-password", status_code=303)
    
    return RedirectResponse(url="/", status_code=303)


@app.get("/logout", tags=[PageType.INFO])
async def logout(request: Request):
    request.session.clear()
    logger.info("User logged out")
    return RedirectResponse(url="/", status_code=303)


@app.get("/settings/user", response_class=HTMLResponse, tags=[PageType.SETTINGS])
async def user_settings_page(
    request: Request,
    accept_language: str = Header(None),
    user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    t = get_text(accept_language)
    logger.info(f"User settings page accessed by {user.email}.")
    return templates.TemplateResponse(
        request, "user_settings.html", {"t": t, "user": user}
    )


@app.get("/settings/user/change-username", response_class=HTMLResponse, tags=[PageType.SETTINGS])
async def user_change_username_page(
    request: Request,
    accept_language: str = Header(None),
    user: User = Depends(login_required),
):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "user_change_username.html", {"t": t, "user": user})


@app.post("/settings/user/change-username", tags=[PageType.SETTINGS])
async def user_change_username(
    request: Request,
    new_username: str = Form(...),
    accept_language: str = Header(None),
    user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    # Check if username exists
    if db.query(User).filter(User.username == new_username).first():
        t = get_text(accept_language)
        return templates.TemplateResponse(
            request, "user_change_username.html", {"t": t, "user": user, "error": t.get("err_username_taken")}
        )

    old_username = user.username
    user.username = new_username
    db.commit()
    logger.info(f"User {user.email} changed username from {old_username} to {new_username}")
    return RedirectResponse(url="/settings/user", status_code=303)


@app.get("/settings/user/change-password", response_class=HTMLResponse, tags=[PageType.SETTINGS])
async def user_change_password_page(
    request: Request,
    accept_language: str = Header(None),
    user: User = Depends(login_required),
):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "user_change_password.html", {"t": t, "user": user})


@app.post("/settings/user/change-password", tags=[PageType.SETTINGS])
async def user_change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    accept_language: str = Header(None),
    user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    if not verify_password(current_password, user.hashed_password):
        t = get_text(accept_language)
        return templates.TemplateResponse(
            request, "user_change_password.html", {"t": t, "user": user, "error": t.get("err_current_password_incorrect")}
        )
    
    if new_password != confirm_password:
        t = get_text(accept_language)
        return templates.TemplateResponse(
            request, "user_change_password.html", {"t": t, "user": user, "error": t.get("err_passwords_mismatch")}
        )
    
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    logger.info(f"User {user.email} changed their password voluntarily.")
    return RedirectResponse(url="/settings/user", status_code=303)


@app.post("/settings/user/upload-photo", tags=[PageType.SETTINGS])
async def upload_photo(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    # Ensure it is an image
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Create safe filename
    ext = os.path.splitext(file.filename)[1]
    filename = f"user_{user.id}{ext}"
    filepath = os.path.join("static", "uploads", "profile_photos", filename)

    # Save file
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Update DB
    user.photo_url = f"/static/uploads/profile_photos/{filename}"
    db.commit()

    logger.info(f"User {user.email} uploaded a new profile photo: {user.photo_url}")
    return RedirectResponse(url="/settings/user", status_code=303)


@app.get("/settings/system", response_class=HTMLResponse, tags=[PageType.SETTINGS])
async def system_settings_page(
    request: Request,
    accept_language: str = Header(None),
    user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    # Future: check for admin permissions here
    t = get_text(accept_language)
    line_count = get_system_setting(db, "log_lines", "100")
    logger.info(f"System settings page accessed by {user.email}.")
    return templates.TemplateResponse(
        request, "system_settings.html", {"t": t, "line_count": line_count, "user": user}
    )


@app.post("/settings/system", tags=[PageType.SETTINGS])
async def save_system_settings(
    log_lines: str = Form(...), 
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    # Future: check for admin permissions here
    setting = db.query(SystemSetting).filter(SystemSetting.name == "log_lines").first()
    if setting:
        setting.value = log_lines
    else:
        db.add(SystemSetting(name="log_lines", value=log_lines))
    db.commit()
    logger.info(f"System settings saved by {user.email}. New log_lines limit: {log_lines}")
    return RedirectResponse(url="/settings/system", status_code=303)


@app.get("/show-log", response_class=PlainTextResponse, tags=[PageType.INFO])
async def show_log(request: Request, accept_language: str = Header(None), user: User = Depends(login_required), db: Session = Depends(get_db)):
    line_limit = int(get_system_setting(db, "log_lines", "100"))
    if os.path.exists(ACTIVE_LOG):
        with open(ACTIVE_LOG, "r") as f:
            lines = f.readlines()
            content = "".join(lines[-line_limit:])
        return content
    t = get_text(accept_language)
    return t.get("err_no_log_found")


@app.get("/about", response_class=HTMLResponse, tags=[PageType.INFO])
async def about_page(
    request: Request,
    accept_language: str = Header(None),
    db: Session = Depends(get_db)
):
    t = get_text(accept_language)
    version = get_system_setting(db, "version", "Unknown")
    return templates.TemplateResponse(request, "about.html", {"t": t, "version": version})


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
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "user:email"},
)


@app.get("/auth/login/{provider}", tags=[PageType.INFO])
async def auth_login(provider: str, request: Request):
    # Determine protocol based on request, handle local dev
    redirect_uri = str(request.url_for("auth_callback", provider=provider))
    
    # Ensure redirect_uri uses https if the app is configured for it or if it's not localhost
    if "127.0.0.1" not in redirect_uri and "localhost" not in redirect_uri:
        if not redirect_uri.startswith("https://"):
            redirect_uri = redirect_uri.replace("http://", "https://")
    
    logger.info(f"Redirecting to {provider} with redirect_uri: {redirect_uri}")
    return await oauth.create_client(provider).authorize_redirect(request, redirect_uri)


@app.get("/auth/callback/{provider}", tags=[PageType.INFO])
async def auth_callback(provider: str, request: Request, db: Session = Depends(get_db)):
    client = oauth.create_client(provider)
    try:
        token = await client.authorize_access_token(request)
    except Exception as e:
        logger.error(f"OAuth error: {e}")
        return RedirectResponse(url="/login?error=OAuth+authentication+failed")
        
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
            username=email.split("@")[0], # Fallback username
            email=email,
            provider=provider,
            profile_json=json.dumps(user_data),
            is_authorized=True, # Assuming OAuth users are authorized
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update profile if it changed
        user.profile_json = json.dumps(user_data)
        db.commit()

    request.session["user_id"] = user.id
    logger.info(f"User logged in via {provider}: {email}")
    return RedirectResponse(url="/", status_code=303)


@app.get("/change-password", response_class=HTMLResponse, tags=[PageType.INFO])
async def change_password_page(
    request: Request,
    accept_language: str = Header(None),
    user: User = Depends(login_required),
):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "change_password.html", {"t": t, "user": user})


@app.post("/change-password", tags=[PageType.INFO])
async def change_password(
    request: Request,
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    accept_language: str = Header(None),
    user: User = Depends(login_required),
    db: Session = Depends(get_db),
):
    if new_password != confirm_password:
        t = get_text(accept_language)
        return templates.TemplateResponse(
            request, "change_password.html", {"t": t, "user": user, "error": t.get("err_passwords_mismatch")}
        )
    
    user.hashed_password = get_password_hash(new_password)
    user.force_password_change = False
    db.commit()
    logger.info(f"Password changed for user: {user.email}")
    return RedirectResponse(url="/", status_code=303)


# --- 8. ADMIN & USER MANAGEMENT ---

@app.get("/admin/users", response_class=HTMLResponse, tags=[PageType.MAINTENANCE])
async def list_users(
    request: Request,
    accept_language: str = Header(None),
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    # In a real app, you'd check if user is an admin
    t = get_text(accept_language)
    users = db.query(User).all()
    return templates.TemplateResponse(request, "admin_users.html", {"t": t, "users": users, "user": user})


@app.post("/admin/users/force-password-change/{user_id}", tags=[PageType.MAINTENANCE])
async def admin_force_password_change(
    user_id: int,
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user:
        target_user.force_password_change = not target_user.force_password_change
        db.commit()
        status_msg = "forced" if target_user.force_password_change else "cleared"
        logger.info(f"Password change {status_msg} for user {target_user.email} by {user.email}")
    
    return RedirectResponse(url="/admin/users", status_code=303)


@app.post("/admin/users/update/{user_id}", tags=[PageType.MAINTENANCE])
async def update_user(
    user_id: int,
    email: str = Form(...),
    force_password_change: bool = Form(False),
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user:
        existing_user = db.query(User).filter(User.email == email, User.id != user_id).first()
        if existing_user:
             logger.warning(f"Admin {user.email} tried to change user {user_id} email to already taken {email}")
             return RedirectResponse(url="/admin/users", status_code=303)
             
        target_user.email = email
        target_user.force_password_change = force_password_change
        db.commit()
        logger.info(f"User {target_user.username} updated by {user.email}: email={email}, force_password_change={force_password_change}")
    
    return RedirectResponse(url="/admin/users", status_code=303)


@app.get("/admin/role", tags=[PageType.MAINTENANCE])
async def redirect_to_roles():
    return RedirectResponse(url="/admin/roles", status_code=303)


@app.get("/admin/roles", response_class=HTMLResponse, tags=[PageType.MAINTENANCE])
async def list_roles(
    request: Request,
    accept_language: str = Header(None),
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    t = get_text(accept_language)
    roles = db.query(Role).all()
    all_users = db.query(User).all()
    return templates.TemplateResponse(request, "admin_roles.html", {
        "t": t, 
        "roles": roles, 
        "user": user,
        "all_users": all_users
    })

@app.post("/admin/roles/create", tags=[PageType.MAINTENANCE])
async def create_role(
    name: str = Form(...),
    description: str = Form(""),
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    new_role = Role(name=name, description=description)
    db.add(new_role)
    db.commit()
    logger.info(f"Role '{name}' created by {user.email}")
    return RedirectResponse(url="/admin/roles", status_code=303)

@app.post("/admin/roles/update/{role_id}", tags=[PageType.MAINTENANCE])
async def update_role(
    role_id: int,
    name: str = Form(...),
    description: str = Form(""),
    user_ids: Optional[str] = Form(None),
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if role:
        role.name = name
        role.description = description
        if user_ids is not None:
            role.users = []
            if user_ids.strip():
                id_list = [int(id_str) for id_str in user_ids.split(",") if id_str.strip()]
                users_to_add = db.query(User).filter(User.id.in_(id_list)).all()
                role.users.extend(users_to_add)
        db.commit()
        logger.info(f"Role '{name}' updated by {user.email}")
    return RedirectResponse(url="/admin/roles", status_code=303)

@app.post("/admin/roles/delete/{role_id}", tags=[PageType.MAINTENANCE])
async def delete_role(
    role_id: int,
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if role:
        if role.name in ["Admin", "User"]:
             return RedirectResponse(url="/admin/roles", status_code=303)
        db.delete(role)
        db.commit()
        logger.info(f"Role '{role.name}' deleted by {user.email}")
    return RedirectResponse(url="/admin/roles", status_code=303)


@app.post("/admin/users/delete/{user_id}", tags=[PageType.MAINTENANCE])
async def delete_user(
    user_id: int,
    request: Request,
    accept_language: str = Header(None),
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    if user.id == user_id:
        t = get_text(accept_language)
        raise HTTPException(status_code=400, detail=t.get("err_cannot_delete_self"))
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user:
        target_user.roles = []
        db.delete(target_user)
        db.commit()
        logger.info(f"User {target_user.email} deleted by {user.email}")
    return RedirectResponse(url="/admin/users", status_code=303)

@app.get("/admin/securities", response_class=HTMLResponse, tags=[PageType.MAINTENANCE])
async def maintenance_securities(request: Request, accept_language: str = Header(None), user: User = Depends(login_required)):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "admin_securities.html", {"t": t, "user": user})

@app.get("/admin/permissions", response_class=HTMLResponse, tags=[PageType.MAINTENANCE])
async def list_permissions(
    request: Request,
    accept_language: str = Header(None),
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    t = get_text(accept_language)
    permissions = db.query(Permission).all()
    roles = db.query(Role).all()
    users = db.query(User).all()
    pages = get_pages()
    
    # Create a map of path -> label
    page_labels = {path: t.get(label_key, path) for path, pt, label_key in pages}

    # Grouping structure: { PageType: { page_path: { "label": str, "subjects": { subject_key: [levels] } } } }
    grouped = {}
    for pt in PageType:
        grouped[pt] = {}
        # Pre-populate pages for this type
        for path, p_type, label_key in pages:
            if p_type == pt:
                grouped[pt][path] = {
                    "label": t.get(label_key, path),
                    "subjects": {}
                }

    for p in permissions:
        pt = p.page_type
        path = p.page_path
        if pt not in grouped: grouped[pt] = {}
        if path not in grouped[pt]: 
            grouped[pt][path] = {
                "label": page_labels.get(path, path),
                "subjects": {}
            }
        
        subject_key = f"role:{p.role_id}" if p.role_id else f"user:{p.user_id}"
        if subject_key not in grouped[pt][path]["subjects"]:
            grouped[pt][path]["subjects"][subject_key] = {
                "role": p.role,
                "user": p.user,
                "permissions": []
            }
        grouped[pt][path]["subjects"][subject_key]["permissions"].append(p)
        
    return templates.TemplateResponse(
        request, 
        "admin_permissions.html", 
        {
            "t": t, 
            "user": user, 
            "grouped": grouped,
            "roles": roles,
            "users": users,
            "page_types": list(PageType),
            "permission_levels": list(PermissionLevel)
        }
    )

@app.post("/admin/permissions/create", tags=[PageType.MAINTENANCE])
async def create_permission(
    page_path: str = Form(...),
    subject: str = Form(...), # Format: "role:ID" or "user:ID"
    level: PermissionLevel = Form(...),
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    subject_type, subject_id = subject.split(":")
    role_id = int(subject_id) if subject_type == "role" else None
    user_id = int(subject_id) if subject_type == "user" else None
    
    # Find page type for this path
    page_type = next((pt for path, pt in get_pages() if path == page_path), PageType.INFO)

    # Exclusivity Logic
    if level in [PermissionLevel.FULL, PermissionLevel.NONE]:
        # Delete ALL existing permissions for this (subject, page)
        db.query(Permission).filter(
            Permission.page_path == page_path,
            Permission.role_id == role_id,
            Permission.user_id == user_id
        ).delete()
        # Add the new one
        new_perm = Permission(page_path=page_path, page_type=page_type, role_id=role_id, user_id=user_id, level=level)
        db.add(new_perm)
    else:
        # CRUD levels
        # 1. Delete FULL or NONE if they exist
        db.query(Permission).filter(
            Permission.page_path == page_path,
            Permission.role_id == role_id,
            Permission.user_id == user_id,
            Permission.level.in_([PermissionLevel.FULL, PermissionLevel.NONE])
        ).delete()
        
        # 2. Add this level if not already present
        existing = db.query(Permission).filter(
            Permission.page_path == page_path,
            Permission.role_id == role_id,
            Permission.user_id == user_id,
            Permission.level == level
        ).first()
        if not existing:
            new_perm = Permission(page_path=page_path, page_type=page_type, role_id=role_id, user_id=user_id, level=level)
            db.add(new_perm)
    
    db.commit()
    logger.info(f"Permission updated for {subject} on {page_path} to include {level} by {user.email}")
    return RedirectResponse(url="/admin/permissions", status_code=303)

@app.post("/admin/permissions/delete-subject", tags=[PageType.MAINTENANCE])
async def delete_subject_permissions(
    page_path: str = Form(...),
    subject: str = Form(...), # Format: "role:ID" or "user:ID"
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    subject_type, subject_id = subject.split(":")
    role_id = int(subject_id) if subject_type == "role" else None
    user_id = int(subject_id) if subject_type == "user" else None

    # Delete all
    db.query(Permission).filter(
        Permission.page_path == page_path,
        Permission.role_id == role_id,
        Permission.user_id == user_id
    ).delete()
    
    # User requirement: MUST have at least one permission.
    # If we deleted all, reset to NONE.
    page_type = next((pt for path, pt in get_pages() if path == page_path), PageType.INFO)
    new_perm = Permission(page_path=page_path, page_type=page_type, role_id=role_id, user_id=user_id, level=PermissionLevel.NONE)
    db.add(new_perm)
    
    db.commit()
    logger.info(f"Permissions cleared (reset to NONE) for {subject} on {page_path} by {user.email}")
    return RedirectResponse(url="/admin/permissions", status_code=303)

@app.post("/admin/permissions/delete/{perm_id}", tags=[PageType.MAINTENANCE])
async def delete_permission(
    perm_id: int,
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    perm = db.query(Permission).filter(Permission.id == perm_id).first()
    if perm:
        path = perm.page_path
        role_id = perm.role_id
        user_id = perm.user_id
        
        db.delete(perm)
        db.commit()
        
        # Check if any left for this (subject, page)
        count = db.query(Permission).filter(
            Permission.page_path == path,
            Permission.role_id == role_id,
            Permission.user_id == user_id
        ).count()
        
        if count == 0:
            # Add NONE
            page_type = next((pt for p_path, pt in get_pages() if p_path == path), PageType.INFO)
            db.add(Permission(page_path=path, page_type=page_type, role_id=role_id, user_id=user_id, level=PermissionLevel.NONE))
            db.commit()

        logger.info(f"Permission {perm_id} deleted by {user.email}")
    return RedirectResponse(url="/admin/permissions", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
