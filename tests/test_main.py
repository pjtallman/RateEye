# tests/test_main.py
import pytest
from fastapi.testclient import TestClient
import sys
import os
from sqlalchemy.orm import Session
from main import app, format_num, User, get_password_hash, SessionLocal

# Ensure the parent directory is in the path so we can import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

client = TestClient(app)

@pytest.fixture(scope="module")
def authenticated_client():
    """Fixture to provide an authenticated test client."""
    db = SessionLocal()
    email = "test_main@example.com"
    password = "password123"
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, hashed_password=get_password_hash(password))
        db.add(user)
        db.commit()
    db.close()
    
    # Create a new client and log in
    ac = TestClient(app)
    ac.post("/login", data={"email": email, "password": password})
    return ac

def test_root_redirect_unauthenticated():
    """Verify that unauthenticated users are redirected from / to /login."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"

def test_language_en(authenticated_client):
    """Verify English strings are returned by default or explicitly."""
    response = authenticated_client.get("/", headers={"Accept-Language": "en-US,en;q=0.9"})
    assert response.status_code == 200
    assert "Yield Tracker" in response.text
    assert "File" in response.text
    # Verify the specific Edit menu items are present
    assert "Cut" in response.text
    assert "Copy" in response.text

def test_language_es(authenticated_client):
    """Verify Spanish strings are returned when requested."""
    # We might need to ensure the client stays logged in or use the session
    response = authenticated_client.get("/", headers={"Accept-Language": "es-ES,es;q=0.9"})
    assert response.status_code == 200
    assert "Rastreador de Rendimiento" in response.text
    assert "Archivo" in response.text
    assert "Cortar" in response.text

def test_language_fallback(authenticated_client):
    """Verify that an unknown language falls back to English."""
    response = authenticated_client.get("/", headers={"Accept-Language": "fr-FR"})
    assert "Yield Tracker" in response.text

def test_numeric_localization():
    """Verify the Jinja2 filter swaps separators for Spanish."""
    val = 1234.56
    assert format_num(val, "en") == "1,234.56"
    assert format_num(val, "es") == "1.234,56"
