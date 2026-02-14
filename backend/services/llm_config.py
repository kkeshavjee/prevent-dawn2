import dspy
import os
from dotenv import load_dotenv
from typing import List, Optional

# Load environment variables from the .env file in the current directory or backend directory
load_dotenv()
load_dotenv("backend/.env") # Fallback if running from root

def get_lm_stack() -> List[dspy.LM]:
    """
    Returns a list of configured DSPy LM objects in order of priority:
    1. OpenAI (NOW PRIMARY - for consistency/speed)
    2. Gemini (Secondary Keys)
    """
    lms = []
    
    # 1. OpenAI (Promoted to Primary for evaluation)
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            lm = dspy.LM(model="openai/gpt-4o-mini", api_key=openai_key)
            lm.provider_name = "OpenAI Primary"
            lms.append(lm)
        except Exception as e:
            print(f"Error checking OpenAI: {e}")

    # 2. Gemini Primary (Now as Fallback)
    google_key_1 = os.getenv("GOOGLE_API_KEY")
    if google_key_1:
        try:
            lm = dspy.LM(model="gemini/gemini-2.0-flash", api_key=google_key_1)
            lm.provider_name = "Gemini Backup 1"
            lms.append(lm)
        except Exception as e:
            print(f"Error checking Gemini Primary: {e}")

    # 3. Gemini Secondary
    google_key_2 = os.getenv("GOOGLE_API_KEY_2")
    if google_key_2:
        try:
            lm = dspy.LM(model="gemini/gemini-2.0-flash", api_key=google_key_2)
            lm.provider_name = "Gemini Backup 2 (2.0)"
            lms.append(lm)
        except Exception as e:
            print(f"Error checking Gemini Secondary: {e}")

    # 4. Gemini Tertiary (New Slot)
    google_key_3 = os.getenv("GOOGLE_API_KEY_3")
    if google_key_3:
        try:
            lm = dspy.LM(model="gemini/gemini-2.0-flash", api_key=google_key_3)
            lm.provider_name = "Gemini Backup 3 (2.0)"
            lms.append(lm)
        except Exception as e:
            print(f"Error checking Gemini Tertiary: {e}")

    # 5. High-Stability Fallback (Gemini 1.5 Flash)
    if google_key_1:
         try:
            lm = dspy.LM(model="gemini/gemini-1.5-flash-latest", api_key=google_key_1)
            lm.provider_name = "Gemini Stability Fallback (1.5)"
            lms.append(lm)
         except Exception as e:
            pass

    # 6. Ultra-High Reliability Fallback (Gemini 1.5 Flash 8B)
    if google_key_1:
         try:
            lm = dspy.LM(model="gemini/gemini-1.5-flash-8b-latest", api_key=google_key_1)
            lm.provider_name = "Gemini Ultra-Resilient (8B)"
            lms.append(lm)
         except Exception as e:
            pass
            
    return lms

def configure_dspy(api_key: str = None, model_name: str = None):
    """
    Configures the global default DSPy LM.
    If specific arguments are provided, uses them.
    Otherwise, uses the highest priority available LM from the stack.
    """
    if api_key:
        # Manual Override
        if api_key.startswith("sk-"):
            final_model = model_name or "openai/gpt-4o-mini"
        else:
            final_model = model_name or "gemini/gemini-2.0-flash"
        
        lm = dspy.LM(model=final_model, api_key=api_key)
        dspy.configure(lm=lm)
        print(f"DSPy manually configured for {final_model}")
        return

    # Auto-detect using priority stack
    stack = get_lm_stack()
    if stack:
        best_lm = stack[0]
        dspy.configure(lm=best_lm)
        print(f"DSPy configured globally with: {getattr(best_lm, 'provider_name', 'Unknown')}")
    else:
        print("Warning: No API Keys found for Gemini or OpenAI.")
