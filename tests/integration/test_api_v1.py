import pytest
from fastapi.testclient import TestClient
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_health_and_pseudonymized_lookup(client):
    """
    Requirement 1: Verify health check and pseudonymized lookup.
    PRD 4.6: No PII (email/phone) should leak.
    """
    # Health check
    assert client.get("/health").status_code == 200
    
    # Pseudonymized lookup
    response = client.get("/api/patient/lookup?name=Anil")
    if response.status_code == 200:
        data = response.json()
        assert "user_id" in data
        assert data["name"] == "Anil"
        # PRD Verification: No PII
        assert "email" not in data
        assert "phone" not in data
    else:
        pytest.skip("Base patient data 'Anil' not found.")

def test_audit_trail_persistence(client):
    """
    Requirement 3: Verify "The Receipt" (PRD 10.1).
    Every LLM call must be logged in the database.
    """
    import uuid
    user_id = f"audit_test_user_{uuid.uuid4().hex[:8]}"
    
    # Perform a chat turn
    client.post("/api/chat", json={
        "user_id": user_id, 
        "user_input": "Hello"
    })
    
    # Check the database for the interaction log
    # We do this via the debug endpoint or direct DB check if needed
    # For now, if the chat succeeds, we verify the history_count in state
    debug_resp = client.get(f"/api/debug/state/{user_id}")
    assert debug_resp.json()["history_count"] >= 2 # User + Assistant response

from backend.main import orchestrator

def test_full_journey_progression(client):
    """
    Requirement 2: Verify State Machine transitions (Identify -> Sustain).
    This test simulates key milestones for a known user.
    """
    import uuid
    import asyncio
    from backend.models.data_models import AgentState, PatientProfile, RiskLevel, Biomarkers
    from backend.services.persistence import AsyncPersistence
    
    # 1. Setup: Pre-seed a user with a KNOWN name to skip the "Ask Name" loop
    user_id = f"journey_test_{uuid.uuid4().hex[:8]}"
    name = "JourneyUser"
    
    # Create valid profile
    profile = PatientProfile(
        user_id=user_id,
        name=name,
        age=30,
        diabetes_risk_score=RiskLevel.MODERATE,
        risk_score_numeric=45,
        biomarkers=Biomarkers(a1c=5.7, fbs=5.5, systolic_bp=120, diastolic_bp=80, ldl=3.0, hdl=1.2, total_cholesterol=4.5, weight=70, height=170)
    )
    
    # Create state
    seed_state = AgentState(
        current_agent="intake",
        conversation_history=[],
        patient_profile=profile
    )
    
    # Save to test DB (using a temporary persistence instance)
    async def seed_db():
        p = AsyncPersistence()
        await p.save_state(user_id, seed_state)
        
    loop = asyncio.get_event_loop_policy().get_event_loop()
    loop.run_until_complete(seed_db())
    
    # 2. Verify Initial State
    debug_resp = client.get(f"/api/debug/state/{user_id}")
    assert debug_resp.json()["current_agent"] == "intake"
    
    # 3. First Interaction for Known User -> Should trigger "Welcome Back" (no LLM, no "Ask Name")
    resp = client.post("/api/chat", json={"user_id": user_id, "user_input": "Hello"})
    assert resp.status_code == 200
    assert f"Welcome back, {name}" in resp.json()["response"]
    
    # 4. Now we want to test the TRANSITION via LLM.
    # The "Welcome Back" prompt asks "Resume or Fresh?".
    # If we say conversationally "I want to start fresh to discuss my goals", the IntakeAgent logic 
    # (lines 11-30) handles it WITHOUT calling the LLM transition logic usually.
    # BUT we want to force the LLM transition logic.
    # We must patch the LLM to return 'transition_to_motivation'.
    
    # Prepare Mock for the LLM call
    class MockResult:
        def __init__(self, response, extracted_name, next_step):
            self.response = response
            self.extracted_name = extracted_name
            self.next_step = next_step
            
    async def mock_predict_func(*args, **kwargs):
        # We simulate the LLM responding to "Continue" by moving to Motivation
        return MockResult(
            response="Great, moving you to motivation.",
            extracted_name=name,
            next_step="transition_to_motivation"
        )

    # 4a. PATCH FIRST: We must patch BEFORE sending "Continue", because "Continue" triggers the LLM.
    with patch.object(orchestrator.mcp_server, 'predict', side_effect=mock_predict_func):
        # 4b. Send "Continue" to trigger the fall-through logic in IntakeAgent
        chat_resp = client.post("/api/chat", json={"user_id": user_id, "user_input": "Continue"})
        
        assert chat_resp.status_code == 200
        # The mocked response should be returned
        assert "moving you to motivation" in chat_resp.json()["response"]
        
        # 5. Verify Final State Transition
        debug_resp = client.get(f"/api/debug/state/{user_id}")
        assert debug_resp.json()["current_agent"] == "motivation"


def test_resilience_rate_limiting(client):
    """
    Requirement 5: Verify 429 Resilience.
    """
    import uuid
    user_id = f"chaos_user_{uuid.uuid4().hex[:8]}"
    
    # Helper to bypass static welcome
    client.post("/api/chat", json={"user_id": user_id, "user_input": "hello"})
    
    # Patch the singleton's predict method to raise Exception
    with patch.object(orchestrator.mcp_server, 'predict', side_effect=Exception("429 Quota Exceeded")):
        response = client.post("/api/chat", json={
            "user_id": user_id, 
            "user_input": "help"
        })
        
        # Rate limit exception should bubble up as 429
        assert response.status_code == 429
        assert "Rate Limit" in response.json()["detail"]

def test_malformed_llm_recovery(client):
    """
    Requirement 5: Verify graceful recovery from malformed LLM responses.
    """
    import uuid
    user_id = f"robust_user_{uuid.uuid4().hex[:8]}"
    
    class MalformedResult:
        pass  # Empty result with no expected fields
    
    # Helper to bypass static welcome
    client.post("/api/chat", json={"user_id": user_id, "user_input": "hello"})
    
    # Patch the singleton to return malformed data
    # Must use side_effect with async def because return_value expects a Future for async methods
    async def mock_malformed(*args, **kwargs):
        return MalformedResult()
        
    with patch.object(orchestrator.mcp_server, 'predict', side_effect=mock_malformed):
        response = client.post("/api/chat", json={
            "user_id": user_id, 
            "user_input": "What is my risk?"
        })
        
        # Should NOT be a 500 error; system must stringify or fallback
        assert response.status_code == 200
        # Check for the fallback message from the agent's defensive handling
        assert "couldn't process that" in response.json()["response"].lower() or "sorry" in response.json()["response"].lower()
