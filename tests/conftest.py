import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Must set this before importing app or database
os.environ["DATABASE_URL"] = "sqlite:///./test_rateeye.db"

from database import Base, get_db, User, UserSetting, SystemSetting, Role, pwd_context, user_roles
from main import app

# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_rateeye.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    # Ensure we are using the test database
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Initialize some system settings if needed
    db = TestingSessionLocal()
    if not db.query(SystemSetting).filter(SystemSetting.name == "log_lines").first():
        db.add(SystemSetting(name="log_lines", value="100"))
    
    # Seed default roles for tests
    if not db.query(Role).filter(Role.name == "Admin").first():
        db.add(Role(name="Admin", description="Admin Role"))
    if not db.query(Role).filter(Role.name == "User").first():
        db.add(Role(name="User", description="User Role"))
        
    db.commit()
    db.close()
    
    yield
    
    # Cleanup after all tests
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_rateeye.db"):
        os.remove("./test_rateeye.db")

@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    # We want to start each test with a clean-ish database, 
    # but keep the seeded roles.
    # Clear users and user_roles, but keep Roles.
    session.execute(user_roles.delete())
    session.query(User).delete()
    session.commit()

    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass # Session is managed by the fixture

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(db):
    hashed_pwd = pwd_context.hash("testpassword")
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hashed_pwd,
        is_authorized=True,
        force_password_change=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def test_admin(db):
    hashed_pwd = pwd_context.hash("adminpassword")
    user = User(
        username="adminuser",
        email="admin@example.com",
        hashed_password=hashed_pwd,
        is_authorized=True,
        force_password_change=False
    )
    # Give it admin role
    admin_role = db.query(Role).filter(Role.name == "Admin").first()
    user.roles.append(admin_role)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
