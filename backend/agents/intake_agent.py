from backend.agents.base_agent import BaseAgent
from backend.models.data_models import AgentState
from backend.models.signatures import IntakeSignature
from backend.mcp_server.mcp_server import MCPServer

class IntakeAgent(BaseAgent):
    def __init__(self, mcp_server: MCPServer):
        super().__init__(mcp_server)

    async def process(self, user_input: str, state: AgentState) -> dict:
        context_updates = {}
        
        # 1. Handle Resume/Fresh Choice
        if state.context_variables.get("pending_resume_choice"):
            print(f"IntakeAgent: Handling resume choice for user input: '{user_input}'")
            # Determine if they want to start fresh
            lower_input = user_input.lower()
            start_fresh = any(word in lower_input for word in ["fresh", "something else", "new", "start over", "mind"])
            
            # Clear the flag locally first
            context_updates["pending_resume_choice"] = False
            
            if start_fresh:
                print("IntakeAgent: User wants a fresh start. Wiping conversation history.")
                # We wipe history but keep the profile
                state.conversation_history = state.conversation_history[-1:] # Keep only the current turn's setup
                return {
                    "response": "Understood. Let's dive in. How are you feeling about your health goals currently?",
                    "next_agent": "motivation",
                    "updated_context": context_updates
                }
            # If not start fresh (Continue), we fall through to normal processing.
            # IMPORTANT: The "pending_resume_choice" = False update will be applied at return.
            
        
        # Debug logging
        print(f"IntakeAgent: Processing request. Current profile name: '{state.patient_profile.name}'")
        
        # 2. Check for Known User (Welcome Back) - ONLY if not just greeted
        greeting_done = state.context_variables.get("intake_greeting_completed", False)
        known_user = state.patient_profile.name and state.patient_profile.name != "User"
        
        if known_user and not greeting_done:
             print(f"IntakeAgent: Name '{state.patient_profile.name}' known. Offering resume choice.")
             # Add flags to context
             context_updates["pending_resume_choice"] = True
             context_updates["intake_greeting_completed"] = True
             
             return {
                "response": f"Welcome back, {state.patient_profile.name}! It's great to see you again. Would you like to continue from where we left off, or is there something else on your mind today?",
                "next_agent": "intake", # Keep them in intake for one more turn to handle the choice
                "updated_context": context_updates
            }
        
        # Call Gemini via MCP Server (handles history and profile injection)
        print(f"IntakeAgent: Calling LLM via MCP with input '{user_input}'...")
        result = await self.mcp_server.predict(IntakeSignature, state, user_input=user_input)
        print(f"IntakeAgent: LLM returned. Result: {result}")
        
        # Defensive access to result attributes
        response_text = getattr(result, 'response', None)
        extracted_name = getattr(result, 'extracted_name', None)
        next_step = getattr(result, 'next_step', None)

        if not response_text:
            print("IntakeAgent WARNING: LLM returned empty response!")
            response_text = "I'm sorry, I couldn't process that. Could you say that again?"
        
        if extracted_name:
            state.patient_profile.name = extracted_name
            context_updates["name"] = extracted_name
            # If we extracted name, we consider greeting done to avoid immediate "Welcome Back" loop next turn
            context_updates["intake_greeting_completed"] = True

        final_next_agent = None
        if next_step == 'transition_to_motivation':
            final_next_agent = "motivation"

        return {
            "response": response_text,
            "next_agent": final_next_agent,
            "updated_context": context_updates
        }
