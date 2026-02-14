import pytest
import os
import asyncio
from unittest.mock import MagicMock, patch
from backend.services.persistence import AsyncPersistence

# Define the test database path
TEST_DB_PATH = "test_antigravity.db"

@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """
    Ensure all tests use the test database path and a clean environment.
    Also provide dummy API keys so MCPServer initializes its LM stack.
    """
    monkeypatch.setenv("ANTIGRAVITY_DB", TEST_DB_PATH)
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy_google_key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy_openai_key")
    
    # Reset the singleton orchestrator state to prevent test-to-test leakage
    from backend.main import orchestrator
    orchestrator.states = {}
    
    # CRITICAL FIX for "RuntimeError: Lock is bound to different loop"
    # We must force a fresh lock for every test because the global orchestrator 
    # persists across tests while the event loop changes.
    if hasattr(orchestrator.persistence, "_lock"):
        orchestrator.persistence._lock = None
        
    # CRITICAL FIX: Ensure Singleton uses the TEST DB path, not the one loaded at import time
    if hasattr(orchestrator.persistence, "db_path"):
        orchestrator.persistence.db_path = TEST_DB_PATH

    yield

@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    """
    Initialize a fresh database for the test session.
    """
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
        
    # We use a secondary persistence instance to initialize the DB specifically for tests
    p = AsyncPersistence()
    p.db_path = TEST_DB_PATH # Force path
    
    # Run async init
    loop = asyncio.get_event_loop_policy().get_event_loop()
    loop.run_until_complete(p.init_db())
    
    yield
    
    # Clean up after the session
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

@pytest.fixture(autouse=True)
def global_llm_mock():
    """
    Globally mock dspy.Predict at the MCP server module where it's actually called.
    This prevents real LLM calls during tests.
    """
    with patch("backend.mcp_server.mcp_server.dspy.Predict") as mock_predict:
        # Default mock behavior: return a simple response
        mock_instance = MagicMock()
        mock_instance.return_value = MagicMock(
            response="[MOCK] I understand your request.",
            extracted_name=None,
            next_step=None
        )
        mock_predict.return_value = mock_instance
        yield mock_predict
