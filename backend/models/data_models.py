from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum
from backend.models.state_machine import PatientStage

class RiskLevel(str, Enum):
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"

class Biomarkers(BaseModel):
    a1c: float
    fbs: float
    systolic_bp: int
    diastolic_bp: int
    ldl: float
    hdl: float
    total_cholesterol: float
    weight: float
    height: float # in cm

    @property
    def bmi(self) -> float:
        if self.height > 0:
            return self.weight / ((self.height / 100) ** 2)
        return 0.0

class PatientProfile(BaseModel):
    user_id: str
    name: str
    age: int
    diabetes_risk_score: RiskLevel
    risk_score_numeric: int # 0-100
    biomarkers: Biomarkers
    psychographics: Dict[str, Any] = {}
    motivation_level: str = "Unknown" # Precontemplation, Contemplation, etc.
    readiness_stage: Optional[str] = None
    importance_rating: Optional[float] = None
    confidence_rating: Optional[float] = None
    barriers: List[str] = []
    facilitators: List[str] = []
    current_stage: PatientStage = PatientStage.EDUCATE_MOTIVATE # Default for new users
    physician_name: Optional[str] = "Dr. Smith"

class Message(BaseModel):
    role: str # 'user', 'assistant', 'system'
    content: str
    timestamp: Optional[str] = None

class AgentState(BaseModel):
    current_agent: str # 'intake', 'motivation', 'education', 'coaching'
    conversation_history: List[Message]
    patient_profile: PatientProfile
    context_variables: Dict[str, Any] = {}

class OrchestratorRequest(BaseModel):
    user_id: Optional[str] = None  # Ignored post-auth; user_id comes from the verified JWT
    user_input: str

class OrchestratorResponse(BaseModel):
    response: str
    suggested_actions: List[str] = []
