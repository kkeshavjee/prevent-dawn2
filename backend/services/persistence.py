import aiosqlite
import json
import os
import asyncio
from typing import Optional
from backend.models.data_models import AgentState, PatientProfile, Message, RiskLevel, Biomarkers

# Try to import supabase, but don't fail if not installed yet
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

class PersistenceInterface:
    async def init_db(self):
        pass
    async def save_state(self, user_id: str, state: AgentState):
        pass
    async def load_state(self, user_id: str) -> Optional[AgentState]:
        pass
    async def log_interaction(self, user_id: str, agent_name: str, signature_name: str, prompt_input: str, response_output: str, model_name: str, provider: str, latency_ms: float):
        pass

class SQLitePersistence(PersistenceInterface):
    def __init__(self):
        # Default path logic
        default_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "antigravity.db")
        self.db_path = os.getenv("ANTIGRAVITY_DB", default_path)
        self._lock = None

    @property
    def lock(self):
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def init_db(self):
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("PRAGMA journal_mode=WAL")
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
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                history_json = json.dumps([m.model_dump() for m in state.conversation_history])
                profile_json = state.patient_profile.model_dump_json()
                context_json = json.dumps(state.context_variables)
                
                await db.execute("""
                    INSERT OR REPLACE INTO user_states 
                    (user_id, current_agent, conversation_history, patient_profile, context_variables)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, state.current_agent, history_json, profile_json, context_json))
                await db.commit()

    async def load_state(self, user_id: str) -> AgentState:
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT current_agent, conversation_history, patient_profile, context_variables FROM user_states WHERE user_id = ?", (user_id,))
                row = await cursor.fetchone()
                
                if not row:
                    return None
                    
                current_agent, history_raw, profile_raw, context_raw = row
                if not current_agent: current_agent = "intake"
                
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
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO llm_interactions 
                    (user_id, agent_name, signature_name, prompt_input, response_output, model_name, provider, latency_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, agent_name, signature_name, prompt_input, response_output, model_name, provider, latency_ms))
                await db.commit()

class SupabasePersistence(PersistenceInterface):
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        if SUPABASE_AVAILABLE and self.url and self.key:
            self.client: Client = create_client(self.url, self.key)
        else:
            self.client = None
            if not SUPABASE_AVAILABLE:
                print("WARNING: Supabase library not installed. Falling back to SQLite.")

    async def init_db(self):
        # We assume tables are created in Supabase console
        # Table: user_states (user_id PK, current_agent, conversation_history (jsonb), patient_profile (jsonb), context_variables (jsonb))
        # Table: llm_interactions (id PK, user_id, agent_name, signature_name, prompt_input, response_output, model_name, provider, latency_ms)
        if not self.client:
            print("Supabase client not initialized. Check SUPABASE_URL and SUPABASE_KEY.")

    async def save_state(self, user_id: str, state: AgentState):
        if not self.client: return
        data = {
            "user_id": user_id,
            "current_agent": state.current_agent,
            "conversation_history": [m.model_dump() for m in state.conversation_history],
            "patient_profile": state.patient_profile.model_dump(),
            "context_variables": state.context_variables
        }
        # Upsert in Supabase
        await asyncio.to_thread(self.client.table("user_states").upsert(data).execute)

    async def load_state(self, user_id: str) -> Optional[AgentState]:
        if not self.client: return None
        response = await asyncio.to_thread(self.client.table("user_states").select("*").eq("user_id", user_id).execute)
        if not response.data:
            return None
        
        row = response.data[0]
        history = [Message(**m) for m in row["conversation_history"]]
        profile = PatientProfile(**row["patient_profile"])
        context = row["context_variables"]
        
        return AgentState(
            current_agent=row["current_agent"],
            conversation_history=history,
            patient_profile=profile,
            context_variables=context
        )

    async def log_interaction(self, user_id: str, agent_name: str, signature_name: str, prompt_input: str, response_output: str, model_name: str, provider: str, latency_ms: float):
        if not self.client: return
        data = {
            "user_id": user_id,
            "agent_name": agent_name,
            "signature_name": signature_name,
            "prompt_input": prompt_input,
            "response_output": response_output,
            "model_name": model_name,
            "provider": provider,
            "latency_ms": latency_ms
        }
        await asyncio.to_thread(self.client.table("llm_interactions").insert(data).execute)

def get_persistence() -> PersistenceInterface:
    if os.getenv("SUPABASE_URL") and (os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")):
        return SupabasePersistence()
    return SQLitePersistence()

# Backward compatibility
AsyncPersistence = SQLitePersistence
