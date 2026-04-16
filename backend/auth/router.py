"""
Authentication API router.
Handles registration, login, MFA, token refresh, and user profile.
"""
from datetime import datetime, timedelta
from typing import Union
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, UserRole, ConsentRecord, RefreshToken, PhysicianInviteCode
from .schemas import (
    RegisterRequest, RegisterResponse,
    LoginRequest, LoginResponse, MFARequiredResponse,
    MFAVerifyRequest, MFAEnableRequest, MFAStatusResponse,
    RefreshRequest, RefreshResponse,
    UserProfileResponse, ConsentResponse,
    PasswordResetRequest, PasswordResetConfirm,
    MessageResponse,
    CreateInviteCodeRequest, InviteCodeResponse, InviteCodeListResponse
)
from .security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, hash_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from .dependencies import get_current_user, get_current_admin, get_current_physician, get_current_patient
from .mfa import MFAService

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Temporary tokens for MFA flow (in production, use Redis)
_mfa_pending: dict = {}


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    Requires consent for data collection.
    """
    # Check if email already exists
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate required consents - support both flat field and array formats
    data_collection_granted = False
    
    # Check flat field first (preferred)
    if request.consent_data_collection:
        data_collection_granted = True
    
    # Also check legacy array format
    for c in request.consents:
        if c.consent_type == "data_collection" and c.granted:
            data_collection_granted = True
            break
    
    if not data_collection_granted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent for data collection is required. Set consent_data_collection: true"
        )
    
    # Validate physician invite code if registering as physician
    invite_code_record = None
    if request.role == UserRole.PHYSICIAN:
        if not request.physician_invite_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Physician registration requires an invite code. Contact an administrator."
            )
        
        # Look up the invite code
        invite_code_record = db.query(PhysicianInviteCode).filter(
            PhysicianInviteCode.code == request.physician_invite_code.upper(),
            PhysicianInviteCode.is_active == True,
            PhysicianInviteCode.is_used == False
        ).first()
        
        if not invite_code_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired physician invite code"
            )
        
        # Check expiration
        if invite_code_record.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invite code has expired"
            )
        
        # MANDATORY: Email must match the invite code's email
        if invite_code_record.physician_email.lower() != request.email.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must register with the email address the invite code was sent to"
            )
    
    # Create user
    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        role=request.role,
        patient_id=request.patient_id,
        phone_number=request.phone_number
    )
    db.add(user)
    db.flush()  # Get user ID
    
    # Record consents
    client_ip = req.client.host if req.client else None
    user_agent = req.headers.get("user-agent")
    
    # Save consents from flat fields
    if request.consent_data_collection:
        consent = ConsentRecord(
            user_id=user.id,
            consent_type="data_collection",
            granted=True,
            ip_address=client_ip,
            user_agent=user_agent
        )
        db.add(consent)
    
    if request.consent_data_sharing:
        consent = ConsentRecord(
            user_id=user.id,
            consent_type="data_sharing",
            granted=True,
            ip_address=client_ip,
            user_agent=user_agent
        )
        db.add(consent)
    
    # Also save from legacy array format (if provided)
    for consent_input in request.consents:
        consent = ConsentRecord(
            user_id=user.id,
            consent_type=consent_input.consent_type,
            granted=consent_input.granted,
            ip_address=client_ip,
            user_agent=user_agent
        )
        db.add(consent)
    
    # Auto-enable MFA with chosen method during registration
    user.mfa_enabled = True
    user.mfa_method = request.mfa_method
    
    # Validate phone number if SMS MFA chosen
    if request.mfa_method == "sms" and not request.phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is required for SMS MFA"
        )
    
    # Mark physician invite code as used
    if invite_code_record:
        invite_code_record.is_used = True
        invite_code_record.used_at = datetime.utcnow()
        invite_code_record.used_by = user.id
    
    db.commit()
    
    # Note: No verification email sent here - it will be combined with first MFA login
    
    return RegisterResponse(
        user_id=user.id,
        email=user.email,
        role=user.role.value,
        message="Registration successful. Please log in to verify your identity.",
        requires_verification=True
    )


@router.post("/login", response_model=Union[LoginResponse, MFARequiredResponse])
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user with email and password.
    Returns tokens if MFA is disabled, or initiates MFA flow.
    """
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Check if MFA is enabled
    if user.mfa_enabled:
        # Generate MFA token and OTP
        mfa_token = secrets.token_urlsafe(32)
        _mfa_pending[mfa_token] = {
            "user_id": user.id,
            "created_at": datetime.utcnow(),
            "also_verifies_email": not user.is_verified  # Track if email needs verification
        }
        
        # Send OTP
        mfa_svc = MFAService(db)
        otp = mfa_svc.generate_and_save_otp(user, "mfa")
        await mfa_svc.send_otp(user, otp, "mfa")
        
        # Inform user if this OTP will also verify their email
        message = "MFA verification required"
        if not user.is_verified:
            message = "Enter the verification code to verify your email and complete login"
        
        return MFARequiredResponse(
            mfa_required=True,
            mfa_method=user.mfa_method or "email",
            mfa_token=mfa_token,
            message=message,
            also_verifies_email=not user.is_verified
        )
    
    # No MFA - generate tokens directly (mfa_verified=False)
    access_token = create_access_token(user.id, user.email, user.role.value, mfa_verified=False)
    refresh_token = create_refresh_token(user.id)
    
    # Save refresh token
    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.utcnow() + __import__("datetime").timedelta(days=7)
    )
    db.add(rt)
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        email=user.email,
        role=user.role.value,
        mfa_required=False
    )


@router.post("/verify-mfa", response_model=LoginResponse)
async def verify_mfa(
    request: MFAVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Verify MFA code and complete login.
    """
    # Validate MFA token
    pending = _mfa_pending.get(request.mfa_token)
    if not pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired MFA session"
        )
    
    # Check expiry (5 minutes)
    age = (datetime.utcnow() - pending["created_at"]).total_seconds()
    if age > 300:
        del _mfa_pending[request.mfa_token]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA session expired. Please login again."
        )
    
    # Get user
    user = db.query(User).filter(User.id == pending["user_id"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    # Verify OTP
    mfa_svc = MFAService(db)
    success, message = mfa_svc.verify_user_otp(user, request.otp_code, "mfa")
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Also verify email if this MFA session was meant to verify email too
    if pending.get("also_verifies_email") and not user.is_verified:
        user.is_verified = True
    
    # Clean up pending
    del _mfa_pending[request.mfa_token]
    
    # Generate tokens (MFA verified!)
    access_token = create_access_token(user.id, user.email, user.role.value, mfa_verified=True)
    refresh_token = create_refresh_token(user.id)
    
    # Save refresh token
    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.utcnow() + __import__("datetime").timedelta(days=7)
    )
    db.add(rt)
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        email=user.email,
        role=user.role.value,
        mfa_required=False
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    request: RefreshRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    # Decode refresh token
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Check if token is revoked
    token_hash = hash_token(request.refresh_token)
    stored = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False
    ).first()
    
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked or not found"
        )
    
    # Get user
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled"
        )
    
    # Generate new access token
    access_token = create_access_token(user.id, user.email, user.role.value)
    
    return RefreshResponse(access_token=access_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout user by revoking all refresh tokens.
    """
    db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id,
        RefreshToken.revoked == False
    ).update({
        "revoked": True,
        "revoked_at": datetime.utcnow()
    })
    db.commit()
    
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserProfileResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role.value,
        patient_id=current_user.patient_id,
        mfa_enabled=current_user.mfa_enabled,
        mfa_method=current_user.mfa_method,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@router.post("/mfa/enable", response_model=MessageResponse)
async def enable_mfa(
    request: MFAEnableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enable MFA for current user.
    SECURITY: Revokes all existing sessions - user must re-login with MFA.
    """
    if request.method == "sms" and not request.phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number required for SMS MFA"
        )
    
    current_user.mfa_enabled = True
    current_user.mfa_method = request.method
    if request.phone_number:
        current_user.phone_number = request.phone_number
    
    # SECURITY: Revoke all existing refresh tokens to force re-login with MFA
    db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id,
        RefreshToken.revoked == False
    ).update({"revoked": True})
    
    db.commit()
    
    return MessageResponse(
        message=f"MFA enabled via {request.method}. Please log in again to verify with MFA.",
        success=True
    )


@router.post("/mfa/disable", response_model=MessageResponse)
async def disable_mfa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable MFA for current user."""
    current_user.mfa_enabled = False
    db.commit()
    
    return MessageResponse(message="MFA disabled")


@router.get("/mfa/status", response_model=MFAStatusResponse)
async def mfa_status(current_user: User = Depends(get_current_user)):
    """Get MFA status for current user."""
    return MFAStatusResponse(
        mfa_enabled=current_user.mfa_enabled,
        mfa_method=current_user.mfa_method
    )


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    otp_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify user email with OTP."""
    mfa_svc = MFAService(db)
    success, message = mfa_svc.verify_user_otp(current_user, otp_code, "verification")
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    current_user.is_verified = True
    db.commit()
    
    return MessageResponse(message="Email verified successfully")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resend email verification OTP."""
    if current_user.is_verified:
        return MessageResponse(message="Email already verified")
    
    mfa_svc = MFAService(db)
    otp = mfa_svc.generate_and_save_otp(current_user, "verification")
    await mfa_svc.send_otp_email(current_user.email, otp, "verification")
    
    return MessageResponse(message="Verification code sent")


# ============================================
# RBAC Test Endpoints
# ============================================

@router.get("/admin/dashboard", response_model=MessageResponse)
async def admin_dashboard(current_user: User = Depends(get_current_admin)):
    """Admin-only endpoint. Returns 403 for non-admin users."""
    return MessageResponse(
        message=f"Welcome Admin {current_user.email}! You have access to the admin dashboard."
    )


@router.get("/physician/patients", response_model=MessageResponse)
async def physician_patients(current_user: User = Depends(get_current_physician)):
    """Physician-only endpoint. Returns 403 for non-physician users."""
    return MessageResponse(
        message=f"Welcome Dr. {current_user.email}! You can view your patient cohorts here."
    )


@router.get("/patient/health-data", response_model=MessageResponse)
async def patient_health_data(current_user: User = Depends(get_current_patient)):
    """Patient-only endpoint. Returns 403 for non-patient users."""
    return MessageResponse(
        message=f"Welcome {current_user.email}! Here is your health data dashboard."
    )


@router.get("/all-users", response_model=MessageResponse)
async def all_users_endpoint(current_user: User = Depends(get_current_user)):
    """Any authenticated user can access this endpoint."""
    return MessageResponse(
        message=f"Hello {current_user.email}! Your role is: {current_user.role.value}"
    )


# ============================================
# Consent Management (PHIPA Compliance)
# ============================================

from pydantic import BaseModel
from typing import List

class ConsentRequest(BaseModel):
    consent_type: str  # 'data_collection', 'data_sharing', 'research', 'marketing'
    granted: bool


class ConsentListResponse(BaseModel):
    consents: List[ConsentResponse]


@router.post("/consent", response_model=ConsentResponse)
async def manage_consent(
    request: ConsentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Grant or revoke consent."""
    # Check if consent record exists
    consent = db.query(ConsentRecord).filter(
        ConsentRecord.user_id == current_user.id,
        ConsentRecord.consent_type == request.consent_type
    ).first()
    
    if consent:
        if request.granted:
            # Re-granting consent
            consent.granted = True
            consent.revoked_at = None
            consent.granted_at = datetime.utcnow()
        else:
            # Revoking consent
            consent.granted = False
            consent.revoked_at = datetime.utcnow()
    else:
        # Create new consent record
        consent = ConsentRecord(
            user_id=current_user.id,
            consent_type=request.consent_type,
            granted=request.granted,
            granted_at=datetime.utcnow() if request.granted else None,
            revoked_at=datetime.utcnow() if not request.granted else None
        )
        db.add(consent)
    
    db.commit()
    db.refresh(consent)
    
    return ConsentResponse(
        id=consent.id,
        consent_type=consent.consent_type,
        granted=consent.granted,
        granted_at=consent.granted_at,
        revoked_at=consent.revoked_at
    )


@router.get("/consents", response_model=ConsentListResponse)
async def get_consents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all consent records for the current user."""
    consents = db.query(ConsentRecord).filter(
        ConsentRecord.user_id == current_user.id
    ).all()
    
    return ConsentListResponse(
        consents=[
            ConsentResponse(
                id=c.id,
                consent_type=c.consent_type,
                granted=c.granted,
                granted_at=c.granted_at,
                revoked_at=c.revoked_at
            ) for c in consents
        ]
    )


# ==================== Admin: Physician Invite Codes ====================

def generate_invite_code(length: int = 8) -> str:
    """Generate a random alphanumeric invite code."""
    chars = string.ascii_uppercase + string.digits
    # Exclude confusing characters
    chars = chars.replace('0', '').replace('O', '').replace('I', '').replace('1', '')
    return ''.join(secrets.choice(chars) for _ in range(length))


@router.post("/admin/invite-codes", response_model=InviteCodeResponse)
async def create_invite_code(
    request: CreateInviteCodeRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Create a physician invite code (Admin only).
    The code can be given to a physician to allow them to register.
    """
    # Generate or use provided code
    code = request.code or generate_invite_code()
    
    # Check if code already exists
    existing = db.query(PhysicianInviteCode).filter(PhysicianInviteCode.code == code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This code already exists. Please use a different code."
        )
    
    # Check if email already has an unused invite
    existing_for_email = db.query(PhysicianInviteCode).filter(
        PhysicianInviteCode.physician_email == request.physician_email.lower(),
        PhysicianInviteCode.is_used == False,
        PhysicianInviteCode.is_active == True
    ).first()
    if existing_for_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An active invite code already exists for {request.physician_email}"
        )
    
    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
    
    invite = PhysicianInviteCode(
        code=code.upper(),  # Standardize to uppercase
        physician_email=request.physician_email.lower(),  # Standardize to lowercase
        physician_name=request.physician_name,
        created_by=current_user.id,
        expires_at=expires_at
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    
    # Send invite email
    mfa_service = MFAService(db)
    email_sent = await mfa_service.send_physician_invite_email(
        email=invite.physician_email,
        invite_code=invite.code,
        physician_name=invite.physician_name,
        expires_at=invite.expires_at.strftime("%B %d, %Y at %H:%M UTC") if invite.expires_at else None
    )
    
    # Update email_sent status
    if email_sent:
        invite.email_sent = True
        invite.email_sent_at = datetime.utcnow()
        db.commit()
        db.refresh(invite)
    
    return InviteCodeResponse(
        id=invite.id,
        code=invite.code,
        physician_email=invite.physician_email,
        physician_name=invite.physician_name,
        is_used=invite.is_used,
        used_at=invite.used_at,
        expires_at=invite.expires_at,
        is_active=invite.is_active,
        created_at=invite.created_at,
        email_sent=invite.email_sent
    )


@router.get("/admin/invite-codes", response_model=InviteCodeListResponse)
async def list_invite_codes(
    include_used: bool = False,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    List all physician invite codes (Admin only).
    By default excludes used codes.
    """
    query = db.query(PhysicianInviteCode)
    if not include_used:
        query = query.filter(PhysicianInviteCode.is_used == False)
    
    codes = query.order_by(PhysicianInviteCode.created_at.desc()).all()
    
    return InviteCodeListResponse(
        codes=[
            InviteCodeResponse(
                id=c.id,
                code=c.code,
                physician_email=c.physician_email,
                physician_name=c.physician_name,
                is_used=c.is_used,
                used_at=c.used_at,
                expires_at=c.expires_at,
                is_active=c.is_active,
                created_at=c.created_at,
                email_sent=c.email_sent
            ) for c in codes
        ],
        total=len(codes)
    )


@router.delete("/admin/invite-codes/{code_id}", response_model=MessageResponse)
async def delete_invite_code(
    code_id: str,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Delete/deactivate a physician invite code (Admin only).
    """
    invite = db.query(PhysicianInviteCode).filter(PhysicianInviteCode.id == code_id).first()
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite code not found"
        )
    
    # Don't delete used codes, just deactivate
    if invite.is_used:
        invite.is_active = False
        db.commit()
        return MessageResponse(message="Invite code deactivated (already used)")
    
    db.delete(invite)
    db.commit()
    return MessageResponse(message="Invite code deleted")
