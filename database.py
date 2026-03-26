import os
from enum import Enum
from sqlalchemy import create_engine, Column, String, Integer, Boolean, Text, ForeignKey, Table, Enum as SQLEnum
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./rateeye.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class PageType(str, Enum):
    MAINTENANCE = "Maintenance"
    SETTINGS = "Settings"
    INFO = "Info"

class PermissionLevel(str, Enum):
    CREATE = "Create"
    UPDATE = "Update"
    DELETE = "Delete"
    READ = "Read"
    FULL = "Full"
    NONE = "None"

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

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, index=True)
    page_path = Column(String, nullable=False) # e.g. "/admin/users"
    page_type = Column(SQLEnum(PageType), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    level = Column(SQLEnum(PermissionLevel), nullable=False, default=PermissionLevel.NONE)

    role = relationship("Role", back_populates="permissions")
    user = relationship("User", back_populates="permissions")

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", back_populates="role", cascade="all, delete-orphan")

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
    photo_url = Column(String, nullable=True)
    
    settings = relationship("UserSetting", back_populates="user", cascade="all, delete-orphan")
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    permissions = relationship("Permission", back_populates="user", cascade="all, delete-orphan")

def init_db(db: Session = None):
    Base.metadata.create_all(bind=engine)
    standalone = False
    if db is None:
        db = SessionLocal()
        standalone = True
    
    # 1. Seed initial system settings
    log_lines = db.query(SystemSetting).filter(SystemSetting.name == "log_lines").first()
    if not log_lines:
        db.add(SystemSetting(name="log_lines", value="100"))

    # Sync version from file system
    if os.path.exists("VERSION"):
        with open("VERSION", "r") as f:
            current_version = f.read().strip()
            if current_version:
                version_setting = db.query(SystemSetting).filter(SystemSetting.name == "version").first()
                if not version_setting:
                    db.add(SystemSetting(name="version", value=current_version))
                elif version_setting.value != current_version:
                    version_setting.value = current_version
    
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

    # 3. Seed default permissions for roles
    # Identify unique pages from database.py get_pages()
    pages_list = get_pages()

    admin_menu_pages = ["/admin/roles", "/admin/permissions", "/admin/users", "/settings/system"]

    # Clear old type-based permissions to avoid confusion during this migration
    db.query(Permission).filter(Permission.page_path == None).delete()

    for path, pt, label_key in pages_list:
        # Admin Role: Gets FULL for all pages
        existing_admin = db.query(Permission).filter(
            Permission.role_id == admin_role.id,
            Permission.page_path == path
        ).first()
        if not existing_admin:
            db.add(Permission(role_id=admin_role.id, page_path=path, page_type=pt, level=PermissionLevel.FULL))

        # User Role: 
        # NONE for Admin menu pages, FULL for others
        existing_user = db.query(Permission).filter(
            Permission.role_id == user_role.id,
            Permission.page_path == path
        ).first()
        if not existing_user:
            level = PermissionLevel.NONE if path in admin_menu_pages else PermissionLevel.FULL
            db.add(Permission(role_id=user_role.id, page_path=path, page_type=pt, level=level))
    
    db.commit()
    
    # 4. Seed default admin user
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

    # Ensure admin user has Admin role
    if admin_role not in admin_user.roles:
        admin_user.roles.append(admin_role)
    if user_role not in admin_user.roles:
        admin_user.roles.append(user_role)
    
    db.commit()
    if standalone:
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

def get_pages():
    """Returns the master list of pages, their types, and their translation keys."""
    return [
        ("/", PageType.INFO, "item_home"),
        ("/register", PageType.INFO, "nav_register"),
        ("/forgot-password", PageType.INFO, "link_forgot_password"),
        ("/login", PageType.INFO, "nav_login"),
        ("/logout", PageType.INFO, "nav_logout"),
        ("/show-log", PageType.INFO, "item_show_log"),
        ("/about", PageType.INFO, "item_about"),
        ("/change-password", PageType.INFO, "heading_change_password"),
        ("/settings/user", PageType.SETTINGS, "item_user_settings"),
        ("/settings/user/change-username", PageType.SETTINGS, "link_change_username"),
        ("/settings/user/change-password", PageType.SETTINGS, "link_change_password"),
        ("/settings/user/upload-photo", PageType.SETTINGS, "label_profile_photo"),
        ("/settings/system", PageType.SETTINGS, "item_system_settings"),
        ("/admin/users", PageType.MAINTENANCE, "item_users"),
        ("/admin/roles", PageType.MAINTENANCE, "item_roles"),
        ("/admin/securities", PageType.MAINTENANCE, "item_securities"),
        ("/admin/permissions", PageType.MAINTENANCE, "item_permissions"),
    ]
