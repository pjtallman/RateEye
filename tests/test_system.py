import pytest
import os
from database import SystemSetting, get_system_setting

def test_system_settings_page(client, test_user):
    # Log in
    client.post(
        "/login",
        data={"email": "test@example.com", "password": "testpassword"}
    )
    
    response = client.get("/settings/system")
    assert response.status_code == 200
    assert "system_settings.html" in response.template.name
    assert "100" in response.text

def test_save_system_settings(client, test_user, db):
    # Log in
    client.post(
        "/login",
        data={"email": "test@example.com", "password": "testpassword"}
    )
    
    # Save settings
    response = client.post(
        "/settings/system",
        data={"log_lines": "250"},
        follow_redirects=True
    )
    assert response.status_code == 200
    
    # Verify in DB
    setting = db.query(SystemSetting).filter(SystemSetting.name == "log_lines").first()
    assert setting.value == "250"

def test_show_log(client, test_user):
    # Log in
    client.post(
        "/login",
        data={"email": "test@example.com", "password": "testpassword"}
    )
    
    # Create a dummy log file if it doesn't exist
    LOG_DIR = "logs"
    ACTIVE_LOG = os.path.join(LOG_DIR, "RateEye.log")
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(ACTIVE_LOG, "w") as f:
        f.write("Test log line 1\nTest log line 2\n")
    
    response = client.get("/show-log")
    assert response.status_code == 200
    assert "Test log line 2" in response.text

def test_unauthorized_access(client):
    # Try to access root without login
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    
    # Try to access settings without login
    response = client.get("/settings/user", follow_redirects=False)
    assert response.status_code == 401 # FastAPI raises HTTPException for login_required
