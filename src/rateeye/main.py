import logging
import os
import shutil
import json
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
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
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext
from authlib.integrations.starlette_client import OAuth

# Local Imports
from .i18n import get_text
from .database import (
    User, UserSetting, SystemSetting, Role, user_roles, engine, SessionLocal, 
    get_db, init_db, get_system_setting, PageType, Permission, PermissionLevel, 
    get_pages, Security, SecurityType, AssetClass
)
from .securities.endpoints import YahooScraperEndpoint, FinnhubEndpoint, AlphaVantageEndpoint

# --- 1. LOGGING & ENVIRONMENT SETUP ---
LOG_DIR = os.environ.get("LOG_DIR", "logs")
ACTIVE_LOG = os.path.join(LOG_DIR, "RateEye.log")
STARTUP_LOG = os.path.join(LOG_DIR, "startup.log")

# Get the base directory of the package
BASE_DIR = os.path.dirname(__file__)

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Initialize Startup Logging
if not IS_TESTING:
    # Rotate old startup log before clearing if it exists
    if os.path.exists(STARTUP_LOG):
        today_str = datetime.now().strftime("%Y%m%d")
        archive_name = os.path.join(LOG_DIR, f"{today_str}_startup.log")
        if not os.path.exists(archive_name):
            shutil.copy(STARTUP_LOG, archive_name)
    
    with open(STARTUP_LOG, "w") as f:
        f.write(f"--- RateEye Startup at {datetime.now()} ---\n")
    
    startup_handler = logging.FileHandler(STARTUP_LOG)
    startup_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(startup_handler)
    root_logger.addHandler(logging.StreamHandler())

logger = logging.getLogger(__name__)

def rotate_logs():
    """Rotates the production log files daily. Skipped during unit tests."""
    if IS_TESTING: return
    today_str = datetime.now().strftime("%Y%m%d")
    for active, suffix in [(ACTIVE_LOG, "RateEye.log"), (STARTUP_LOG, "startup.log")]:
        archive = os.path.join(LOG_DIR, f"{today_str}_{suffix}")
        if os.path.exists(active) and not os.path.exists(archive):
            shutil.copy(active, archive)
            with open(active, "w") as f: f.write(f"--- Log Rotated at {datetime.now()} ---\n")

def cleanup_logs(db: Session):
    """Deletes old log archives based on system retention settings."""
    if IS_TESTING: return
    app_days = int(get_system_setting(db, "app_log_retention", "10"))
    start_days = int(get_system_setting(db, "startup_log_retention", "10"))
    now = datetime.now()
    for filename in os.listdir(LOG_DIR):
        if not filename.endswith(".log") or "_" not in filename: continue
        try:
            date_str = filename.split("_")[0]
            file_date = datetime.strptime(date_str, "%Y%m%d")
            diff = (now - file_date).days
            if ("RateEye.log" in filename and diff >= app_days) or ("startup.log" in filename and diff >= start_days):
                os.remove(os.path.join(LOG_DIR, filename))
                logger.info(f"Deleted old log: {filename}")
        except Exception as e: logger.error(f"Error cleaning {filename}: {e}")


def finalize_logging():
    """Switches from startup log to the main application log."""
    if IS_TESTING:
        return
    
    root_logger = logging.getLogger()
    # Remove startup handler
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename.endswith("startup.log"):
            root_logger.removeHandler(handler)
            handler.close()
            
    # Add application log handler
    app_handler = logging.FileHandler(ACTIVE_LOG)
    app_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    root_logger.addHandler(app_handler)
    logger.info("Startup complete. Switching to application log.")


def load_metadata(activity_name: str, model_class=None) -> dict:
    """Loads metadata for a maintenance activity."""
    metadata_dir = os.path.join(BASE_DIR, "metadata")
    paths = [
        os.path.join(metadata_dir, f"{activity_name}_maint_activity_metadata.json"),
        os.path.join(metadata_dir, f"{activity_name}.json")
    ]
    for path in paths:
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
    
    # Fallback to model-derived defaults
    if model_class:
        from sqlalchemy import inspect
        columns = [c.key for c in inspect(model_class).mapper.column_attrs if c.key != 'id']
        return {
            "browse_panel": {
                "columns": [{"name": c, "label_key": f"th_{c}"} for c in columns]
            },
            "maintenance_panel": {
                "buttons": ["new", "edit", "delete"],
                "fields": [{"name": c, "label_key": f"label_{c}", "read_only": False} for c in columns]
            }
        }
    return {}

def get_security_endpoint(db: Session):
    """Factory to get the active security data endpoint based on system settings."""
    endpoint_type = get_system_setting(db, "security_data_endpoint", "yahoo")
    api_key = get_system_setting(db, "security_data_api_key", "")
    
    if endpoint_type == "finnhub":
        return FinnhubEndpoint(api_key=api_key)
    elif endpoint_type == "alphavantage":
        return AlphaVantageEndpoint(api_key=api_key)
    else:
        return YahooScraperEndpoint()

def get_activity_categories(db: Session, context: str, t: dict):
    """
    Scans all activity metadata to find categories supported for export/import.
    context: 'user_data' or 'system_data'
    """
    categories = []
    # 1. Add core categories based on context
    if context == "user_data":
        categories.append({"id": "roles", "name": "include_roles", "label": t.get("label_include_roles", "Custom Roles")})
    else: # system_data
        categories.append({"id": "logging", "name": "include_logging", "label": t.get("label_include_logging", "Logging")})
        categories.append({"id": "endpoints", "name": "include_endpoints", "label": t.get("label_include_endpoints", "Endpoints")})
        categories.append({"id": "system_roles", "name": "include_system_roles", "label": t.get("label_include_system_roles", "System Roles")})

    # 2. Scan activity metadata
    metadata_dir = os.path.join(BASE_DIR, "metadata")
    if os.path.exists(metadata_dir):
        for filename in os.listdir(metadata_dir):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(metadata_dir, filename), "r") as f:
                        meta = json.load(f)
                        ei = meta.get("export_import", {})
                        if context == "user_data" and ei.get("supports_user_data"):
                            for cat in ei.get("user_data_categories", []):
                                categories.append({
                                    "id": cat["id"], 
                                    "name": cat["name"], 
                                    "label": t.get(cat["label_key"], cat["id"])
                                })
                        elif context == "system_data" and ei.get("supports_system_data"):
                            for cat in ei.get("system_data_categories", []):
                                categories.append({
                                    "id": cat["id"], 
                                    "name": cat["name"], 
                                    "label": t.get(cat["label_key"], cat["id"])
                                })
                except Exception as e:
                    logger.error(f"Error reading metadata for categories: {filename}: {e}")
    
    return categories

rotate_logs()

# Initialize database
if not IS_TESTING:
    logger.info("Initializing database...")
    db = SessionLocal()
    init_db(db)
    cleanup_logs(db)
    db.close()
    finalize_logging()

# --- 3. AUTH & SECURITY SETUP ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        request.session.clear()
        return None
    return user

def login_required(user: Optional[User] = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not user.is_authorized:
        raise HTTPException(status_code=403, detail="User not authorized")
    return user

# --- 4. APP SETUP ---
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=86400)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.exception_handler(403)
async def unauthorized_exception_handler(request: Request, exc: HTTPException):
    t = get_text(request.headers.get("accept-language"))
    return templates.TemplateResponse(
        request, "unauthorized.html", {"t": t, "user": getattr(request.state, "user", None)}, status_code=403
    )

async def check_page_permission(request: Request, db: Session = Depends(get_db), user: User = Depends(login_required)):
    request.state.user = user
    path = request.url.path
    role_ids = [role.id for role in user.roles]
    potential_paths = [path]
    parts = path.strip("/").split("/")
    while len(parts) > 1:
        parts.pop()
        potential_paths.append("/" + "/".join(parts))

    permission = db.query(Permission).filter(
        Permission.page_path.in_(potential_paths),
        (Permission.user_id == user.id) | (Permission.role_id.in_(role_ids)),
        Permission.level != PermissionLevel.NONE
    ).first()    

    if not permission:
        raise HTTPException(status_code=403, detail="Access Denied")
    return user

def format_num(value, lang_code="en"):
    try:
        formatted = "{:,.2f}".format(float(value))
        if lang_code and lang_code.startswith("es"):
            return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except (ValueError, TypeError):
        return value

templates.env.filters["format_num"] = format_num

# --- 6. ROUTES ---

@app.get("/", response_class=HTMLResponse, tags=[PageType.INFO])
async def read_root(request: Request, accept_language: str = Header(None), user: Optional[User] = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if user.force_password_change:
        return RedirectResponse(url="/change-password", status_code=303)
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "index.html", {"t": t, "user": user})

@app.get("/register", response_class=HTMLResponse, tags=[PageType.INFO])
async def register_page(request: Request, accept_language: str = Header(None)):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "register.html", {"t": t})

@app.post("/register", tags=[PageType.INFO])
async def register_user(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...), accept_language: str = Header(None), db: Session = Depends(get_db)):
    t = get_text(accept_language)
    if db.query(User).filter(User.username == username).first():
        return templates.TemplateResponse(request, "register.html", {"t": t, "error": t.get("err_username_taken")})
    hashed_password = get_password_hash(password)
    new_user = User(username=username, email=email, hashed_password=hashed_password, is_authorized=True)
    db.add(new_user); db.commit()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/forgot-password", response_class=HTMLResponse, tags=[PageType.INFO])
async def forgot_password_page(request: Request, accept_language: str = Header(None)):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "forgot_password.html", {"t": t})

@app.post("/forgot-password", tags=[PageType.INFO])
async def forgot_password(email: str = Form(...), accept_language: str = Header(None)):
    t = get_text(accept_language)
    return HTMLResponse(content=f"<p>{t.get('msg_forgot_pw_sent')}</p><a href='/login'>{t.get('btn_back')}</a>")

@app.get("/login", response_class=HTMLResponse, tags=[PageType.INFO])
async def login_page(request: Request, accept_language: str = Header(None), error: str = None):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "login.html", {"t": t, "error": error})

@app.post("/login", tags=[PageType.INFO])
async def login(request: Request, email: str = Form(...), password: str = Form(...), accept_language: str = Header(None), db: Session = Depends(get_db)):
    user = db.query(User).filter((User.email == email) | (User.username == email)).first()
    t = get_text(accept_language)
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(request, "login.html", {"t": t, "error": t.get("err_invalid_login")})
    request.session["user_id"] = user.id
    if user.force_password_change:
        return RedirectResponse(url="/change-password", status_code=303)
    return RedirectResponse(url="/", status_code=303)

@app.get("/logout", tags=[PageType.INFO])
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

@app.get("/settings/user", response_class=HTMLResponse, tags=[PageType.SETTINGS])
async def user_settings_page(request: Request, accept_language: str = Header(None), user: User = Depends(check_page_permission), db: Session = Depends(get_db)):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "user_settings.html", {"t": t, "user": user})

@app.get("/settings/export", response_class=HTMLResponse, tags=[PageType.SETTINGS])
async def export_data_page(request: Request, accept_language: str = Header(None), user: User = Depends(check_page_permission), db: Session = Depends(get_db)):
    t = get_text(accept_language)
    categories = get_activity_categories(db, "user_data", t)
    return templates.TemplateResponse(request, "export_data.html", {
        "t": t, "user": user, "heading": t.get("heading_export_data"),
        "action_url": "/settings/export", "categories": categories,
        "default_filename": f"rateeye_user_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    })

@app.post("/settings/export", tags=[PageType.SETTINGS])
async def export_data(filename: str = Form(...), include_securities: bool = Form(False), include_roles: bool = Form(False), user: User = Depends(check_page_permission), db: Session = Depends(get_db)):
    export_payload = {"metadata": {"type": "user_data", "version": get_system_setting(db, "version", "unknown"), "timestamp": datetime.now().isoformat(), "exported_by": user.email}}
    if include_securities:
        export_payload["securities"] = [{"symbol": s.symbol, "name": s.name, "security_type": s.security_type, "asset_class": s.asset_class, "current_price": s.current_price, "yield_30_day": s.yield_30_day, "yield_7_day": s.yield_7_day} for s in db.query(Security).all()]
    if include_roles:
        export_payload["roles"] = [{"name": r.name, "description": r.description, "is_system": False, "permissions": [{"path": p.page_path, "type": p.page_type, "level": p.level} for p in r.permissions]} for r in db.query(Role).filter(Role.is_system == False).all()]
    if not filename.endswith(".json"): filename += ".json"
    return JSONResponse(content=export_payload, headers={"Content-Disposition": f"attachment; filename={filename}"})

@app.get("/admin/settings/export", response_class=HTMLResponse, tags=[PageType.SETTINGS])
async def system_export_page(request: Request, accept_language: str = Header(None), user: User = Depends(check_page_permission), db: Session = Depends(get_db)):
    t = get_text(accept_language)
    categories = get_activity_categories(db, "system_data", t)
    return templates.TemplateResponse(request, "export_data.html", {
        "t": t, "user": user, "heading": t.get("heading_system_export"),
        "action_url": "/admin/settings/export", "categories": categories,
        "default_filename": f"rateeye_system_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    })

@app.post("/admin/settings/export", tags=[PageType.SETTINGS])
async def system_export(filename: str = Form(...), include_logging: bool = Form(False), include_endpoints: bool = Form(False), include_system_roles: bool = Form(False), user: User = Depends(check_page_permission), db: Session = Depends(get_db)):
    export_payload = {"metadata": {"type": "system_config", "version": get_system_setting(db, "version", "unknown"), "timestamp": datetime.now().isoformat()}}
    settings_data = {}
    if include_logging:
        s = db.query(SystemSetting).filter(SystemSetting.name == "log_lines").first()
        if s: settings_data["log_lines"] = s.value
    if include_endpoints:
        for k in ["security_data_endpoint", "security_data_api_key"]:
            s = db.query(SystemSetting).filter(SystemSetting.name == k).first()
            if s: settings_data[k] = s.value
    export_payload["system_settings"] = settings_data
    if include_system_roles:
        export_payload["roles"] = [{"name": r.name, "description": r.description, "is_system": True, "permissions": [{"path": p.page_path, "type": p.page_type, "level": p.level} for p in r.permissions]} for r in db.query(Role).filter(Role.is_system == True).all()]
    if not filename.endswith(".json"): filename += ".json"
    return JSONResponse(content=export_payload, headers={"Content-Disposition": f"attachment; filename={filename}"})

@app.get("/settings/import", response_class=HTMLResponse, tags=[PageType.SETTINGS])
async def import_data_page(request: Request, accept_language: str = Header(None), user: User = Depends(check_page_permission), db: Session = Depends(get_db)):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "import_data.html", {
        "t": t, "user": user, "heading": t.get("heading_import_data"),
        "action_url": "/settings/import", "categories": get_activity_categories(db, "user_data", t),
        "success": request.query_params.get("success") == "true", "error": request.query_params.get("error") == "true"
    })

@app.get("/admin/settings/import", response_class=HTMLResponse, tags=[PageType.SETTINGS])
async def system_import_page(request: Request, accept_language: str = Header(None), user: User = Depends(check_page_permission), db: Session = Depends(get_db)):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "import_data.html", {
        "t": t, "user": user, "heading": t.get("heading_system_import"),
        "action_url": "/admin/settings/import", "categories": get_activity_categories(db, "system_data", t),
        "success": request.query_params.get("success") == "true", "error": request.query_params.get("error") == "true"
    })

@app.post("/settings/import", tags=[PageType.SETTINGS])
async def import_data(file: UploadFile = File(...), include_securities: bool = Form(False), include_roles: bool = Form(False), user: User = Depends(check_page_permission), db: Session = Depends(get_db)):
    try:
        data = json.loads(await file.read())
        if data.get("metadata", {}).get("type") != "user_data": raise Exception("Invalid file type")
        if include_securities and "securities" in data:
            for s in data["securities"]:
                existing = db.query(Security).filter(Security.symbol == s["symbol"]).first()
                if not existing: db.add(Security(**s))
                else:
                    for k, v in s.items(): setattr(existing, k, v)
        if include_roles and "roles" in data:
            for r in data["roles"]:
                existing = db.query(Role).filter(Role.name == r["name"]).first()
                if not existing:
                    nr = Role(name=r["name"], description=r["description"], is_system=False)
                    db.add(nr); db.flush()
                    for p in r.get("permissions", []): db.add(Permission(role_id=nr.id, page_path=p["path"], page_type=p["type"], level=p["level"], is_system=False))
        db.commit(); return RedirectResponse(url="/settings/import?success=true", status_code=303)
    except Exception as e:
        logger.error(f"Import failed: {e}"); db.rollback(); return RedirectResponse(url="/settings/import?error=true", status_code=303)

@app.post("/admin/settings/import", tags=[PageType.SETTINGS])
async def system_import(file: UploadFile = File(...), include_logging: bool = Form(False), include_endpoints: bool = Form(False), include_system_roles: bool = Form(False), user: User = Depends(check_page_permission), db: Session = Depends(get_db)):
    try:
        data = json.loads(await file.read())
        if data.get("metadata", {}).get("type") != "system_config": raise Exception("Invalid file type")
        if "system_settings" in data:
            s_data = data["system_settings"]
            if include_logging and "log_lines" in s_data:
                s = db.query(SystemSetting).filter(SystemSetting.name == "log_lines").first()
                if s: s.value = s_data["log_lines"]
            if include_endpoints:
                for k in ["security_data_endpoint", "security_data_api_key"]:
                    if k in s_data:
                        s = db.query(SystemSetting).filter(SystemSetting.name == k).first()
                        if s: s.value = s_data[k]
                        else: db.add(SystemSetting(name=k, value=s_data[k], is_system=True))
        if include_system_roles and "roles" in data:
            for r in data["roles"]:
                if r.get("is_system"):
                    er = db.query(Role).filter(Role.name == r["name"]).first()
                    if er:
                        er.description = r["description"]
                        db.query(Permission).filter(Permission.role_id == er.id).delete()
                        for p in r.get("permissions", []): db.add(Permission(role_id=er.id, page_path=p["path"], page_type=p["type"], level=p["level"], is_system=True))
        db.commit(); return RedirectResponse(url="/admin/settings/import?success=true", status_code=303)
    except Exception as e:
        logger.error(f"System import failed: {e}"); db.rollback(); return RedirectResponse(url="/admin/settings/import?error=true", status_code=303)

@app.get("/settings/user/change-username", response_class=HTMLResponse, tags=[PageType.SETTINGS])
async def user_change_username_page(request: Request, accept_language: str = Header(None), user: User = Depends(check_page_permission)):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "user_change_username.html", {"t": t, "user": user})

@app.post("/settings/user/change-username", tags=[PageType.SETTINGS])
async def user_change_username(request: Request, new_username: str = Form(...), accept_language: str = Header(None), user: User = Depends(login_required), db: Session = Depends(get_db)):
    t = get_text(accept_language)
    if db.query(User).filter(User.username == new_username).first():
        return templates.TemplateResponse(request, "user_change_username.html", {"t": t, "user": user, "error": t.get("err_username_taken")})
    user.username = new_username; db.commit()
    return RedirectResponse(url="/settings/user", status_code=303)

@app.get("/settings/user/change-password", response_class=HTMLResponse, tags=[PageType.SETTINGS])
async def user_change_password_page(request: Request, accept_language: str = Header(None), user: User = Depends(check_page_permission)):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "user_change_password.html", {"t": t, "user": user})

@app.post("/settings/user/change-password", tags=[PageType.SETTINGS])
async def user_change_password(request: Request, current_password: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...), accept_language: str = Header(None), user: User = Depends(login_required), db: Session = Depends(get_db)):
    t = get_text(accept_language)
    if not verify_password(current_password, user.hashed_password):
        return templates.TemplateResponse(request, "user_change_password.html", {"t": t, "user": user, "error": t.get("err_current_password_incorrect")})
    if new_password != confirm_password:
        return templates.TemplateResponse(request, "user_change_password.html", {"t": t, "user": user, "error": t.get("err_passwords_mismatch")})
    user.hashed_password = get_password_hash(new_password); db.commit()
    return RedirectResponse(url="/settings/user", status_code=303)

@app.post("/settings/user/upload-photo", tags=[PageType.SETTINGS])
async def upload_photo(file: UploadFile = File(...), user: User = Depends(login_required), db: Session = Depends(get_db)):
    if not file.content_type.startswith("image/"): raise HTTPException(status_code=400, detail="Not an image")
    ext = os.path.splitext(file.filename)[1]
    filepath = os.path.join(BASE_DIR, "static", "uploads", "profile_photos", f"user_{user.id}{ext}")
    with open(filepath, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
    user.photo_url = f"/static/uploads/profile_photos/user_{user.id}{ext}"; db.commit()
    return RedirectResponse(url="/settings/user", status_code=303)

@app.get("/settings/system", response_class=HTMLResponse, tags=[PageType.SETTINGS])
async def system_settings_page(request: Request, accept_language: str = Header(None), user: User = Depends(check_page_permission), db: Session = Depends(get_db)):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "system_settings.html", {
        "t": t, "line_count": get_system_setting(db, "log_lines", "100"), "user": user,
        "app_log_retention": get_system_setting(db, "app_log_retention", "10"),
        "startup_log_retention": get_system_setting(db, "startup_log_retention", "10"),
        "active_endpoint": get_system_setting(db, "security_data_endpoint", "yahoo"),
        "active_key": get_system_setting(db, "security_data_api_key", "")
    })

@app.post("/settings/system", tags=[PageType.SETTINGS])
async def save_system_settings(log_lines: str = Form(...), app_log_retention: str = Form("10"), startup_log_retention: str = Form("10"), security_data_endpoint: str = Form("yahoo"), api_key: str = Form(""), user: User = Depends(login_required), db: Session = Depends(get_db)):
    for n, v in {"log_lines": log_lines, "app_log_retention": app_log_retention, "startup_log_retention": startup_log_retention, "security_data_endpoint": security_data_endpoint, "security_data_api_key": api_key}.items():
        s = db.query(SystemSetting).filter(SystemSetting.name == n).first()
        if s: s.value = v
        else: db.add(SystemSetting(name=n, value=v, is_system=True))
    db.commit(); return RedirectResponse(url="/settings/system", status_code=303)

@app.get("/show-log", response_class=PlainTextResponse, tags=[PageType.INFO])
async def show_log(db: Session = Depends(get_db)):
    if os.path.exists(ACTIVE_LOG):
        with open(ACTIVE_LOG, "r") as f:
            return "".join(f.readlines()[-int(get_system_setting(db, "log_lines", "100")):])
    return "Log not found"

@app.get("/about", response_class=HTMLResponse, tags=[PageType.INFO])
async def about_page(request: Request, accept_language: str = Header(None), db: Session = Depends(get_db), user: Optional[User] = Depends(get_current_user)):
    return templates.TemplateResponse(request, "about.html", {"t": get_text(accept_language), "version": get_system_setting(db, "version", "Unknown"), "user": user})

# --- 7. OAUTH2 SETUP ---
oauth = OAuth()
oauth.register(name="google", client_id=os.environ.get("GOOGLE_CLIENT_ID", "id"), client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", "sec"), server_metadata_url="https://accounts.google.com/.well-known/openid-configuration", client_kwargs={"scope": "openid email profile"})
oauth.register(name="github", client_id=os.environ.get("GITHUB_CLIENT_ID", "id"), client_secret=os.environ.get("GITHUB_CLIENT_SECRET", "sec"), access_token_url="https://github.com/login/oauth/access_token", authorize_url="https://github.com/login/oauth/authorize", api_base_url="https://api.github.com/", client_kwargs={"scope": "user:email"})

@app.get("/auth/login/{provider}", tags=[PageType.INFO])
async def auth_login(provider: str, request: Request):
    return await oauth.create_client(provider).authorize_redirect(request, str(request.url_for("auth_callback", provider=provider)))

@app.get("/auth/callback/{provider}", tags=[PageType.INFO])
async def auth_callback(provider: str, request: Request, db: Session = Depends(get_db)):
    client = oauth.create_client(provider); token = await client.authorize_access_token(request)
    user_data = token.get("userinfo") or (await client.get("user", token=token)).json()
    email = user_data.get("email")
    if not email and provider == "github": email = next(e["email"] for e in (await client.get("user/emails", token=token)).json() if e["primary"])
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(username=email.split("@")[0], email=email, provider=provider, profile_json=json.dumps(user_data), is_authorized=True)
        db.add(user); db.commit(); db.refresh(user)
    request.session["user_id"] = user.id; return RedirectResponse(url="/", status_code=303)

@app.get("/change-password", response_class=HTMLResponse, tags=[PageType.INFO])
async def change_password_page(request: Request, accept_language: str = Header(None), user: User = Depends(login_required)):
    return templates.TemplateResponse(request, "change_password.html", {"t": get_text(accept_language), "user": user})

@app.post("/change-password", tags=[PageType.INFO])
async def change_password(request: Request, new_password: str = Form(...), confirm_password: str = Form(...), accept_language: str = Header(None), user: User = Depends(login_required), db: Session = Depends(get_db)):
    if new_password != confirm_password: return templates.TemplateResponse(request, "change_password.html", {"t": get_text(accept_language), "user": user, "error": "Mismatch"})
    user.hashed_password = get_password_hash(new_password); user.force_password_change = False; db.commit(); return RedirectResponse(url="/", status_code=303)

@app.get("/admin/users", response_class=HTMLResponse, tags=[PageType.MAINTENANCE])
async def list_users(request: Request, accept_language: str = Header(None), user: User = Depends(check_page_permission), db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "admin_users.html", {"t": get_text(accept_language), "users": db.query(User).all(), "user": user})

@app.post("/admin/users/create", tags=[PageType.MAINTENANCE])
async def create_user(username: str = Form(...), email: str = Form(...), db: Session = Depends(get_db)):
    nu = User(username=username, email=email, hashed_password=get_password_hash(username), is_authorized=True, force_password_change=True)
    ur = db.query(Role).filter(Role.name == "User").first()
    if ur: nu.roles.append(ur)
    db.add(nu); db.commit(); return RedirectResponse(url="/admin/users", status_code=303)

@app.post("/admin/users/update/{user_id}", tags=[PageType.MAINTENANCE])
async def update_user(user_id: int, email: str = Form(...), force_password_change: bool = Form(False), db: Session = Depends(get_db)):
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user:
        # Check if email is taken by another user
        existing = db.query(User).filter(User.email == email, User.id != user_id).first()
        if not existing:
            target_user.email = email; target_user.force_password_change = force_password_change; db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)

@app.post("/admin/users/force-password-change/{user_id}", tags=[PageType.MAINTENANCE])
async def force_password_change(user_id: int, db: Session = Depends(get_db)):
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user:
        target_user.force_password_change = True; db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)

@app.get("/admin/roles", response_class=HTMLResponse, tags=[PageType.MAINTENANCE])
async def list_roles(request: Request, accept_language: str = Header(None), user: User = Depends(check_page_permission), db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "admin_roles.html", {"t": get_text(accept_language), "roles": db.query(Role).all(), "user": user, "all_users": db.query(User).all()})

@app.post("/admin/roles/create", tags=[PageType.MAINTENANCE])
async def create_role(name: str = Form(...), description: str = Form(""), db: Session = Depends(get_db)):
    db.add(Role(name=name, description=description)); db.commit(); return RedirectResponse(url="/admin/roles", status_code=303)

@app.post("/admin/roles/update/{role_id}", tags=[PageType.MAINTENANCE])
async def update_role(role_id: int, name: str = Form(...), description: str = Form(""), user_ids: Optional[str] = Form(None), db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if role:
        role.name = name; role.description = description
        if user_ids is not None:
            role.users = []
            if user_ids.strip(): role.users.extend(db.query(User).filter(User.id.in_([int(i) for i in user_ids.split(",") if i.strip()])).all())
        db.commit()
    return RedirectResponse(url="/admin/roles", status_code=303)

@app.post("/admin/roles/delete/{role_id}", tags=[PageType.MAINTENANCE])
async def delete_role(role_id: int, db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if role and role.name not in ["Admin", "User"]: db.delete(role); db.commit()
    return RedirectResponse(url="/admin/roles", status_code=303)

@app.post("/admin/users/delete/{user_id}", tags=[PageType.MAINTENANCE])
async def delete_user(user_id: int, user: User = Depends(login_required), db: Session = Depends(get_db)):
    if user.id == user_id: raise HTTPException(status_code=400, detail="Cannot delete yourself.")
    tu = db.query(User).filter(User.id == user_id).first()
    if tu: tu.roles = []; db.delete(tu); db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)

@app.get("/admin/securities", response_class=HTMLResponse, tags=[PageType.MAINTENANCE])
async def list_securities(request: Request, accept_language: str = Header(None), user: User = Depends(check_page_permission), db: Session = Depends(get_db)):
    t = get_text(accept_language)
    return templates.TemplateResponse(request, "admin_securities.html", {
        "t": t, "title": t.get("item_securities"), "user": user, "securities": db.query(Security).all(),
        "security_types": list(SecurityType), "asset_classes": list(AssetClass), "metadata": load_metadata("securities", Security)
    })

@app.post("/admin/securities/create", tags=[PageType.MAINTENANCE])
async def create_security(symbol: str = Form(...), name: str = Form(...), security_type: SecurityType = Form(...), asset_class: Optional[AssetClass] = Form(None), previous_close: Optional[str] = Form(None), open_price: Optional[str] = Form(None), current_price: Optional[str] = Form(None), nav: Optional[str] = Form(None), range_52_week: Optional[str] = Form(None), avg_volume: Optional[str] = Form(None), yield_30_day: Optional[str] = Form(None), yield_7_day: Optional[str] = Form(None), accept_language: str = Header(None), db: Session = Depends(get_db)):
    if db.query(Security).filter(Security.symbol == symbol.upper()).first(): raise HTTPException(status_code=400, detail="already exists")
    db.add(Security(symbol=symbol.upper(), name=name, security_type=security_type, asset_class=asset_class, previous_close=previous_close, open_price=open_price, current_price=current_price, nav=nav, range_52_week=range_52_week, avg_volume=avg_volume, yield_30_day=yield_30_day, yield_7_day=yield_7_day))
    db.commit(); return RedirectResponse(url="/admin/securities", status_code=303)

@app.post("/admin/securities/update/{sec_id}", tags=[PageType.MAINTENANCE])
async def update_security(sec_id: int, symbol: str = Form(...), name: str = Form(...), security_type: SecurityType = Form(...), asset_class: Optional[AssetClass] = Form(None), previous_close: Optional[str] = Form(None), open_price: Optional[str] = Form(None), current_price: Optional[str] = Form(None), nav: Optional[str] = Form(None), range_52_week: Optional[str] = Form(None), avg_volume: Optional[str] = Form(None), yield_30_day: Optional[str] = Form(None), yield_7_day: Optional[str] = Form(None), db: Session = Depends(get_db)):
    sec = db.query(Security).filter(Security.id == sec_id).first()
    if sec:
        sec.symbol = symbol; sec.name = name; sec.security_type = security_type; sec.asset_class = asset_class
        sec.previous_close = previous_close; sec.open_price = open_price; sec.current_price = current_price
        sec.nav = nav; sec.range_52_week = range_52_week; sec.avg_volume = avg_volume
        sec.yield_30_day = yield_30_day; sec.yield_7_day = yield_7_day; db.commit()
    return RedirectResponse(url="/admin/securities", status_code=303)

@app.post("/admin/securities/delete/{sec_id}", tags=[PageType.MAINTENANCE])
async def delete_security(sec_id: int, db: Session = Depends(get_db)):
    sec = db.query(Security).filter(Security.id == sec_id).first()
    if sec: db.delete(sec); db.commit()
    return RedirectResponse(url="/admin/securities", status_code=303)

@app.get("/admin/securities/search", tags=[PageType.MAINTENANCE])
async def search_securities(q: str, db: Session = Depends(get_db)):
    return await get_security_endpoint(db).search(q)

@app.get("/admin/securities/lookup", tags=[PageType.MAINTENANCE])
async def lookup_security(symbol: str, db: Session = Depends(get_db)):
    data = await get_security_endpoint(db).lookup(symbol)
    if not data: raise HTTPException(status_code=404, detail="Not found")
    return data

class BulkCreateRequest(BaseModel): symbols: List[str]
@app.post("/admin/securities/bulk_create", tags=[PageType.MAINTENANCE])
async def bulk_create_securities(request: BulkCreateRequest, db: Session = Depends(get_db)):
    ep = get_security_endpoint(db); added = []; errors = []
    for s in request.symbols:
        s = s.upper().strip()
        if not s: continue
        if db.query(Security).filter(Security.symbol == s).first():
            errors.append(f"{s} already exists")
            continue
        try:
            d = await ep.lookup(s)
            if d:
                db.add(Security(symbol=s, name=d.get("name", s), security_type=d.get("security_type", SecurityType.STOCK), asset_class=d.get("asset_class"), current_price=d.get("current_price"), previous_close=d.get("previous_close"), open_price=d.get("open_price"), nav=d.get("nav"), range_52_week=d.get("range_52_week"), avg_volume=d.get("avg_volume"), yield_30_day=d.get("yield_30_day"), yield_7_day=d.get("yield_7_day")))
                added.append(s)
            else: errors.append(f"{s} not found")
        except Exception as e: errors.append(f"Error {s}: {e}")
    db.commit(); return {"added": added, "errors": errors}

class BulkDeleteRequest(BaseModel): symbols: List[str]
@app.post("/admin/securities/bulk_delete", tags=[PageType.MAINTENANCE])
async def bulk_delete_securities(request: BulkDeleteRequest, db: Session = Depends(get_db)):
    c = db.query(Security).filter(Security.symbol.in_([s.upper().strip() for s in request.symbols])).delete(synchronize_session=False)
    db.commit(); return {"deleted": c}

@app.post("/admin/securities/test_endpoint", tags=[PageType.SETTINGS])
async def test_security_endpoint(endpoint: str = Form(...), api_key: Optional[str] = Form(None)):
    try:
        if endpoint == "finnhub": ep = FinnhubEndpoint(api_key=api_key or "")
        elif endpoint == "alphavantage": ep = AlphaVantageEndpoint(api_key=api_key or "")
        else: ep = YahooScraperEndpoint()
        d = await ep.lookup("VOO")
        return {"success": True} if d and d.get("symbol") == "VOO" else {"success": False, "error": "No data"}
    except Exception as e: return {"success": False, "error": str(e)}

@app.get("/admin/permissions", response_class=HTMLResponse, tags=[PageType.MAINTENANCE])
async def list_permissions(request: Request, accept_language: str = Header(None), user: User = Depends(check_page_permission), db: Session = Depends(get_db)):
    t = get_text(accept_language); perms = db.query(Permission).all(); pages = get_pages()
    grouped = {pt: {path: {"label": t.get(lk, path), "subjects": {}} for path, p_type, lk in pages if p_type == pt} for pt in PageType}
    for p in perms:
        sk = f"role:{p.role_id}" if p.role_id else f"user:{p.user_id}"
        if p.page_path in grouped.get(p.page_type, {}):
            s = grouped[p.page_type][p.page_path]["subjects"]
            if sk not in s: s[sk] = {"role": p.role, "user": p.user, "permissions": []}
            s[sk]["permissions"].append(p)
    return templates.TemplateResponse(request, "admin_permissions.html", {"t": t, "user": user, "grouped": grouped, "roles": db.query(Role).all(), "users": db.query(User).all(), "page_types": list(PageType), "permission_levels": list(PermissionLevel)})

@app.post("/admin/permissions/create", tags=[PageType.MAINTENANCE])
async def create_permission(page_path: str = Form(...), subject: str = Form(...), level: PermissionLevel = Form(...), db: Session = Depends(get_db)):
    st, sid = subject.split(":"); rid = int(sid) if st == "role" else None; uid = int(sid) if st == "user" else None
    pt = next((p[1] for p in get_pages() if p[0] == page_path), PageType.INFO)
    
    if level in [PermissionLevel.FULL, PermissionLevel.NONE]:
        # FULL or NONE clears everything else for this subject/path
        db.query(Permission).filter(Permission.page_path == page_path, Permission.role_id == rid, Permission.user_id == uid).delete()
    else:
        # Other levels (READ, UPDATE, etc.) remove FULL/NONE first
        db.query(Permission).filter(
            Permission.page_path == page_path, 
            Permission.role_id == rid, 
            Permission.user_id == uid,
            Permission.level.in_([PermissionLevel.FULL, PermissionLevel.NONE])
        ).delete()
        # And remove the exact same level if it already exists to avoid duplicates
        db.query(Permission).filter(Permission.page_path == page_path, Permission.role_id == rid, Permission.user_id == uid, Permission.level == level).delete()

    db.add(Permission(page_path=page_path, page_type=pt, role_id=rid, user_id=uid, level=level))
    db.commit(); return RedirectResponse(url="/admin/permissions", status_code=303)

@app.post("/admin/permissions/delete-subject", tags=[PageType.MAINTENANCE])
async def delete_permission_subject(page_path: str = Form(...), subject: str = Form(...), db: Session = Depends(get_db)):
    st, sid = subject.split(":"); rid = int(sid) if st == "role" else None; uid = int(sid) if st == "user" else None
    db.query(Permission).filter(Permission.page_path == page_path, Permission.role_id == rid, Permission.user_id == uid).delete()
    # Reset to NONE
    pt = next((p[1] for p in get_pages() if p[0] == page_path), PageType.INFO)
    db.add(Permission(page_path=page_path, page_type=pt, role_id=rid, user_id=uid, level=PermissionLevel.NONE))
    db.commit(); return RedirectResponse(url="/admin/permissions", status_code=303)

@app.post("/admin/permissions/delete/{perm_id}", tags=[PageType.MAINTENANCE])
async def delete_permission(perm_id: int, db: Session = Depends(get_db)):
    p = db.query(Permission).filter(Permission.id == perm_id).first()
    if p:
        path, rid, uid = p.page_path, p.role_id, p.user_id; db.delete(p); db.commit()
        if db.query(Permission).filter(Permission.page_path == path, Permission.role_id == rid, Permission.user_id == uid).count() == 0:
            pt = next((pg[1] for pg in get_pages() if pg[0] == path), PageType.INFO)
            db.add(Permission(page_path=path, page_type=pt, role_id=rid, user_id=uid, level=PermissionLevel.NONE)); db.commit()
    return RedirectResponse(url="/admin/permissions", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
