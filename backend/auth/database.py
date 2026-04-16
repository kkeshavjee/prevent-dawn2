"""
Database configuration with SQLAlchemy.
Uses SQLite for development, designed for easy migration to PostgreSQL/MySQL.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
import os

# Database URL - SQLite for development, can be swapped for PostgreSQL/MySQL
# For PostgreSQL: "postgresql://user:password@localhost/dbname"
# For MySQL: "mysql+pymysql://user:password@localhost/dbname"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./prevent_auth.db")

# SQLite-specific configuration for development
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # SQLite specific
        poolclass=StaticPool,  # For SQLite thread safety
        echo=False  # Set to True for SQL debugging
    )
else:
    # PostgreSQL/MySQL configuration
    engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """
    Dependency for FastAPI routes to get database session.
    Ensures proper session cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables. Call on application startup."""
    Base.metadata.create_all(bind=engine)


def seed_admin():
    """
    Seed a default admin user for development/testing.
    In production, create admin accounts through a secure process.
    """
    from .models import User, UserRole
    from .security import hash_password
    
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if admin:
            print(f"Admin user already exists: {admin.email}")
            return
        
        # Create default admin
        admin_email = os.getenv("ADMIN_EMAIL", "admin@prevent.health")
        admin_password = os.getenv("ADMIN_PASSWORD", "AdminPass123!")
        
        admin = User(
            email=admin_email,
            hashed_password=hash_password(admin_password),
            role=UserRole.ADMIN,
            is_verified=True,  # Admin is pre-verified
            is_active=True,
            mfa_enabled=False  # Admin may enable MFA later
        )
        db.add(admin)
        db.commit()
        print(f"✓ Created admin user: {admin_email}")
        print(f"  Password: {admin_password}")
        print("  ⚠️  Change this password in production!")
    finally:
        db.close()
