from backend.agents.base_agent import BaseAgent
from backend.models.data_models import AgentState
from backend.models.signatures import IntakeSignature
import dspy
import json
import logging
logger = logging.getLogger(__name__)

class IntakeAgent(BaseAgent):
    def __init__(self):
        self.predictor = dspy.Predict(IntakeSignature)

    async def process(self, user_input: str, state: AgentState) -> dict:
        # Check if we already have the name
        if state.patient_profile.name:
             return {
                "response": f"Welcome back, {state.patient_profile.name}. Let's check in on your motivation.",
                "next_agent": "motivation"
            }
        
        try:
            # Serialize profile for the LLM
            profile_json = state.patient_profile.model_dump_json()
            
            # Call Gemini via DSPy
            result = self.predictor(user_input=user_input, user_profile=profile_json)
            
            updated_context = {}
            if result.extracted_name:
                state.patient_profile.name = result.extracted_name
                updated_context["name"] = result.extracted_name

            next_agent = None
            if result.next_step == 'transition_to_motivation':
                next_agent = "motivation"

            return {
                "response": result.response,
                "next_agent": next_agent,
                "updated_context": updated_context
            }
        except Exception as e:
            # Fallback response if DSPy/LLM fails
            logger.error(f"[IntakeAgent] Error: {e}")
            
            # Simple name extraction from input
            extracted_name = None
            input_lower = user_input.lower()
            
            # Check for "my name is X" or "I'm X" patterns
            for pattern in ["my name is ", "i'm ", "i am ", "call me "]:
                if pattern in input_lower:
                    idx = input_lower.index(pattern) + len(pattern)
                    remaining = user_input[idx:].strip()
                    # Take first word, strip punctuation
                    name_candidate = remaining.split()[0].strip('.,!?') if remaining else None
                    if name_candidate and len(name_candidate) > 1:
                        extracted_name = name_candidate.title()
                        break
            
            if extracted_name:
                state.patient_profile.name = extracted_name
                return {
                    "response": f"Nice to meet you, {extracted_name}! I'm here to help you on your health journey. How are you feeling about making some changes to prevent diabetes?",
                    "next_agent": "motivation",
                    "updated_context": {"name": extracted_name}
                }
            else:
                return {
                    "response": "Welcome to PREVENT Dawn! I'm your health coach, here to support your diabetes prevention journey. Could you tell me your name so I can personalize our conversation?",
                    "next_agent": None,
                    "updated_context": {}
                }
