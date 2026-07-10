import asyncio
import os
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from supabase import create_client, Client

security = HTTPBearer()

_supabase: Client | None = None


@dataclass
class CurrentUser:
    id: str
    role: str


def _supabase_client() -> Client:
    global _supabase
    if _supabase is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        _supabase = create_client(url, key)
    return _supabase


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    if not jwt_secret:
        raise HTTPException(status_code=500, detail="Auth not configured: missing SUPABASE_JWT_SECRET")

    try:
        payload = jwt.decode(
            credentials.credentials,
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    client = _supabase_client()
    response = await asyncio.to_thread(
        lambda: client.table("profiles").select("role").eq("id", user_id).single().execute()
    )
    if not response.data:
        raise HTTPException(status_code=403, detail="User profile not found")

    return CurrentUser(id=user_id, role=response.data["role"])
