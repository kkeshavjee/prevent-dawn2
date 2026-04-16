"""
Security utilities for authentication.
Handles password hashing, JWT tokens, and OTP generation.
"""
from datetime import datetime, timedelta
from typing import Optional
import secrets
import hashlib
import os

from passlib.context import CryptContext
from jose import jwt, JWTError
from pydantic import BaseModel

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# OTP Configuration
OTP_LENGTH = 6
OTP_EXPIRE_MINUTES = 10


class TokenData(BaseModel):
    """Token payload data."""
    user_id: str
    email: str
    role: str
    exp: datetime


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# Password Functions
def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# JWT Functions
def create_access_token(user_id: str, email: str, role: str, mfa_verified: bool = False) -> str:
    """
    Create a JWT access token.
    mfa_verified: True if the session was authenticated with MFA
    """
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": expire,
        "type": "access",
        "mfa_verified": mfa_verified
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Create a refresh token."""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
        "jti": secrets.token_urlsafe(16)  # Unique ID for revocation
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def hash_token(token: str) -> str:
    """Hash a token for storage (refresh tokens)."""
    return hashlib.sha256(token.encode()).hexdigest()


# OTP Functions
def generate_otp() -> str:
    """Generate a numeric OTP code."""
    return ''.join([str(secrets.randbelow(10)) for _ in range(OTP_LENGTH)])


def hash_otp(otp: str) -> str:
    """Hash an OTP for storage."""
    return hashlib.sha256(otp.encode()).hexdigest()


def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
    """Verify an OTP against its hash."""
    return hash_otp(plain_otp) == hashed_otp


def get_otp_expiry() -> datetime:
    """Get OTP expiration time."""
    return datetime.utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES)
