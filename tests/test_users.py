import pytest
from database import User, pwd_context

def test_user_settings_page(client, test_user):
    # Log in
    client.post(
        "/login",
        data={"email": "test@example.com", "password": "testpassword"}
    )
    
    response = client.get("/settings/user")
    assert response.status_code == 200
    assert "user_settings.html" in response.template.name
    assert "test@example.com" in response.text

def test_change_username_success(client, test_user, db):
    # Log in
    client.post(
        "/login",
        data={"email": "test@example.com", "password": "testpassword"}
    )
    
    # Change username
    response = client.post(
        "/settings/user/change-username",
        data={"new_username": "updatedusername"},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert "user_settings.html" in response.template.name
    
    # Verify in DB
    db.refresh(test_user)
    assert test_user.username == "updatedusername"

def test_change_username_taken(client, test_user, db):
    # Create another user
    db.add(User(username="otheruser", email="other@example.com", hashed_password="hashed"))
    db.commit()
    
    # Log in
    client.post(
        "/login",
        data={"email": "test@example.com", "password": "testpassword"}
    )
    
    # Try to change to 'otheruser'
    response = client.post(
        "/settings/user/change-username",
        data={"new_username": "otheruser"},
        follow_redirects=False
    )
    assert response.status_code == 200
    assert "Username already taken" in response.text

def test_admin_list_users(client, test_admin):
    # Log in as admin
    client.post(
        "/login",
        data={"email": "admin@example.com", "password": "adminpassword"}
    )
    
    response = client.get("/admin/users")
    assert response.status_code == 200
    assert "admin_users.html" in response.template.name
    assert "adminuser" in response.text

def test_admin_force_password_change(client, test_admin, test_user, db):
    # Log in as admin
    client.post(
        "/login",
        data={"email": "admin@example.com", "password": "adminpassword"}
    )
    
    # Force password change for test_user
    response = client.post(
        f"/admin/users/force-password-change/{test_user.id}",
        follow_redirects=True
    )
    assert response.status_code == 200
    
    # Verify in DB
    db.refresh(test_user)
    assert test_user.force_password_change is True

def test_admin_delete_user(client, test_admin, test_user, db):
    # Log in as admin
    client.post(
        "/login",
        data={"email": "admin@example.com", "password": "adminpassword"}
    )
    
    user_id = test_user.id
    # Delete test_user
    response = client.post(
        f"/admin/users/delete/{user_id}",
        follow_redirects=True
    )
    assert response.status_code == 200
    
    # Verify in DB
    deleted_user = db.query(User).filter(User.id == user_id).first()
    assert deleted_user is None

def test_admin_delete_self_fails(client, test_admin):
    # Log in as admin
    client.post(
        "/login",
        data={"email": "admin@example.com", "password": "adminpassword"}
    )
    
    # Delete self
    response = client.post(
        f"/admin/users/delete/{test_admin.id}",
        follow_redirects=True
    )
    assert response.status_code == 400
    assert "Cannot delete yourself" in response.text
