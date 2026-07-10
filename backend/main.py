import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.orchestrator.orchestrator import Orchestrator
from backend.models.data_models import OrchestratorRequest, OrchestratorResponse, PatientProfile
from backend.auth.dependencies import get_current_user, CurrentUser
from backend.auth.rbac import require_role, PATIENT, ADMIN, HEALTH_COACH

app = FastAPI()

# Configure CORS to allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = Orchestrator()

@app.on_event("startup")
async def startup_event():
    if not os.getenv("GOOGLE_API_KEY"):
        print("Backend started. WARNING: GOOGLE_API_KEY NOT FOUND!")
    else:
        print("Backend started. Brain connectivity enabled.")
    
    # Initialize Database
    await orchestrator.persistence.init_db()
    print("Backend: Persistence database initialized.")

# --- System Configuration Endpoints ---

class KeyConfigRequest(BaseModel):
    key_type: str  # "primary", "secondary", or "custom"
    custom_key: str = None

from backend.services.llm_config import configure_dspy

@app.post("/api/config/key")
async def switch_api_key(config: KeyConfigRequest, _: CurrentUser = Depends(require_role(ADMIN))):
    """
    Switch the active API Key at runtime.
    """
    new_key = None
    model_name = None
    
    if config.key_type == "primary":
        new_key = os.getenv("GOOGLE_API_KEY")
        if not new_key:
            raise HTTPException(status_code=400, detail="Primary key (GOOGLE_API_KEY) not found.")
            
    elif config.key_type == "secondary":
        new_key = os.getenv("GOOGLE_API_KEY_2")
        if not new_key:
            raise HTTPException(status_code=400, detail="Secondary key (GOOGLE_API_KEY_2) not found.")
            
    elif config.key_type == "openai":
        new_key = os.getenv("OPENAI_API_KEY")
        if not new_key:
            raise HTTPException(status_code=400, detail="OpenAI key (OPENAI_API_KEY) not found.")
        model_name = "openai/gpt-4o-mini"
        
    elif config.key_type == "custom":
        if not config.custom_key:
             raise HTTPException(status_code=400, detail="Custom key must be provided.")
        new_key = config.custom_key
        
    else:
        raise HTTPException(status_code=400, detail="Invalid key_type.")

    # Re-configure DSPy
    configure_dspy(api_key=new_key, model_name=model_name)
    
    return {"status": "success", "message": f"Switched to {config.key_type} key."}

@app.get("/api/config/info")
async def get_config_info(_: CurrentUser = Depends(require_role(ADMIN))):
    """
    Observability Endpoint: Returns currently active LLM stack and configuration.
    Use this to verify which API keys/Providers are enabled and their priority order.
    """
    lms = orchestrator.mcp_server.lms
    stack_info = [f"{getattr(lm, 'provider_name', 'Unknown')} ({getattr(lm, 'model', 'Unknown')})" for lm in lms]
    
    return {
        "status": "active",
        "llm_priority_stack": stack_info,
        "primary_provider": stack_info[0] if stack_info else "None",
        "failover_enabled": len(stack_info) > 1,
        "brain_connectivity": "Online" if stack_info else "Offline"
    }

@app.post("/api/chat/warmup")
async def chat_warmup():
    """
    Triggers a background probe of LLM providers to pre-calculate health status.
    Called by the frontend during idle time (e.g. while showing static greeting).
    """
    import asyncio
    # Fire and forget
    asyncio.create_task(orchestrator.mcp_server.warmup())
    return {"status": "warmup_initiated"}

# --- Chat Endpoints ---

@app.post("/api/chat", response_model=OrchestratorResponse)
async def chat(
    request: OrchestratorRequest,
    current_user: CurrentUser = Depends(require_role(PATIENT, HEALTH_COACH)),
):
    try:
        # user_id comes from the verified JWT, not the request body
        result = await orchestrator.process_request(current_user.id, request.user_input)
        
        # Robustly handle the response content
        raw_response = result.get("response")
        final_response = "I apologize, I'm having trouble formulating a response right now."
        
        if isinstance(raw_response, str):
            final_response = raw_response
        elif raw_response and hasattr(raw_response, 'response') and isinstance(raw_response.response, str):
            # Handle case where dspy returns a Prediction object nested or similar
            final_response = raw_response.response
        else:
            # Fallback: Stringify the object but log a warning
            print(f"Backend WARNING: Non-string response received: {type(raw_response)}. Attempting to stringify.")
            final_response = str(raw_response)

        return OrchestratorResponse(
            response=final_response,
            suggested_actions=[] # TODO: Add actions support
        )
    except Exception as e:
        import traceback
        full_trace = traceback.format_exc()
        error_type = type(e).__name__
        error_msg = str(e) or "No message"
        print(f"\n--- CHAT ERROR ---\nType: {error_type}\nMessage: {error_msg}\n{full_trace}\n-------------------")
        
        # Friendly error handling for Rate Limits
        if "429" in error_msg or "RateLimitError" in error_type or "Quota exceeded" in error_msg:
            detail_msg = "I'm currently experiencing high traffic (Rate Limit Exceeded). Please try again in a minute."
            raise HTTPException(status_code=429, detail=detail_msg)
            
        # Ensure detail is a string to avoid "Error: None" or similar serializations
        detail_msg = f"{error_type}: {error_msg}"
        raise HTTPException(status_code=500, detail=detail_msg)

from backend.services.data_loader import DataLoader

data_path = os.path.join(os.path.dirname(__file__), "data", "PREVENT_Inform_Table_V2 (2).xlsx")
# Fallback hardcoded if needed, but relative is safer now
EXCEL_PATH = data_path 
data_loader = DataLoader(EXCEL_PATH)

@app.get("/api/patient/lookup", response_model=PatientProfile)
async def lookup_patient(name: str, _: CurrentUser = Depends(require_role(ADMIN, HEALTH_COACH))):
    profile = data_loader.get_patient_by_name(name)
    if not profile:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Returning profile directly
    return profile

from backend.api.admin import router as admin_router
app.include_router(admin_router)

@app.get("/api/debug/state/{user_id}")
async def get_state_debug(user_id: str, _: CurrentUser = Depends(require_role(ADMIN))):
    """
    Debug endpoint for integration tests to verify internal state progression.
    NOT for production use.
    """
    state = await orchestrator.get_or_create_state(user_id)
    return {
        "user_id": user_id,
        "current_agent": state.current_agent,
        "current_stage": state.patient_profile.current_stage,
        "history_count": len(state.conversation_history)
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Diabetes Prevention Bot Backend is running!", "docs_url": "/docs"}

