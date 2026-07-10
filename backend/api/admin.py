from fastapi import APIRouter, Depends
from typing import List
from pydantic import BaseModel
from backend.auth.rbac import require_role, ADMIN
from backend.auth.dependencies import CurrentUser

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_role(ADMIN))])

# We need a way to access the orchestrator instance.
# For now, we'll import it from main (circular import risk, but okay for MVP if structured right,
# or better, dependency injection).
# simplified: We will re-instantiate or share state via a singleton pattern in a real app.
# For this mock, I'll just return mock data.

class AgentConfig(BaseModel):
    name: str
    description: str
    status: str

class ConversationLog(BaseModel):
    user_id: str
    message_count: int
    last_active: str

@router.get("/agents", response_model=List[AgentConfig])
async def get_agents():
    return [
        AgentConfig(name="Intake Agent", description="Handles onboarding", status="Active"),
        AgentConfig(name="Motivation Agent", description="Assesses readiness", status="Active"),
        AgentConfig(name="Education Agent", description="Delivers content", status="Active"),
        AgentConfig(name="Coaching Agent", description="Lifestyle interventions", status="Active"),
    ]

@router.get("/conversations", response_model=List[ConversationLog])
async def get_conversations():
    return [
        ConversationLog(user_id="user_123", message_count=15, last_active="2025-10-26T10:00:00"),
        ConversationLog(user_id="user_456", message_count=5, last_active="2025-10-26T09:30:00"),
    ]
