import pytest
from fastapi.testclient import TestClient
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.main import app
from tests.conftest import TEST_PATIENT_ID

@pytest.fixture
def client():
    """Unauthenticated client — for public endpoints only (e.g. /health)."""
    with TestClient(app) as c:
        yield c

def test_health_and_pseudonymized_lookup(client, auth_client):
    """
    Requirement 1: Verify health check and pseudonymized lookup.
    PRD 4.6: No PII (email/phone) should leak.
    """
    # Health check — public endpoint, no auth needed
    assert client.get("/health").status_code == 200

    # Pseudonymized lookup — requires admin or health_coach
    response = auth_client.as_admin().get("/api/patient/lookup?name=Anil")
    if response.status_code == 200:
        data = response.json()
        assert "user_id" in data
        assert data["name"] == "Anil"
        # PRD Verification: No PII
        assert "email" not in data
        assert "phone" not in data
    else:
        pytest.skip("Base patient data 'Anil' not found.")

def test_audit_trail_persistence(auth_client):
    """
    Requirement 3: Verify "The Receipt" (PRD 10.1).
    Every LLM call must be logged in the database.
    """
    # user_id comes from the JWT mock (TEST_PATIENT_ID), not the request body
    auth_client.as_patient().post("/api/chat", json={"user_input": "Hello"})

    # Debug endpoint requires admin role
    debug_resp = auth_client.as_admin().get(f"/api/debug/state/{TEST_PATIENT_ID}")
    assert debug_resp.json()["history_count"] >= 2  # User + Assistant response

from backend.main import orchestrator

def test_full_journey_progression(auth_client):
    """
    Requirement 2: Verify State Machine transitions (Identify -> Sustain).
    This test simulates key milestones for a known user.
    """
    import asyncio
    from backend.models.data_models import AgentState, PatientProfile, RiskLevel, Biomarkers
    from backend.services.persistence import AsyncPersistence

    # 1. Setup: Pre-seed the test patient (TEST_PATIENT_ID) with a known name
    #    to skip the "Ask Name" loop. user_id must match the mock JWT's CurrentUser.id.
    name = "JourneyUser"

    profile = PatientProfile(
        user_id=TEST_PATIENT_ID,
        name=name,
        age=30,
        diabetes_risk_score=RiskLevel.MODERATE,
        risk_score_numeric=45,
        biomarkers=Biomarkers(a1c=5.7, fbs=5.5, systolic_bp=120, diastolic_bp=80, ldl=3.0, hdl=1.2, total_cholesterol=4.5, weight=70, height=170)
    )

    seed_state = AgentState(
        current_agent="intake",
        conversation_history=[],
        patient_profile=profile
    )

    async def seed_db():
        p = AsyncPersistence()
        await p.save_state(TEST_PATIENT_ID, seed_state)

    loop = asyncio.get_event_loop_policy().get_event_loop()
    loop.run_until_complete(seed_db())

    # 2. Verify Initial State (admin required for debug endpoint)
    debug_resp = auth_client.as_admin().get(f"/api/debug/state/{TEST_PATIENT_ID}")
    assert debug_resp.json()["current_agent"] == "intake"

    # 3. First Interaction — should trigger "Welcome Back" (no LLM call)
    resp = auth_client.as_patient().post("/api/chat", json={"user_input": "Hello"})
    assert resp.status_code == 200
    assert f"Welcome back, {name}" in resp.json()["response"]

    # 4. Patch LLM to force a state transition to motivation
    class MockResult:
        def __init__(self, response, extracted_name, next_step):
            self.response = response
            self.extracted_name = extracted_name
            self.next_step = next_step

    async def mock_predict_func(*args, **kwargs):
        return MockResult(
            response="Great, moving you to motivation.",
            extracted_name=name,
            next_step="transition_to_motivation"
        )

    with patch.object(orchestrator.mcp_server, 'predict', side_effect=mock_predict_func):
        chat_resp = auth_client.as_patient().post("/api/chat", json={"user_input": "Continue"})
        assert chat_resp.status_code == 200
        assert "moving you to motivation" in chat_resp.json()["response"]

        # 5. Verify transition
        debug_resp = auth_client.as_admin().get(f"/api/debug/state/{TEST_PATIENT_ID}")
        assert debug_resp.json()["current_agent"] == "motivation"


def test_resilience_rate_limiting(auth_client):
    """
    Requirement 5: Verify 429 Resilience.
    """
    # Bypass static welcome first
    auth_client.as_patient().post("/api/chat", json={"user_input": "hello"})

    with patch.object(orchestrator.mcp_server, 'predict', side_effect=Exception("429 Quota Exceeded")):
        response = auth_client.as_patient().post("/api/chat", json={"user_input": "help"})
        assert response.status_code == 429
        assert "Rate Limit" in response.json()["detail"]

def test_malformed_llm_recovery(auth_client):
    """
    Requirement 5: Verify graceful recovery from malformed LLM responses.
    """
    class MalformedResult:
        pass  # Empty result with no expected fields

    # Bypass static welcome first
    auth_client.as_patient().post("/api/chat", json={"user_input": "hello"})

    async def mock_malformed(*args, **kwargs):
        return MalformedResult()

    with patch.object(orchestrator.mcp_server, 'predict', side_effect=mock_malformed):
        response = auth_client.as_patient().post("/api/chat", json={"user_input": "What is my risk?"})

        # Should NOT crash — system must return 200 with a non-empty fallback string
        assert response.status_code == 200
        assert isinstance(response.json()["response"], str)
        assert len(response.json()["response"]) > 0
