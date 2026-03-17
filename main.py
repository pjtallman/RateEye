import logging
import os
import shutil
from datetime import datetime
from fastapi import FastAPI, Request, Form, Header
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import sessionmaker, declarative_base  # Updated import

# Local Imports
from i18n import get_text

# --- 1. LOGGING ROTATION LOGIC ---
LOG_DIR = "logs"
ACTIVE_LOG = os.path.join(LOG_DIR, "RateEye.log")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


def rotate_logs():
    today_str = datetime.now().strftime("%Y%m%d")
    archive_name = os.path.join(LOG_DIR, f"{today_str}_RateEye.log")
    if os.path.exists(ACTIVE_LOG):
        if not os.path.exists(archive_name):
            shutil.copy(ACTIVE_LOG, archive_name)
            with open(ACTIVE_LOG, "w") as f:
                f.write(f"--- Log Rotated/Started at {datetime.now()} ---\n")


rotate_logs()

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

# FIXED: Modern SQLAlchemy 2.0 approach
Base = declarative_base()


class Setting(Base):
    __tablename__ = "settings"
    name = Column(String, primary_key=True, index=True)
    value = Column(String)


Base.metadata.create_all(bind=engine)


def get_setting(name: str, default: str):
    db = SessionLocal()
    res = db.query(Setting).filter(Setting.name == name).first()
    db.close()
    return res.value if res else default


# --- 3. APP SETUP ---
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# --- 4. LOCALIZATION FILTERS ---
def format_num(value, lang_code="en"):
    try:
        formatted = "{:,.2f}".format(float(value))
        if lang_code and lang_code.startswith("es"):
            return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except (ValueError, TypeError):
        return value


templates.env.filters["format_num"] = format_num

# --- 5. ROUTES ---


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, accept_language: str = Header(None)):
    t = get_text(accept_language)
    # FIXED: TemplateResponse(request, name, context) is the new standard
    return templates.TemplateResponse(request, "index.html", {"t": t})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, accept_language: str = Header(None)):
    t = get_text(accept_language)
    line_count = get_setting("log_lines", "100")
    return templates.TemplateResponse(
        request, "settings.html", {"t": t, "line_count": line_count}
    )


@app.post("/settings")
async def save_settings(log_lines: str = Form(...)):
    db = SessionLocal()
    setting = db.query(Setting).filter(Setting.name == "log_lines").first()
    if setting:
        setting.value = log_lines
    else:
        db.add(Setting(name="log_lines", value=log_lines))
    db.commit()
    db.close()
    return RedirectResponse(url="/", status_code=303)


@app.get("/show-log", response_class=PlainTextResponse)
async def show_log():
    line_limit = int(get_setting("log_lines", "100"))
    if os.path.exists(ACTIVE_LOG):
        with open(ACTIVE_LOG, "r") as f:
            lines = f.readlines()
            content = "".join(lines[-line_limit:])
        return content
    return "No log file found."


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
