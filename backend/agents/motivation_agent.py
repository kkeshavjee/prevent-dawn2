from backend.agents.base_agent import BaseAgent
from backend.models.data_models import AgentState
from backend.models.signatures import MotivationSignature
import dspy

class MotivationAgent(BaseAgent):
    def __init__(self):
        self.predictor = dspy.Predict(MotivationSignature)

    async def process(self, user_input: str, state: AgentState) -> dict:
        try:
            # Format history
            history_str = "\n".join([f"{m.role}: {m.content}" for m in state.conversation_history[-5:]])
            
            # Call Gemini via DSPy
            result = self.predictor(history=history_str, user_input=user_input)
            
            updated_context = {}
            if result.readiness_score and float(result.readiness_score) > 0:
                updated_context["readiness_score"] = float(result.readiness_score)
                state.patient_profile.motivation_level = f"Readiness: {result.readiness_score}/10"

            return {
                "response": result.response,
                "updated_context": updated_context
            }
        except Exception as e:
            # Fallback response if DSPy/LLM fails
            print(f"[MotivationAgent] Error: {e}")
            
            name = state.patient_profile.name or "there"
            responses = [
                f"Thanks for sharing, {name}. It sounds like you're thinking about making some positive changes. On a scale of 1-10, how important is preventing diabetes to you?",
                f"I appreciate you opening up, {name}. What would be a small first step you could take this week towards better health?",
                f"That's great to hear, {name}. What motivates you most to work on your health - is it family, feeling better, or something else?",
            ]
            import random
            return {
                "response": random.choice(responses),
                "updated_context": {}
            }
