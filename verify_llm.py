import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.services.llm_config import get_lm_stack
import dspy
import asyncio

async def test_stack():
    stack = get_lm_stack()
    print(f"Testing {len(stack)} providers in stack...")
    
    for lm in stack:
        name = getattr(lm, 'provider_name', 'Unknown')
        print(f"\n--- Testing Provder: {name} ---")
        try:
            with dspy.context(lm=lm):
                predictor = dspy.Predict("input -> output")
                response = predictor(input="Hello, are you online? Answer in 3 words.")
                print(f"Response: {response.output}")
        except Exception as e:
            print(f"Error for {name}: {e}")

if __name__ == "__main__":
    asyncio.run(test_stack())
