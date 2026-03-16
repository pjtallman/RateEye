import logging
import os
import shutil
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# --- 1. LOGGING ROTATION LOGIC ---
LOG_DIR = "logs"
ACTIVE_LOG = os.path.join(LOG_DIR, "RateEye.log")

# Ensure log directory exists
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


def rotate_logs():
    """Archives the current log if it's the first run of a new day."""
    today_str = datetime.now().strftime("%Y%m%d")
    archive_name = os.path.join(LOG_DIR, f"{today_str}_RateEye.log")

    if os.path.exists(ACTIVE_LOG):
        # If today's archive doesn't exist yet, rotate the current log
        if not os.path.exists(archive_name):
            shutil.copy(ACTIVE_LOG, archive_name)
            # Clear the active log and start fresh
            with open(ACTIVE_LOG, "w") as f:
                f.write(f"--- Log Rotated/Started at {datetime.now()} ---\n")
            print(f"Log archived to {archive_name}")


# Perform rotation check immediately upon script execution
rotate_logs()

# Configure the logger to use the Active Log file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(ACTIVE_LOG), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# --- 2. DATABASE SETUP (SQLAlchemy) ---
DATABASE_URL = "sqlite:///./rateeye.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Setting(Base):
    __tablename__ = "settings"
    name = Column(String, primary_key=True, index=True)
    value = Column(String)


# Create the tables if they don't exist
Base.metadata.create_all(bind=engine)


def get_setting(name: str, default: str):
    """Utility to fetch a setting value from the DB."""
    db = SessionLocal()
    res = db.query(Setting).filter(Setting.name == name).first()
    db.close()
    return res.value if res else default


# --- 3. APP SETUP ---
app = FastAPI()

# Mount the static folder so index.html can find style.css
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="templates")

# --- 4. ROUTES ---


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    logger.info("Accessing Landing Page")
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    line_count = get_setting("log_lines", "100")
    return templates.TemplateResponse(
        "settings.html", {"request": request, "line_count": line_count}
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
    logger.info(f"Settings updated: log_lines set to {log_lines}")
    return RedirectResponse(url="/", status_code=303)


@app.get("/show-log", response_class=PlainTextResponse)
async def show_log():
    # Retrieve user preference from DB
    line_limit = int(get_setting("log_lines", "100"))

    if os.path.exists(ACTIVE_LOG):
        with open(ACTIVE_LOG, "r") as f:
            lines = f.readlines()
            # Slice the list to get the last N lines
            content = "".join(lines[-line_limit:])
        return content
    return "No log file found."


# --- 5. SERVER START ---
if __name__ == "__main__":
    import uvicorn

    logger.info("RateEye engine starting up...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
