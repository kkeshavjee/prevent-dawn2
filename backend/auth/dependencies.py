"""
FastAPI dependencies for authentication.
Provides route-level security checks.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, UserRole
from .security import decode_token

# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user.
    Raises 401 if not authenticated or token is invalid.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # SECURITY: If user has MFA enabled, require MFA-verified session
    if user.mfa_enabled:
        mfa_verified = payload.get("mfa_verified", False)
        if not mfa_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="MFA verification required. Please log in again and complete MFA."
            )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication - returns None if not authenticated.
    Useful for endpoints that work for both authenticated and anonymous users.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory for role-based access control.
    Usage: @router.get("/admin", dependencies=[Depends(require_role(UserRole.ADMIN))])
    """
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker


# Convenience dependencies for common role checks
async def get_current_patient(current_user: User = Depends(get_current_user)) -> User:
    """Ensure current user is a patient."""
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only for patients"
        )
    return current_user


async def get_current_physician(current_user: User = Depends(get_current_user)) -> User:
    """Ensure current user is a physician."""
    if current_user.role != UserRole.PHYSICIAN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only for physicians"
        )
    return current_user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Ensure current user is an admin."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ============================================
# Verified User Dependencies (PHIPA Compliance)
# ============================================

async def get_verified_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Ensure current user has verified their email.
    Use this for sensitive endpoints that require email verification.
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required. Please verify your email before accessing this resource."
        )
    return current_user


async def get_verified_patient(current_user: User = Depends(get_verified_user)) -> User:
    """Verified patient only."""
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only for patients"
        )
    return current_user


async def get_verified_physician(current_user: User = Depends(get_verified_user)) -> User:
    """Verified physician only."""
    if current_user.role != UserRole.PHYSICIAN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only for physicians"
        )
    return current_user


async def get_verified_admin(current_user: User = Depends(get_verified_user)) -> User:
    """Verified admin only."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def require_consent(consent_type: str):
    """
    Dependency factory to check if user has given specific consent.
    Usage: @router.get("/data", dependencies=[Depends(require_consent("data_sharing"))])
    """
    from .models import ConsentRecord
    
    async def consent_checker(
        current_user: User = Depends(get_verified_user),
        db: Session = Depends(get_db)
    ):
        consent = db.query(ConsentRecord).filter(
            ConsentRecord.user_id == current_user.id,
            ConsentRecord.consent_type == consent_type,
            ConsentRecord.granted == True,
            ConsentRecord.revoked_at == None
        ).first()
        
        if not consent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Consent for '{consent_type}' is required to access this resource."
            )
        return current_user
    return consent_checker
