import os
from dotenv import load_dotenv
from supabase import acreate_client, AsyncClient

# Load environment variables
load_dotenv()

_client: AsyncClient = None

async def get_supabase_client() -> AsyncClient:
    """
    Returns a singleton instance of the asynchronous Supabase client.
    """
    global _client
    if _client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        if supabase_url:
            # Strip /rest/v1 path if present to get the clean base URL
            if "/rest/v1" in supabase_url:
                supabase_url = supabase_url.split("/rest/v1")[0]
            supabase_url = supabase_url.rstrip("/")
            
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and either SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY "
                "must be configured in environment variables."
            )
        
        _client = await acreate_client(supabase_url, supabase_key)
    return _client
