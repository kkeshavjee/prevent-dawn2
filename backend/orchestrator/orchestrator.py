from typing import Dict
from backend.models.data_models import AgentState, PatientProfile, RiskLevel, Biomarkers, Message
from backend.agents.intake_agent import IntakeAgent
from backend.agents.motivation_agent import MotivationAgent
from backend.agents.education_agent import EducationAgent
from backend.agents.coaching_agent import CoachingAgent

from backend.services.data_loader import DataLoader
from backend.services.llm_config import configure_dspy
import os

from backend.services.persistence import get_persistence
from backend.mcp_server.mcp_server import MCPServer

class Orchestrator:
    def __init__(self):
        configure_dspy() # Initialize Gemini
        self.mcp_server = MCPServer()
        self.agents = {
            "intake": IntakeAgent(self.mcp_server),
            "motivation": MotivationAgent(self.mcp_server),
            "education": EducationAgent(self.mcp_server),
            "coaching": CoachingAgent(self.mcp_server)
        }
        self.states: Dict[str, AgentState] = {}
        self.persistence = get_persistence()  
        # Note: self.persistence.init_db() needs to be awaited, can't be in __init__
        # We will check table existence on first access or use a startup event in main.py
        
        # Initialize Data Loader
        # Data is now in backend/data/
        data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "PREVENT_Inform_Table_V2 (2).xlsx")
        print(f"Orchestrator: Loading database from {data_path}...")
        self.data_loader = DataLoader(data_path)
        self.user_database = self.data_loader.load_data()
        
        if self.user_database:
            print(f"Orchestrator: Database loaded successfully with {len(self.user_database)} users.")
            # Print first few IDs for verification
            sample_ids = list(self.user_database.keys())[:5]
            print(f"Orchestrator: Sample IDs: {sample_ids}")
        else:
            print("Orchestrator WARNING: Database is empty!")

    async def get_or_create_state(self, user_id: str) -> AgentState:
        # P1: Try to load from persistent DB
        persisted_state = await self.persistence.load_state(user_id)
        if persisted_state:
            self.states[user_id] = persisted_state
            return persisted_state

        # P2: If in-memory (fallback), return it
        if user_id in self.states:
             return self.states[user_id]

        # P3: Create New (and persist it immediately)
        # Check if user exists in loaded database (Excel)
        if user_id in self.user_database:
            profile = self.user_database[user_id]
        else:
            # Fallback for unknown users
            profile = PatientProfile(
                user_id=user_id,
                name="",
                age=0,
                diabetes_risk_score=RiskLevel.MODERATE,
                risk_score_numeric=45,
                biomarkers=Biomarkers(
                    a1c=5.7, fbs=5.5, systolic_bp=120, diastolic_bp=80, 
                    ldl=3.0, hdl=1.2, total_cholesterol=4.5, weight=70, height=170
                )
            )
        
        new_state = AgentState(
            current_agent="intake",
            conversation_history=[],
            patient_profile=profile
        )
        
        self.states[user_id] = new_state
        await self.persistence.save_state(user_id, new_state)
        return new_state

    async def process_request(self, user_id: str, user_input: str) -> Dict:
        state = await self.get_or_create_state(user_id)
        
        # Add user message to history
        state.conversation_history.append(Message(role="user", content=user_input))
        
        # Get current agent
        current_agent_name = state.current_agent
        agent = self.agents[current_agent_name]
        
        # Process with agent
        result = await agent.process(user_input, state)
        
        # Update state based on result
        response_text = result["response"]
        state.conversation_history.append(Message(role="assistant", content=response_text))
        
        if "updated_context" in result:
             state.context_variables.update(result["updated_context"])
             
        if "next_agent" in result and result["next_agent"]:
            print(f"Orchestrator: Transitioning {user_id} from {state.current_agent} to {result['next_agent']}")
            state.current_agent = result["next_agent"]
        else:
            print(f"Orchestrator: Staying at {state.current_agent}")
            
        # Save state to DB (Fire-and-Forget for low latency)
        import asyncio
        asyncio.create_task(self.persistence.save_state(user_id, state))
        # print("Orchestrator: Background save initiated.")
        
        return {
            "response": response_text,
            "current_agent": state.current_agent
        }
