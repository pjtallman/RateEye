import logging
import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# --- DATABASE SETUP ---
DATABASE_URL = "sqlite:///./rateeye.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Setting(Base):
    __tablename__ = "settings"
    name = Column(String, primary_key=True, index=True)
    value = Column(String)


Base.metadata.create_all(bind=engine)


# Helper to get/set settings
def get_setting(name, default):
    db = SessionLocal()
    res = db.query(Setting).filter(Setting.name == name).first()
    db.close()
    return res.value if res else default


# --- APP SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.FileHandler("rateeye.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
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
    return RedirectResponse(url="/", status_code=303)


@app.get("/show-log", response_class=PlainTextResponse)
async def show_log():
    line_limit = int(get_setting("log_lines", "100"))
    if os.path.exists("rateeye.log"):
        with open("rateeye.log", "r") as f:
            lines = f.readlines()
            # Get the last N lines
            content = "".join(lines[-line_limit:])
        return content
    return "No log file found."


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
