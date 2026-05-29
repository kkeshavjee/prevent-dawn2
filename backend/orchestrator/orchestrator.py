from typing import Dict
from backend.models.data_models import AgentState, PatientProfile, RiskLevel, Biomarkers, Message
from backend.agents.intake_agent import IntakeAgent
from backend.agents.motivation_agent import MotivationAgent
from backend.agents.education_agent import EducationAgent
from backend.agents.coaching_agent import CoachingAgent

from backend.services.data_loader import DataLoader
from backend.services.llm_config import configure_dspy
import os
import logging
logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        configure_dspy() # Initialize Gemini
        self.agents = {
            "intake": IntakeAgent(),
            "motivation": MotivationAgent(),
            "education": EducationAgent(),
            "coaching": CoachingAgent()
        }
        self.states: Dict[str, AgentState] = {}
        
        # Initialize Data Loader
        # Assuming file is in root workspace
        data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "PREVENT_Inform_Table_V2 (2).xlsx")
        self.data_loader = DataLoader(data_path)
        self.user_database = self.data_loader.load_data()

    async def get_or_create_state(self, user_id: str) -> AgentState:
        if user_id not in self.states:
            # Check if user exists in loaded database
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
            
            self.states[user_id] = AgentState(
                current_agent="intake",
                conversation_history=[],
                patient_profile=profile
            )
        return self.states[user_id]

    async def process_request(self, user_id: str, user_input: str) -> Dict:
        state = await self.get_or_create_state(user_id)
        
        # Add user message to history
        state.conversation_history.append(Message(role="user", content=user_input))
        
        try:
            # Get current agent
            current_agent_name = state.current_agent
            agent = self.agents[current_agent_name]
            
            # Process with agent
            result = await agent.process(user_input, state)
            
            # Update state based on result
            response_text = result["response"]
            state.conversation_history.append(Message(role="assistant", content=response_text))
            
            if "updated_context" in result and result["updated_context"]:
                state.context_variables.update(result["updated_context"])
                 
            if "next_agent" in result and result["next_agent"]:
                state.current_agent = result["next_agent"]
                
            return {
                "response": response_text,
                "current_agent": state.current_agent
            }
        except Exception as e:
            # Fallback at orchestrator level
            logger.error(f"[Orchestrator] Error processing request: {e}")
            
            fallback_response = "I'm here to help with your diabetes prevention journey. What would you like to know about maintaining a healthy lifestyle?"
            state.conversation_history.append(Message(role="assistant", content=fallback_response))
            
            return {
                "response": fallback_response,
                "current_agent": state.current_agent
            }
