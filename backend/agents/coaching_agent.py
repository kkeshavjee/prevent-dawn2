from backend.agents.base_agent import BaseAgent
from backend.models.data_models import AgentState
from backend.models.signatures import CoachingSignature
import dspy
import logging
logger = logging.getLogger(__name__)

class CoachingAgent(BaseAgent):
    def __init__(self):
        self.predictor = dspy.Predict(CoachingSignature)

    async def process(self, user_input: str, state: AgentState) -> dict:
        try:
            # Serializing specific biomarkers for context
            profile_summary = (
                f"Name: {state.patient_profile.name}, "
                f"Risk: {state.patient_profile.diabetes_risk_score.value}, "
                f"A1c: {state.patient_profile.biomarkers.a1c}"
            )
            
            # Call Gemini via DSPy
            result = self.predictor(user_profile=profile_summary, user_input=user_input)
            
            return {
                "response": getattr(result, 'response', "Let me give you some coaching advice on your wellness journey."),
                "updated_context": {"suggested_action": getattr(result, 'suggested_action', None)}
            }
        except Exception as e:
            # Fallback response if DSPy/LLM fails
            logger.error(f"[CoachingAgent] Error: {e}")
            
            name = state.patient_profile.name or "there"
            coaching_tips = [
                f"Great question, {name}! Here's a simple tip: Try taking a 10-minute walk after your biggest meal today. It helps with blood sugar regulation.",
                f"I hear you, {name}. Let's start small - can you swap one sugary drink for water today? Every little change counts!",
                f"That's a good point, {name}. Have you tried the plate method? Fill half your plate with vegetables, a quarter with protein, and a quarter with whole grains.",
                f"Thanks for sharing, {name}. Sleep is crucial for blood sugar control. Aim for 7-8 hours tonight and see how you feel tomorrow.",
            ]
            import random
            return {
                "response": random.choice(coaching_tips),
                "updated_context": {}
            }
