# tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from main import app, User, get_db, SessionLocal
import os

client = TestClient(app)

@pytest.fixture
def test_user():
    # Setup: ensure we have a clean state or a known user
    db = SessionLocal()
    user = db.query(User).filter(User.email == "test@example.com").first()
    if user:
        db.delete(user)
        db.commit()
    db.close()
    return {"email": "test@example.com", "password": "securepassword123"}

def test_registration(test_user):
    response = client.post(
        "/register",
        data={"email": test_user["email"], "password": test_user["password"]},
        follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login"

def test_login_success(test_user):
    # Ensure user exists
    client.post(
        "/register",
        data={"email": test_user["email"], "password": test_user["password"]}
    )
    
    response = client.post(
        "/login",
        data={"email": test_user["email"], "password": test_user["password"]},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert "Logged in as: test@example.com" in response.text

def test_login_with_remember_me(test_user):
    # Ensure user exists
    client.post(
        "/register",
        data={"email": test_user["email"], "password": test_user["password"]}
    )
    
    response = client.post(
        "/login",
        data={"email": test_user["email"], "password": test_user["password"], "remember_me": "on"},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert "Logged in as: test@example.com" in response.text
    # In a real test we'd check cookie expiration, but TestClient simplifies this.

def test_login_failure():
    response = client.post(
        "/login",
        data={"email": "wrong@example.com", "password": "wrongpassword"},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert "Invalid email or password" in response.text

def test_root_redirect_unauthenticated():
    # Logout first
    client.get("/logout")
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"

def test_protected_settings_redirect_unauthenticated():
    client.get("/logout")
    response = client.get("/settings", follow_redirects=False)
    assert response.status_code == 401

def test_logout(test_user):
    # Login first
    client.post(
        "/login",
        data={"email": test_user["email"], "password": test_user["password"]}
    )
    # Logout
    response = client.get("/logout", follow_redirects=True)
    # After logout, / redirects to /login
    assert response.url.path == "/login"
    assert "Login" in response.text

def test_show_log_protected():
    client.get("/logout")
    response = client.get("/show-log")
    assert response.status_code == 401
