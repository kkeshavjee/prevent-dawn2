"""
Pydantic schemas for auth API requests and responses.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

from .models import UserRole


# --- Registration ---
class ConsentInput(BaseModel):
    """Consent checkbox input during registration."""
    consent_type: str  # "data_collection", "physician_sharing"
    granted: bool


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    role: UserRole = UserRole.PATIENT
    patient_id: Optional[str] = None  # For linking to existing patient profile
    phone_number: Optional[str] = None  # For SMS MFA
    mfa_method: str = Field(default="email", pattern="^(email|sms)$")  # MFA method choice
    physician_invite_code: Optional[str] = None  # Required if role is physician
    # Simple consent flags (preferred)
    consent_data_collection: bool = False
    consent_data_sharing: bool = False  # Optional additional consent
    # Legacy array format (also supported)
    consents: List[ConsentInput] = []


class RegisterResponse(BaseModel):
    """Registration success response."""
    user_id: str
    email: str
    role: str
    message: str = "Registration successful. Please verify your email."
    requires_verification: bool = True


# --- Login ---
class LoginRequest(BaseModel):
    """Login request."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response (when MFA is not required or after MFA)."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str
    mfa_required: bool = False


class MFARequiredResponse(BaseModel):
    """Response when MFA verification is needed."""
    mfa_required: bool = True
    mfa_method: str  # "email" or "sms"
    mfa_token: str  # Temporary token to use for MFA verification
    message: str = "MFA verification required"
    also_verifies_email: bool = False  # True if this OTP will also verify email


# --- MFA ---
class MFAVerifyRequest(BaseModel):
    """MFA verification request."""
    mfa_token: str
    otp_code: str = Field(..., min_length=6, max_length=6)


class MFAEnableRequest(BaseModel):
    """Enable MFA request."""
    method: str = Field(..., pattern="^(email|sms)$")
    phone_number: Optional[str] = None  # Required if method is "sms"


class MFAStatusResponse(BaseModel):
    """MFA status response."""
    mfa_enabled: bool
    mfa_method: Optional[str] = None


# --- Token Refresh ---
class RefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class RefreshResponse(BaseModel):
    """Token refresh response."""
    access_token: str
    token_type: str = "bearer"


# --- User Profile ---
class UserProfileResponse(BaseModel):
    """User profile response."""
    id: str
    email: str
    role: str
    patient_id: Optional[str] = None
    mfa_enabled: bool
    mfa_method: Optional[str] = None
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConsentResponse(BaseModel):
    """Consent record response."""
    consent_type: str
    granted: bool
    granted_at: datetime
    consent_version: str


# --- Password Reset ---
class PasswordResetRequest(BaseModel):
    """Request password reset."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Confirm password reset with OTP."""
    email: EmailStr
    otp_code: str
    new_password: str = Field(..., min_length=8)


# --- General ---
class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    success: bool = True


# --- Physician Invite Codes (Admin) ---
class CreateInviteCodeRequest(BaseModel):
    """Admin request to create a physician invite code."""
    code: Optional[str] = None  # If not provided, auto-generate
    physician_email: EmailStr  # Required: invite code is sent to this email
    physician_name: Optional[str] = None  # Display name for the physician
    expires_in_days: int = 7  # Default: code expires in 7 days


class InviteCodeResponse(BaseModel):
    """Response for invite code."""
    id: str
    code: str
    physician_email: str  # The email this code was sent to
    physician_name: Optional[str] = None
    is_used: bool
    used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    email_sent: bool = False  # Whether the invite email was sent

    class Config:
        from_attributes = True


class InviteCodeListResponse(BaseModel):
    """List of invite codes."""
    codes: List[InviteCodeResponse]
    total: int
