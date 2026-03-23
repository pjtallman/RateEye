import os
from sqlalchemy import create_engine, Column, String, Integer, Boolean, Text, ForeignKey, Table
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./rateeye.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Many-to-Many Association Table
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)

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

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    
    users = relationship("User", secondary=user_roles, back_populates="roles")

from passlib.context import CryptContext
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
    roles = relationship("Role", secondary=user_roles, back_populates="users")

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # 1. Seed initial system settings
    log_lines = db.query(SystemSetting).filter(SystemSetting.name == "log_lines").first()
    if not log_lines:
        db.add(SystemSetting(name="log_lines", value="100"))
    
    # 2. Seed default roles
    admin_role = db.query(Role).filter(Role.name == "Admin").first()
    if not admin_role:
        admin_role = Role(name="Admin", description="System Administrator with full access")
        db.add(admin_role)
        
    user_role = db.query(Role).filter(Role.name == "User").first()
    if not user_role:
        user_role = Role(name="User", description="Standard user with limited access")
        db.add(user_role)
    
    db.commit() # Commit roles so they have IDs
    
    # 3. Seed default admin user
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        hashed_pwd = pwd_context.hash("adminpassword")
        admin_user = User(
            username="admin",
            email="admin@rateeye.local",
            hashed_password=hashed_pwd,
            is_authorized=True,
            force_password_change=True
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print("Default admin user created: admin / adminpassword")

    # Ensure admin has both roles
    if admin_role not in admin_user.roles:
        admin_user.roles.append(admin_role)
    if user_role not in admin_user.roles:
        admin_user.roles.append(user_role)
    
    db.commit()
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
