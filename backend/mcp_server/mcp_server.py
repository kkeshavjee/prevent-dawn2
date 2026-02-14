import dspy
import json
import logging
import time
import asyncio
from typing import Any, Dict, List, Type

from backend.models.data_models import AgentState, PatientProfile
from pydantic import ValidationError

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MCPServer")

from backend.services.persistence import AsyncPersistence
from backend.services.llm_config import get_lm_stack

class MCPServer:
    """
    Model Context Protocol (MCP) Server.
    Acts as a centralized interface for LLM calls with automated context injection and resilience.
    """

    def __init__(self):
        self.persistence = AsyncPersistence()
        self.lms = get_lm_stack()
        self.predictor_cache = {} 
        self.provider_status = {} # Track failures and cooldowns: {provider_name: cooldown_until}
        self._warmup_task = None
        logger.info(f"MCP Server initialized with {len(self.lms)} LMs available for failover.")

    async def warmup(self):
        """
        Background Warmup: Probes providers to pre-fill the Penalty Box.
        This runs without blocking the main conversational flow.
        """
        if not self.lms:
            self.lms = get_lm_stack()
            
        print("MCP: Starting background warmup probe...")
        for lm in self.lms:
            name = getattr(lm, 'provider_name', 'Unknown')
            if name in self.provider_status and time.time() < self.provider_status[name]:
                continue # Already penalized
                
            try:
                # Use a tiny timeout and a trivial task to probe
                with dspy.context(lm=lm):
                    # We don't use a signature here, just a direct call if possible, 
                    # or a very simple Predict to see if the key is alive.
                    predictor = dspy.Predict("input -> output")
                    # Use a very short timeout for the probe
                    await asyncio.wait_for(asyncio.to_thread(predictor, input="ping"), timeout=5.0)
                    print(f"MCP Warmup: {name} is healthy.")
                    # If it was in penalty box, clean it
                    if name in self.provider_status: del self.provider_status[name]
                    # Since we found a working one, we can stop the probe or continue to check all
                    # Let's check all to map the whole stack
            except Exception as e:
                print(f"MCP Warmup: {name} failed probe. Entering 10m penalty box. Error: {str(e)[:50]}")
                self.provider_status[name] = time.time() + 600

    async def predict(self, signature: Type[dspy.Signature], state: AgentState, **kwargs) -> Any:
        """
        Resilient Prediction: Loops through the LM stack until success.
        Skips providers currently in cooldown after a failure.
        """
        history_str = "\n".join([f"{m.role}: {m.content}" for m in state.conversation_history[-8:]])
        profile_json = state.patient_profile.model_dump_json()
        
        inputs = kwargs.copy()
        if "history" in signature.input_fields: inputs["history"] = history_str
        if "user_profile" in signature.input_fields: inputs["user_profile"] = profile_json

        if not self.lms:
            self.lms = get_lm_stack()

        now = time.time()
        # Sort/Filter: We want to skip providers in the "Penalty Box"
        active_lms = []
        for lm in self.lms:
            name = getattr(lm, 'provider_name', 'Unknown')
            cooldown_until = self.provider_status.get(name, 0)
            if now < cooldown_until:
                print(f"MCP: Skipping {name} (In Penalty Box for {int(cooldown_until - now)}s)")
                continue
            active_lms.append(lm)

        if not active_lms:
            print("MCP WARNING: All providers in penalty box. Force-resetting one.")
            active_lms = [self.lms[0]] # Fallback to first one if everything failed

        print(f"MCP: Starting failover loop. Providers to attempt: {[getattr(l, 'provider_name', '??') for l in active_lms]}")

        last_error = None
        for i, lm in enumerate(active_lms):
            provider = getattr(lm, 'provider_name', f'Provider_{i}')
            print(f"MCP Attempt {i+1}: Trying {provider}...")
            
            try:
                with dspy.context(lm=lm):
                    if signature not in self.predictor_cache:
                        self.predictor_cache[signature] = dspy.Predict(signature)
                    
                    predictor = self.predictor_cache[signature]
                    result = predictor(**inputs)
                    
                    # SUCCESS: Ensure this provider is removed from penalty box
                    if provider in self.provider_status:
                        del self.provider_status[provider]
                    
                    print(f"MCP SUCCESS: {provider} responded.")
                    return result
            except Exception as e:
                # FAILURE: Put in penalty box for 10 minutes (600s)
                error_str = str(e)
                print(f"MCP FAILURE: {provider} failed. Entering 10m cooldown. Error: {error_str[:100]}")
                self.provider_status[provider] = time.time() + 600
                last_error = e
                continue 
        
        print("MCP FATAL: All available providers failed.")
        raise last_error or RuntimeError("All LLM providers exhausted.")
