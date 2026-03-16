import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# 1. Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("rateeye.log"),  # Saves to a file
        logging.StreamHandler(),  # Also prints to terminal
    ],
)
logger = logging.getLogger(__name__)

app = FastAPI()

# 2. Mount Static Files (CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    logger.info("Landing page accessed")
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/show-log", response_class=PlainTextResponse)
async def show_log():
    # Reads the log file and displays it in the browser
    if os.path.exists("rateeye.log"):
        with open("rateeye.log", "r") as f:
            content = f.read()
        return content
    return "No log file found yet."


import os

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting RateEye Server...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
