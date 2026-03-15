"""Supabase database client for the LLM Council backend."""

import os
from typing import Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("VITE_SUPABASE_ANON_KEY", "")

ENCRYPTION_SECRET = os.getenv("API_KEY_ENCRYPTION_SECRET", "llm-council-default-secret-change-me")


def get_service_headers() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def get_user_headers(user_token: str) -> dict:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


async def db_select(
    table: str,
    query_params: str = "",
    user_token: Optional[str] = None,
) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}{query_params}"
    headers = get_user_headers(user_token) if user_token else get_service_headers()

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=15.0)
        response.raise_for_status()
        return response.json()


async def db_insert(
    table: str,
    data: dict,
    user_token: Optional[str] = None,
) -> dict:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = get_user_headers(user_token) if user_token else get_service_headers()

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data, timeout=15.0)
        response.raise_for_status()
        result = response.json()
        return result[0] if isinstance(result, list) and result else result


async def db_upsert(
    table: str,
    data: dict,
    on_conflict: str = "",
    user_token: Optional[str] = None,
) -> dict:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if on_conflict:
        url += f"?on_conflict={on_conflict}"
    headers = get_user_headers(user_token) if user_token else get_service_headers()
    headers["Prefer"] = "return=representation,resolution=merge-duplicates"

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data, timeout=15.0)
        response.raise_for_status()
        result = response.json()
        return result[0] if isinstance(result, list) and result else result


async def db_update(
    table: str,
    query_params: str,
    data: dict,
    user_token: Optional[str] = None,
) -> None:
    url = f"{SUPABASE_URL}/rest/v1/{table}{query_params}"
    headers = get_user_headers(user_token) if user_token else get_service_headers()
    headers["Prefer"] = "return=minimal"

    async with httpx.AsyncClient() as client:
        response = await client.patch(url, headers=headers, json=data, timeout=15.0)
        response.raise_for_status()


async def db_delete(
    table: str,
    query_params: str,
    user_token: Optional[str] = None,
) -> None:
    url = f"{SUPABASE_URL}/rest/v1/{table}{query_params}"
    headers = get_user_headers(user_token) if user_token else get_service_headers()

    async with httpx.AsyncClient() as client:
        response = await client.delete(url, headers=headers, timeout=15.0)
        response.raise_for_status()


async def db_rpc(
    function_name: str,
    params: dict,
    user_token: Optional[str] = None,
) -> any:
    url = f"{SUPABASE_URL}/rest/v1/rpc/{function_name}"
    # Always use service role for RPC calls (encryption functions need elevated privileges)
    headers = get_service_headers()
    if user_token:
        # Override with user token only if service role key is not available
        if not SUPABASE_SERVICE_ROLE_KEY:
            headers = get_user_headers(user_token)

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=params, timeout=15.0)
        response.raise_for_status()
        return response.json()
