import dspy
import os
from dotenv import load_dotenv

import logging
logger = logging.getLogger(__name__))

# Load environment variables from the .env file in the current directory or backend directory
load_dotenv()
load_dotenv("backend/.env") # Fallback if running from root

def configure_dspy():
    """
    Configures DSPy to use Gemini as the Language Model.
    Requires GOOGLE_API_KEY environment variable.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("Warning: GOOGLE_API_KEY not found. LLM calls will fail.")
        return

    try:
        # Configure Gemini using dspy.LM (DSPy 3.0+ compatible)
        # Using gemini-2.5-flash (latest stable model)
        lm = dspy.LM(model='gemini/gemini-2.5-flash', api_key=api_key)
        dspy.configure(lm=lm)
        logger.info("DSPy configured for Gemini (gemini-2.5-flash).")
    except Exception as e:
        logger.error(f"Error configuring Gemini: {e}")
