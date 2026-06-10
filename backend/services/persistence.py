import json
import os
import asyncio
import uuid
from backend.models.data_models import AgentState, PatientProfile, Message, RiskLevel, Biomarkers
from backend.services.supabase_client import get_supabase_client

class AsyncPersistence:
    def __init__(self):
        # Kept for backward compatibility and interface symmetry
        self._lock = asyncio.Lock()

    async def init_db(self):
        """
        Verifies connection to the Supabase database.
        Since tables are created externally via Supabase's SQL Editor,
        this acts as a connection health check.
        """
        try:
            client = await get_supabase_client()
            # Attempt a minimal query to verify connectivity
            await client.table("patients").select("count", count="exact").limit(1).execute()
            print("Supabase Persistence: Connected successfully.")
        except Exception as e:
            print(f"Supabase Persistence: Connection check failed: {e}")

    async def _get_or_create_prevent_id(self, user_id: str) -> str:
        """
        Helper method to map a user_id (either a nickname like 'user_123' or an Auth UUID)
        to the corresponding prevent_id (UUID) in the patients/profiles schema.
        Automatically provisions a patient and health status if not found.
        """
        supabase = await get_supabase_client()
        
        def is_valid_uuid(val: str) -> bool:
            try:
                uuid.UUID(str(val))
                return True
            except ValueError:
                return False

        # 1. If user_id is a UUID, check if it's an authenticated user in profiles
        if is_valid_uuid(user_id):
            res_profile = await supabase.table("profiles").select("prevent_id").eq("id", user_id).execute()
            if res_profile.data and res_profile.data[0].get("prevent_id"):
                return res_profile.data[0]["prevent_id"]
                
            # If not in profiles, check if it's already a prevent_id in the patients table
            res_patient = await supabase.table("patients").select("prevent_id").eq("prevent_id", user_id).execute()
            if res_patient.data:
                return res_patient.data[0]["prevent_id"]

        # 2. Otherwise, check by nickname (used for local/test users like "user_123")
        res_patient = await supabase.table("patients").select("prevent_id").eq("nickname", user_id).execute()
        if res_patient.data:
            return res_patient.data[0]["prevent_id"]

        # 3. If the patient does not exist, provision a new patient
        email = user_id if "@" in user_id else f"{user_id}@example.com"
        insert_data = {
            "nickname": user_id,
            "email": email
        }
        
        # If user_id itself is a UUID, preserve it as the prevent_id
        if is_valid_uuid(user_id):
            insert_data["prevent_id"] = user_id

        res_new_patient = await supabase.table("patients").insert(insert_data).execute()
        if not res_new_patient.data:
            raise RuntimeError(f"Failed to create patient for user_id: {user_id}")
            
        prevent_id = res_new_patient.data[0]["prevent_id"]

        # Initialize default health status records
        await supabase.table("patient_health_status").insert({
            "prevent_id": prevent_id,
            "readiness_stage": "Precontemplation",
            "risk_level": "Medium"
        }).execute()

        # If user_id is a UUID (comes from authentication), create the profile link
        if is_valid_uuid(user_id):
            await supabase.table("profiles").insert({
                "id": user_id,
                "role": "patient",
                "prevent_id": str(prevent_id),
                "display_name": user_id
            }).execute()

        return prevent_id

    async def save_state(self, user_id: str, state: AgentState):
        """
        Saves the complete state of the agent session to Supabase.
        Updates metadata across structured tables for dashboard analytics,
        and serializes the full PatientProfile object inside context_variables.
        """
        supabase = await get_supabase_client()
        prevent_id = await self._get_or_create_prevent_id(user_id)
        
        # 1. Save agent session state (current_agent and context_variables)
        context_data = dict(state.context_variables)
        # Serialize the PatientProfile inside context_variables so no Pydantic fields are lost
        context_data["_patient_profile_serialized"] = state.patient_profile.model_dump()
        
        session_data = {
            "prevent_id": prevent_id,
            "current_agent": state.current_agent,
            "context_variables": context_data,
            "updated_at": "now()"
        }
        await supabase.table("agent_sessions").upsert(session_data).execute()
        
        # 2. Sync Patient Health Status
        readiness_stage = state.patient_profile.readiness_stage or state.patient_profile.motivation_level
        risk_level = state.patient_profile.diabetes_risk_score.value if hasattr(state.patient_profile.diabetes_risk_score, "value") else str(state.patient_profile.diabetes_risk_score)
        
        health_status_data = {
            "prevent_id": prevent_id,
            "readiness_stage": readiness_stage,
            "risk_level": risk_level,
            "updated_at": "now()"
        }
        await supabase.table("patient_health_status").upsert(health_status_data, on_conflict="prevent_id").execute()
        
        # 3. Log Biomarkers (Historical Logs)
        biomarkers = state.patient_profile.biomarkers
        if biomarkers:
            biomarker_data = {
                "prevent_id": prevent_id,
                "a1c": biomarkers.a1c,
                "fbs": biomarkers.fbs,
                "bmi": biomarkers.bmi,
                "recorded_at": "now()"
            }
            await supabase.table("biomarker_logs").insert(biomarker_data).execute()
            
        # 4. Save Barriers and Facilitators (Synchronize lists)
        await supabase.table("barriers_facilitators").delete().eq("prevent_id", prevent_id).execute()
        
        barriers_to_insert = []
        for barrier in state.patient_profile.barriers:
            barriers_to_insert.append({
                "prevent_id": prevent_id,
                "content": barrier,
                "type": "barrier",
                "category": "logistical"
            })
        for facilitator in state.patient_profile.facilitators:
            barriers_to_insert.append({
                "prevent_id": prevent_id,
                "content": facilitator,
                "type": "facilitator",
                "category": "social"
            })
            
        if barriers_to_insert:
            await supabase.table("barriers_facilitators").insert(barriers_to_insert).execute()
            
        # 5. Synchronize chat history messages
        await supabase.table("messages").delete().eq("prevent_id", prevent_id).execute()
        
        messages_to_insert = []
        for m in state.conversation_history:
            messages_to_insert.append({
                "prevent_id": prevent_id,
                "role": m.role,
                "content": m.content
            })
            
        if messages_to_insert:
            await supabase.table("messages").insert(messages_to_insert).execute()

    async def load_state(self, user_id: str) -> AgentState:
        """
        Loads the complete agent state session from Supabase.
        Reconstructs the Pydantic models from serialized and structured data.
        """
        supabase = await get_supabase_client()
        prevent_id = await self._get_or_create_prevent_id(user_id)
        
        # Load agent session
        res_session = await supabase.table("agent_sessions").select("current_agent, context_variables").eq("prevent_id", prevent_id).execute()
        if not res_session.data:
            return None
            
        session_data = res_session.data[0]
        current_agent = session_data.get("current_agent") or "intake"
        context_data = session_data.get("context_variables") or {}
        
        # Extract serialized patient profile
        profile_dict = context_data.pop("_patient_profile_serialized", None)
        
        if profile_dict:
            patient_profile = PatientProfile(**profile_dict)
        else:
            # Fallback reconstruction if serialized backup doesn't exist
            res_patient = await supabase.table("patients").select("nickname").eq("prevent_id", prevent_id).execute()
            nickname = res_patient.data[0]["nickname"] if res_patient.data else user_id
            
            res_health = await supabase.table("patient_health_status").select("readiness_stage, risk_level").eq("prevent_id", prevent_id).execute()
            readiness = "Precontemplation"
            risk = RiskLevel.MODERATE
            if res_health.data:
                readiness = res_health.data[0].get("readiness_stage") or "Precontemplation"
                risk_str = res_health.data[0].get("risk_level") or "Moderate"
                try:
                    risk = RiskLevel(risk_str)
                except ValueError:
                    risk = RiskLevel.MODERATE
            
            res_bio = await supabase.table("biomarker_logs").select("a1c, fbs, bmi").eq("prevent_id", prevent_id).order("recorded_at", desc=True).limit(1).execute()
            a1c, fbs, bmi = 0.0, 0.0, 0.0
            if res_bio.data:
                a1c = res_bio.data[0].get("a1c") or 0.0
                fbs = res_bio.data[0].get("fbs") or 0.0
                bmi = res_bio.data[0].get("bmi") or 0.0
            
            res_bf = await supabase.table("barriers_facilitators").select("content, type").eq("prevent_id", prevent_id).execute()
            barriers = [row["content"] for row in res_bf.data if row["type"] == "barrier"]
            facilitators = [row["content"] for row in res_bf.data if row["type"] == "facilitator"]
            
            patient_profile = PatientProfile(
                user_id=user_id,
                name=nickname,
                age=45,
                diabetes_risk_score=risk,
                risk_score_numeric=50,
                biomarkers=Biomarkers(a1c=a1c, fbs=fbs, systolic_bp=120, diastolic_bp=80, ldl=100, hdl=50, total_cholesterol=200, weight=70, height=170),
                motivation_level=readiness,
                readiness_stage=readiness,
                barriers=barriers,
                facilitators=facilitators
            )
            
        # Load conversation history
        res_messages = await supabase.table("messages").select("role, content, created_at").eq("prevent_id", prevent_id).order("created_at").execute()
        history = []
        for m in res_messages.data:
            history.append(Message(
                role=m["role"],
                content=m["content"],
                timestamp=m.get("created_at")
            ))
            
        return AgentState(
            current_agent=current_agent,
            conversation_history=history,
            patient_profile=patient_profile,
            context_variables=context_data
        )

    async def log_interaction(self, user_id: str, agent_name: str, signature_name: str, prompt_input: str, response_output: str, model_name: str, provider: str, latency_ms: float):
        """
        Logs details of an LLM query/response into the llm_interactions auditing table in Supabase.
        """
        supabase = await get_supabase_client()
        prevent_id = await self._get_or_create_prevent_id(user_id)
        
        interaction_data = {
            "prevent_id": prevent_id,
            "agent_name": agent_name,
            "signature_name": signature_name,
            "prompt_input": prompt_input,
            "response_output": response_output,
            "model_name": model_name,
            "provider": provider,
            "latency_ms": latency_ms,
            "timestamp": "now()"
        }
        await supabase.table("llm_interactions").insert(interaction_data).execute()
