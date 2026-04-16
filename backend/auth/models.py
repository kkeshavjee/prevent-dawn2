"""
SQLAlchemy models for authentication system.
Defines User, Role, ConsentRecord, and OTP models.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from .database import Base


class UserRole(str, enum.Enum):
    """User roles for RBAC."""
    PATIENT = "patient"
    PHYSICIAN = "physician"
    ADMIN = "admin"


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.PATIENT, nullable=False)
    
    # Profile linkage (for patients linked to PatientProfile)
    patient_id = Column(String(50), nullable=True)  # Links to PREVENT_ID in Excel data
    
    # MFA settings
    mfa_enabled = Column(Boolean, default=False)
    mfa_method = Column(String(20), nullable=True)  # "email" or "sms"
    phone_number = Column(String(20), nullable=True)  # For SMS MFA
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)  # Email verified
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    consents = relationship("ConsentRecord", back_populates="user")
    otp_records = relationship("OTPRecord", back_populates="user")

    def __repr__(self):
        return f"<User {self.email} ({self.role.value})>"


class ConsentRecord(Base):
    """Records of user consents for PHIPA compliance."""
    __tablename__ = "consent_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    consent_type = Column(String(50), nullable=False)  # "data_collection", "physician_sharing", "research"
    granted = Column(Boolean, nullable=False)
    consent_version = Column(String(20), default="1.0")  # Track consent form versions
    
    # Audit fields
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    granted_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)

    # Relationship
    user = relationship("User", back_populates="consents")

    def __repr__(self):
        return f"<Consent {self.consent_type} for {self.user_id}: {self.granted}>"


class OTPRecord(Base):
    """OTP codes for Email/SMS MFA."""
    __tablename__ = "otp_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    code = Column(String(10), nullable=False)  # Hashed OTP code
    otp_type = Column(String(20), nullable=False)  # "email", "sms", "verification"
    
    # Validity
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)
    
    # Attempt tracking for rate limiting
    attempts = Column(String(5), default="0")
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="otp_records")

    def __repr__(self):
        return f"<OTP {self.otp_type} for {self.user_id}>"


class RefreshToken(Base):
    """Refresh tokens for session management."""
    __tablename__ = "refresh_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    token_hash = Column(String(255), nullable=False, unique=True)
    
    # Token metadata
    device_info = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # Validity
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<RefreshToken for {self.user_id}>"


class AssignmentStatus(str, enum.Enum):
    """Status of patient-physician assignment."""
    PENDING_PATIENT = "pending_patient"    # Physician invited, waiting for patient
    PENDING_PHYSICIAN = "pending_physician"  # Patient requested, waiting for physician
    APPROVED = "approved"
    REJECTED = "rejected"


class PatientPhysicianAssignment(Base):
    """
    Links patients to physicians.
    - Each patient can have at most ONE physician (unique constraint on patient_id)
    - Each physician can have multiple patients
    - Once approved, patient cannot request another physician
    """
    __tablename__ = "patient_physician_assignments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Patient can only have one physician (unique constraint)
    patient_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True)
    physician_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Who initiated the assignment
    requested_by = Column(String(20), nullable=False)  # "patient" or "physician"
    
    # Status flow
    status = Column(SQLEnum(AssignmentStatus), default=AssignmentStatus.PENDING_PATIENT, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    
    # Relationships
    patient = relationship("User", foreign_keys=[patient_id], backref="physician_assignment")
    physician = relationship("User", foreign_keys=[physician_id], backref="patient_assignments")

    def __repr__(self):
        return f"<Assignment Patient:{self.patient_id} -> Physician:{self.physician_id} ({self.status.value})>"


class PhysicianInviteCode(Base):
    """
    Admin-generated invite codes for physician registration.
    Prevents unauthorized users from registering as physicians.
    """
    __tablename__ = "physician_invite_codes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # The invite code itself (admin can specify or auto-generate)
    code = Column(String(20), unique=True, nullable=False, index=True)
    
    # Required: the physician's email - they must register with this exact email
    physician_email = Column(String(255), nullable=False, index=True)
    
    # Optional: physician name for display
    physician_name = Column(String(100), nullable=True)
    
    # Who created it
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Usage tracking
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)
    used_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    # Expiration (required)
    expires_at = Column(DateTime, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Email tracking
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PhysicianInviteCode {self.code} for {self.physician_email}>"
