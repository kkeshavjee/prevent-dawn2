from backend.agents.base_agent import BaseAgent
from backend.models.data_models import AgentState
from backend.models.signatures import EducationSignature
import dspy

class EducationAgent(BaseAgent):
    def __init__(self):
        self.predictor = dspy.Predict(EducationSignature)

    async def process(self, user_input: str, state: AgentState) -> dict:
        try:
            context = f"Risk Score: {state.patient_profile.diabetes_risk_score.value}. " 
            
            # Call Gemini via DSPy
            result = self.predictor(user_context=context, user_input=user_input)
            
            return {
                "response": result.response,
                "updated_context": {"last_quiz": result.quiz_question}
            }
        except Exception as e:
            # Fallback response if DSPy/LLM fails
            print(f"[EducationAgent] Error: {e}")
            
            education_facts = [
                "Did you know? Prediabetes can often be reversed with lifestyle changes. Just 30 minutes of walking 5 days a week can significantly reduce your risk!",
                "Here's a helpful tip: Eating more fiber-rich foods like vegetables, whole grains, and legumes can help stabilize blood sugar levels.",
                "Fun fact: Losing just 5-7% of your body weight can reduce your diabetes risk by up to 58%. Small changes add up!",
                "Good to know: Stress can raise blood sugar levels. Simple relaxation techniques like deep breathing can help.",
            ]
            import random
            return {
                "response": random.choice(education_facts),
                "updated_context": {}
            }
