import os
import sys

def get_base_dir():
    """Returns the base directory for the application, handling PyInstaller bundles."""
    if getattr(sys, 'frozen', False):
        # Running as a bundled executable
        # sys._MEIPASS is the root of the temporary bundle folder
        return sys._MEIPASS
    else:
        # Running as a normal Python script
        # __file__ is src/rateeye/core/paths.py
        # root is 4 levels up
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

BASE_DIR = get_base_dir()

def get_writable_root():
    """Returns a writable directory for logs and data."""
    # If running as a bundle, default to ~/RateEye
    if getattr(sys, 'frozen', False):
        home_dir = os.path.expanduser("~")
        fallback = os.path.join(home_dir, "RateEye")
        if not os.path.exists(fallback):
            os.makedirs(fallback, exist_ok=True)
        return fallback

    cwd = os.getcwd()
    # Check if CWD is writable (for dev mode)
    if os.access(cwd, os.W_OK) and not cwd == "/":
        return cwd
    
    home_dir = os.path.expanduser("~")
    fallback = os.path.join(home_dir, "RateEye")
    if not os.path.exists(fallback):
        os.makedirs(fallback, exist_ok=True)
    return fallback

ROOT_DIR = get_writable_root()
