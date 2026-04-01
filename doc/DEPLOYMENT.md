# RateEye Deployment & Installation Guide

## 1. Deployment Model Overview
RateEye utilizes a **Monolithic Self-Hosted Model**. The application is designed to run as a single process that serves both the FastAPI backend and the static frontend assets.

### Key Architectural Components:
- **Application Server:** FastAPI (Uvicorn) handles all HTTP requests and API endpoints.
- **Database:** A local SQLite file (`rateeye.db`) is used for persistent storage, requiring no external database server configuration for standard deployments.
- **Frontend:** TypeScript files are pre-compiled into JavaScript and served as static files by the FastAPI application.
- **Dependency Management:** Python dependencies are managed via `uv` or `pip`, and frontend dependencies via `npm`.

---

## 2. System Prerequisites
Before installation, ensure the target machine has the following installed:
- **Python 3.12 or newer**
- **Node.js (v18+) and NPM**
- **Git** (for cloning the repository)
- **uv** (Recommended for Python package management)

---

## 3. Installation Instructions: Mac OS

### Step 1: Clone the Repository
Open **Terminal** and run:
```bash
git clone https://github.com/pjtallman/RateEye.git
cd RateEye
```

### Step 2: Set Up Python Environment
We recommend using `uv` for speed, but standard `venv` works as well.
**Using uv (Recommended):**
```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```
**Using standard venv:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Build the Frontend
Install Node dependencies and compile the TypeScript assets:
```bash
npm install
npm run build
```

### Step 4: Launch the Application
```bash
python3 main.py
```
The application will be available at `http://localhost:8000`.

---

## 4. Installation Instructions: Windows

### Step 1: Clone the Repository
Open **PowerShell** or **Command Prompt** and run:
```powershell
git clone https://github.com/pjtallman/RateEye.git
cd RateEye
```

### Step 2: Set Up Python Environment
**Using uv (Recommended):**
```powershell
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
```
**Using standard venv:**
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Build the Frontend
```powershell
npm install
npm run build
```

### Step 4: Launch the Application
```powershell
python main.py
```
The application will be available at `http://localhost:8000`.

---

## 5. Deployment Configuration (Production)

### Environment Variables
By default, RateEye uses a local SQLite database. You can override this using the `DATABASE_URL` environment variable:
- **Unix:** `export DATABASE_URL="sqlite:///./prod.db"`
- **Windows:** `$env:DATABASE_URL="sqlite:///./prod.db"`

### Security Considerations
- **HTTPS:** In a production environment, it is highly recommended to run RateEye behind a reverse proxy like **Nginx** or **Apache** to handle SSL/TLS termination.
- **Port Mapping:** The default port is `8000`. Ensure your firewall allows traffic on this port or configure the proxy to forward requests to it.

## 6. Troubleshooting
- **Missing Modules:** If you see `ModuleNotFoundError`, ensure your virtual environment is active (`source .venv/bin/activate` or `.venv\Scripts\activate`).
- **JavaScript Errors:** If the UI doesn't load correctly, ensure `npm run build` completed without errors and check that the `static/js/` directory contains compiled `.js` files.
- **Database Locked:** If multiple processes try to write to SQLite simultaneously, you may see a "Database is locked" error. Ensure only one instance of `main.py` is running.
