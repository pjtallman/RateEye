# RateEye Deployment & Installation Guide

## 1. Deployment Model Overview
RateEye utilizes a **Monolithic Self-Hosted Model**. The application is designed to run as a single process that serves both the FastAPI backend and the static frontend assets.

### Key Architectural Components:
- **Application Server:** FastAPI (Uvicorn) handles all HTTP requests and API endpoints.
- **Database:** A local SQLite file (`rateeye.db`) is used for persistent storage.
- **Frontend:** TypeScript files are compiled into JavaScript and served as static files.
- **Automation:** A unified `install.py` script handles environment setup, builds, testing, and deployment.

---

## 2. Automated Installation (Recommended)

RateEye provides a robust, cross-platform installation script that automates prerequisite validation, environment setup, frontend building, and unit testing.

### Prerequisites:
Ensure you have the following installed on your system:
- **Python 3.12+**
- **Node.js (v18+) & NPM**
- **Git**

### Execution:
1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/pjtallman/RateEye.git
    cd RateEye
    ```
2.  **Run the Installer:**
    ```bash
    # On Mac/Linux:
    python3 install.py
    
    # On Windows:
    python install.py
    ```

### What the Installer Does:
1.  **Detects OS:** Configures paths for Mac, Windows, or Linux.
2.  **Validates Prerequisites:** Ensures Git, Node, and NPM are in your PATH.
3.  **Environment Setup:** Creates a virtual environment (`.venv`) and installs all dependencies from `requirements.txt`.
4.  **Frontend Build:** Runs `npm install` and `npm run build` to compile TypeScript assets.
5.  **Validation:** Runs the full suite of **Unit Tests**. 
    *   *Note: If tests fail, the application will not launch, and errors will be reported.*
6.  **Launch:** Starts the FastAPI server at `http://localhost:8000`.
7.  **Logging:** Detailed logs of the entire process are saved to `logs/install.log`.

---

## 3. Manual Installation: Mac OS

If you prefer to perform steps manually:

1.  **Environment Setup:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```
2.  **Build Frontend:**
    ```bash
    npm install
    npm run build
    ```
3. **Run Tests:**
    ```bash
    export PYTHONPATH=$PYTHONPATH:$(pwd)/src
    pytest
    ```
4. **Launch:**
    ```bash
    export PYTHONPATH=$PYTHONPATH:$(pwd)/src
    python3 -m rateeye.main
    ```


---

## 4. Manual Installation: Windows

1.  **Environment Setup:**
    ```powershell
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    ```
2.  **Build Frontend:**
    ```powershell
    npm install
    npm run build
    ```
3. **Run Tests:**
    ```powershell
    $env:PYTHONPATH += ";$(Get-Location)\src"
    pytest
    ```
4. **Launch:**
    ```powershell
    $env:PYTHONPATH += ";$(Get-Location)\src"
    python -m rateeye.main
    ```


---

## 5. Deployment Configuration (Production)

### Environment Variables
Override the default SQLite database:
- **Unix:** `export DATABASE_URL="sqlite:///./prod.db"`
- **Windows:** `$env:DATABASE_URL="sqlite:///./prod.db"`

### Security Considerations
- **HTTPS:** Run RateEye behind a reverse proxy (Nginx/Apache) for SSL termination.
- **Port:** Default is `8000`.

## 6. Troubleshooting
- **Install Logs:** Check `logs/install.log` for detailed failure reasons.
- **Missing Modules:** Ensure your virtual environment is active.
- **Build Errors:** Verify Node.js and NPM versions.
