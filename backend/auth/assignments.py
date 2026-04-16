"""
Patient-Physician Assignment API.
Handles bidirectional invitations and assignments.
"""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from .database import get_db
from .models import User, UserRole, PatientPhysicianAssignment, AssignmentStatus
from .dependencies import get_verified_user, get_verified_patient, get_verified_physician

router = APIRouter(prefix="/auth/assignments", tags=["Patient-Physician Assignments"])


# ============================================
# Schemas
# ============================================

class InvitePatientRequest(BaseModel):
    patient_email: EmailStr


class RequestPhysicianRequest(BaseModel):
    physician_email: EmailStr


class AssignmentResponse(BaseModel):
    id: str
    patient_id: str
    patient_email: str
    physician_id: str
    physician_email: str
    status: str
    requested_by: str
    created_at: datetime
    approved_at: datetime | None = None

    class Config:
        from_attributes = True


class PatientListResponse(BaseModel):
    patients: List[AssignmentResponse]
    total: int


class PhysicianResponse(BaseModel):
    physician_id: str | None = None
    physician_email: str | None = None
    status: str | None = None
    has_physician: bool = False


# ============================================
# Physician Endpoints
# ============================================

@router.post("/physician/invite-patient", response_model=AssignmentResponse)
async def physician_invite_patient(
    request: InvitePatientRequest,
    current_user: User = Depends(get_verified_physician),
    db: Session = Depends(get_db)
):
    """
    Physician invites a patient by email.
    Patient must accept the invitation.
    """
    # Find patient
    patient = db.query(User).filter(
        User.email == request.patient_email,
        User.role == UserRole.PATIENT
    ).first()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient with this email not found"
        )
    
    # Check if patient already has an assignment
    existing = db.query(PatientPhysicianAssignment).filter(
        PatientPhysicianAssignment.patient_id == patient.id
    ).first()
    
    if existing:
        if existing.status == AssignmentStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This patient is already assigned to a physician"
            )
        elif existing.status in [AssignmentStatus.PENDING_PATIENT, AssignmentStatus.PENDING_PHYSICIAN]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This patient has a pending invitation"
            )
    
    # Create assignment
    assignment = PatientPhysicianAssignment(
        patient_id=patient.id,
        physician_id=current_user.id,
        requested_by="physician",
        status=AssignmentStatus.PENDING_PATIENT
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    
    return AssignmentResponse(
        id=assignment.id,
        patient_id=patient.id,
        patient_email=patient.email,
        physician_id=current_user.id,
        physician_email=current_user.email,
        status=assignment.status.value,
        requested_by=assignment.requested_by,
        created_at=assignment.created_at,
        approved_at=assignment.approved_at
    )


@router.get("/physician/my-patients", response_model=PatientListResponse)
async def get_my_patients(
    current_user: User = Depends(get_verified_physician),
    db: Session = Depends(get_db)
):
    """Get all patients assigned to this physician."""
    assignments = db.query(PatientPhysicianAssignment).filter(
        PatientPhysicianAssignment.physician_id == current_user.id
    ).all()
    
    result = []
    for a in assignments:
        patient = db.query(User).filter(User.id == a.patient_id).first()
        result.append(AssignmentResponse(
            id=a.id,
            patient_id=a.patient_id,
            patient_email=patient.email if patient else "",
            physician_id=a.physician_id,
            physician_email=current_user.email,
            status=a.status.value,
            requested_by=a.requested_by,
            created_at=a.created_at,
            approved_at=a.approved_at
        ))
    
    return PatientListResponse(patients=result, total=len(result))


# ============================================
# Patient Endpoints
# ============================================

@router.post("/patient/request-physician", response_model=AssignmentResponse)
async def patient_request_physician(
    request: RequestPhysicianRequest,
    current_user: User = Depends(get_verified_patient),
    db: Session = Depends(get_db)
):
    """
    Patient requests a physician by email.
    Physician must accept the request.
    """
    # Check if patient already has an assignment
    existing = db.query(PatientPhysicianAssignment).filter(
        PatientPhysicianAssignment.patient_id == current_user.id
    ).first()
    
    if existing:
        if existing.status == AssignmentStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already assigned to a physician"
            )
        elif existing.status in [AssignmentStatus.PENDING_PATIENT, AssignmentStatus.PENDING_PHYSICIAN]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have a pending invitation. Please respond to it first."
            )
    
    # Find physician
    physician = db.query(User).filter(
        User.email == request.physician_email,
        User.role == UserRole.PHYSICIAN
    ).first()
    
    if not physician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physician with this email not found"
        )
    
    # Create assignment
    assignment = PatientPhysicianAssignment(
        patient_id=current_user.id,
        physician_id=physician.id,
        requested_by="patient",
        status=AssignmentStatus.PENDING_PHYSICIAN
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    
    return AssignmentResponse(
        id=assignment.id,
        patient_id=current_user.id,
        patient_email=current_user.email,
        physician_id=physician.id,
        physician_email=physician.email,
        status=assignment.status.value,
        requested_by=assignment.requested_by,
        created_at=assignment.created_at,
        approved_at=assignment.approved_at
    )


@router.get("/patient/my-physician", response_model=PhysicianResponse)
async def get_my_physician(
    current_user: User = Depends(get_verified_patient),
    db: Session = Depends(get_db)
):
    """Get the patient's assigned physician."""
    assignment = db.query(PatientPhysicianAssignment).filter(
        PatientPhysicianAssignment.patient_id == current_user.id
    ).first()
    
    if not assignment:
        return PhysicianResponse(has_physician=False)
    
    physician = db.query(User).filter(User.id == assignment.physician_id).first()
    
    return PhysicianResponse(
        physician_id=assignment.physician_id,
        physician_email=physician.email if physician else None,
        status=assignment.status.value,
        has_physician=assignment.status == AssignmentStatus.APPROVED
    )


# ============================================
# Common Endpoints (Approve/Reject)
# ============================================

@router.post("/{assignment_id}/approve")
async def approve_assignment(
    assignment_id: str,
    current_user: User = Depends(get_verified_user),
    db: Session = Depends(get_db)
):
    """Approve a pending assignment."""
    assignment = db.query(PatientPhysicianAssignment).filter(
        PatientPhysicianAssignment.id == assignment_id
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Check authorization
    if assignment.status == AssignmentStatus.PENDING_PATIENT:
        # Patient needs to approve
        if current_user.id != assignment.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the patient can approve this invitation"
            )
    elif assignment.status == AssignmentStatus.PENDING_PHYSICIAN:
        # Physician needs to approve
        if current_user.id != assignment.physician_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the physician can approve this request"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve assignment with status: {assignment.status.value}"
        )
    
    # Approve
    assignment.status = AssignmentStatus.APPROVED
    assignment.approved_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Assignment approved successfully", "success": True}


@router.post("/{assignment_id}/reject")
async def reject_assignment(
    assignment_id: str,
    current_user: User = Depends(get_verified_user),
    db: Session = Depends(get_db)
):
    """Reject a pending assignment."""
    assignment = db.query(PatientPhysicianAssignment).filter(
        PatientPhysicianAssignment.id == assignment_id
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Check authorization - either party can reject
    if current_user.id not in [assignment.patient_id, assignment.physician_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to reject this assignment"
        )
    
    if assignment.status == AssignmentStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reject an approved assignment"
        )
    
    # Delete the assignment so patient can try again
    db.delete(assignment)
    db.commit()
    
    return {"message": "Assignment rejected and removed", "success": True}


@router.get("/pending")
async def get_pending_assignments(
    current_user: User = Depends(get_verified_user),
    db: Session = Depends(get_db)
):
    """Get pending assignments for the current user."""
    if current_user.role == UserRole.PHYSICIAN:
        # Physician sees patient requests pending their approval
        assignments = db.query(PatientPhysicianAssignment).filter(
            PatientPhysicianAssignment.physician_id == current_user.id,
            PatientPhysicianAssignment.status == AssignmentStatus.PENDING_PHYSICIAN
        ).all()
    elif current_user.role == UserRole.PATIENT:
        # Patient sees physician invitations pending their approval
        assignments = db.query(PatientPhysicianAssignment).filter(
            PatientPhysicianAssignment.patient_id == current_user.id,
            PatientPhysicianAssignment.status == AssignmentStatus.PENDING_PATIENT
        ).all()
    else:
        assignments = []
    
    result = []
    for a in assignments:
        patient = db.query(User).filter(User.id == a.patient_id).first()
        physician = db.query(User).filter(User.id == a.physician_id).first()
        result.append({
            "id": a.id,
            "patient_email": patient.email if patient else "",
            "physician_email": physician.email if physician else "",
            "status": a.status.value,
            "requested_by": a.requested_by,
            "created_at": a.created_at.isoformat()
        })
    
    return {"pending": result, "count": len(result)}


# ============================================
# Physician Patient Data Access (Phase 3)
# ============================================

class PatientProfileResponse(BaseModel):
    """Patient profile visible to assigned physician."""
    id: str
    email: str
    phone_number: str | None = None
    is_verified: bool
    mfa_enabled: bool
    created_at: datetime
    # Add health data fields as needed


@router.get("/physician/patient/{patient_id}/profile", response_model=PatientProfileResponse)
async def get_patient_profile(
    patient_id: str,
    current_user: User = Depends(get_verified_physician),
    db: Session = Depends(get_db)
):
    """
    Get a patient's profile. 
    Only accessible if physician has an APPROVED assignment with the patient.
    """
    # Verify assignment exists and is approved
    assignment = db.query(PatientPhysicianAssignment).filter(
        PatientPhysicianAssignment.physician_id == current_user.id,
        PatientPhysicianAssignment.patient_id == patient_id,
        PatientPhysicianAssignment.status == AssignmentStatus.APPROVED
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this patient's data. Assignment required."
        )
    
    # Get patient
    patient = db.query(User).filter(User.id == patient_id).first()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    return PatientProfileResponse(
        id=patient.id,
        email=patient.email,
        phone_number=patient.phone_number,
        is_verified=patient.is_verified,
        mfa_enabled=patient.mfa_enabled,
        created_at=patient.created_at
    )

