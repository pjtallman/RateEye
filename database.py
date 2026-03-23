import os
from sqlalchemy import create_engine, Column, String, Integer, Boolean, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./rateeye.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class SystemSetting(Base):
    __tablename__ = "system_settings"
    name = Column(String, primary_key=True, index=True)
    value = Column(String)

class UserSetting(Base):
    __tablename__ = "user_settings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    name = Column(String, index=True)
    value = Column(String)
    
    user = relationship("User", back_populates="settings")

from passlib.context import CryptContext

# Use the same context as main.py for seeding
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True)
    is_authorized = Column(Boolean, default=True)
    force_password_change = Column(Boolean, default=False)
    provider = Column(String, default="local")
    profile_json = Column(Text, nullable=True)
    
    settings = relationship("UserSetting", back_populates="user", cascade="all, delete-orphan")

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Seed initial system settings
    log_lines = db.query(SystemSetting).filter(SystemSetting.name == "log_lines").first()
    if not log_lines:
        db.add(SystemSetting(name="log_lines", value="100"))
        db.commit()

    # Seed default admin user if no users exist
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        hashed_pwd = pwd_context.hash("adminpassword")
        new_admin = User(
            username="admin",
            email="admin@rateeye.local",
            hashed_password=hashed_pwd,
            is_authorized=True,
            force_password_change=True # Best practice: force change on first login
        )
        db.add(new_admin)
        db.commit()
        print("Default admin user created: admin / adminpassword")

    db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_system_setting(db: Session, name: str, default: str):
    res = db.query(SystemSetting).filter(SystemSetting.name == name).first()
    return res.value if res else default
