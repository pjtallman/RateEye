import sys
import os
import multiprocessing
import traceback

def show_error(msg):
    """Shows a macOS or Windows error dialog."""
    print(msg) # Still print to console
    try:
        if sys.platform == 'darwin':
            os.system(f"osascript -e 'display alert \"RateEye Startup Error\" message \"{msg}\" buttons {{\"OK\"}} default button \"OK\"'")
        elif sys.platform == 'win32':
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, msg, "RateEye Startup Error", 0x10)
    except:
        pass

if __name__ == "__main__":
    # Required for PyInstaller bundles using uvicorn/multiprocessing
    multiprocessing.freeze_support()
    
    try:
        # Add 'src' to the path so 'rateeye' is found as a package
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        src_path = os.path.join(base_path, "src")
        if os.path.exists(src_path):
            sys.path.insert(0, src_path)
        else:
            # In some bundle modes, MEIPASS is the root
            sys.path.insert(0, base_path)

        # Import paths early to initialize ROOT_DIR
        from rateeye.core.paths import ROOT_DIR
        print(f"RateEye initializing... Data/Logs located at: {ROOT_DIR}")

        from rateeye.main import app
        import uvicorn
        import webbrowser
        from threading import Timer

        def open_browser():
            webbrowser.open("http://127.0.0.1:8000")

        # Check if we are running in a test environment
        is_testing = "pytest" in os.environ.get("PYTEST_CURRENT_TEST", "")
        
        if not is_testing:
            Timer(1.5, open_browser).start()

        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

    except Exception as e:
        error_msg = f"Failed to start RateEye:\n\n{str(e)}\n\n{traceback.format_exc()}"
        show_error(error_msg)
        sys.exit(1)
