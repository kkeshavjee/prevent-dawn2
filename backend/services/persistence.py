import aiosqlite
import json
import os
from backend.models.data_models import AgentState, PatientProfile, Message, RiskLevel, Biomarkers

import logging
logger = logging.getLogger(__name__)

class AsyncPersistence:
    def __init__(self):
        # Default path logic
        default_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "antigravity.db")
        # Always check environment variable for overrides (isolation)
        self.db_path = os.getenv("ANTIGRAVITY_DB", default_path)

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_states (
                    user_id TEXT PRIMARY KEY,
                    current_agent TEXT,
                    conversation_history TEXT,
                    patient_profile TEXT,
                    context_variables TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS llm_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    agent_name TEXT,
                    signature_name TEXT,
                    prompt_input TEXT,
                    response_output TEXT,
                    model_name TEXT,
                    provider TEXT,
                    latency_ms FLOAT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def save_state(self, user_id: str, state: AgentState):
        async with aiosqlite.connect(self.db_path) as db:
            # Serialize complex objects
            history_json = json.dumps([m.model_dump() for m in state.conversation_history])
            profile_json = state.patient_profile.model_dump__json()
            context_json = json.dumps(state.context_variables)
            
            await db.execute("""
                INSERT OR REPLACE INTO user_states 
                (user_id, current_agent, conversation_history, patient_profile, context_variables)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, state.current_agent, history_json, profile_json, context_json))
            await db.commit()

    async def load_state(self, user_id: str) -> AgentState:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT current_agent, conversation_history, patient_profile, context_variables FROM user_states WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            
            if not row:
                return None
                
            current_agent, history_raw, profile_raw, context_raw = row
            
            # Robustness: Handle NULL current_agent
            if not current_agent:
                logger.warning(f"Persistence WARNING: Found NULL current_agent for user {user_id}. Defaulting to 'intake'.")
                current_agent = "intake"
            
            # Deserialize
            history = [Message(**m) for m in json.loads(history_raw)]
            profile = PatientProfile.model_validate_json(profile_raw)
            context = json.loads(context_raw)
            
            return AgentState(
                current_agent=current_agent,
                conversation_history=history,
                patient_profile=profile,
                context_variables=context
            )

    async def log_interaction(self, user_id: str, agent_name: str, signature_name: str, prompt_input: str, response_output: str, model_name: str, provider: str, latency_ms: float):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO llm_interactions 
                (user_id, agent_name, signature_name, prompt_input, response_output, model_name, provider, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, agent_name, signature_name, prompt_input, response_output, model_name, provider, latency_ms))
            await db.commit()
