import sys
import os

# Add 'src' to the path so 'rateeye' is found as a package
base_path = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(base_path, "src")
if os.path.exists(src_path):
    sys.path.insert(0, src_path)

from rateeye.main import app
import uvicorn
import webbrowser
from threading import Timer

def open_browser():
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    # Check if we are running in a test environment
    is_testing = "pytest" in os.environ.get("PYTEST_CURRENT_TEST", "")
    
    if not is_testing:
        Timer(1.5, open_browser).start()

    uvicorn.run(app, host="0.0.0.0", port=8000)
