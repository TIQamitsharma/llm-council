"""Supabase-backed storage for conversations and messages."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from . import db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_conversation(user_id: str, user_token: str) -> Dict[str, Any]:
    result = await db.db_insert(
        "conversations",
        {"user_id": user_id, "title": "New Conversation"},
        user_token=user_token,
    )
    return {
        "id": result["id"],
        "created_at": result["created_at"],
        "title": result["title"],
        "messages": [],
    }


async def get_conversation(conversation_id: str, user_token: str) -> Optional[Dict[str, Any]]:
    rows = await db.db_select(
        "conversations",
        f"?id=eq.{conversation_id}&select=*",
        user_token=user_token,
    )
    if not rows:
        return None

    conv = rows[0]

    messages_raw = await db.db_select(
        "messages",
        f"?conversation_id=eq.{conversation_id}&order=message_index.asc&select=*",
        user_token=user_token,
    )

    messages = []
    for m in messages_raw:
        if m["role"] == "user":
            messages.append({"role": "user", "content": m["content"]})
        else:
            messages.append({
                "role": "assistant",
                "stage1": m.get("stage1"),
                "stage2": m.get("stage2"),
                "stage3": m.get("stage3"),
            })

    return {
        "id": conv["id"],
        "created_at": conv["created_at"],
        "title": conv["title"],
        "messages": messages,
    }


async def list_conversations(user_token: str) -> List[Dict[str, Any]]:
    rows = await db.db_select(
        "conversations",
        "?select=id,created_at,title,updated_at&order=updated_at.desc",
        user_token=user_token,
    )

    result = []
    for conv in rows:
        count_rows = await db.db_select(
            "messages",
            f"?conversation_id=eq.{conv['id']}&select=id",
            user_token=user_token,
        )
        result.append({
            "id": conv["id"],
            "created_at": conv["created_at"],
            "title": conv["title"],
            "message_count": len(count_rows),
        })

    return result


async def add_user_message(conversation_id: str, user_id: str, content: str, user_token: str) -> int:
    count_rows = await db.db_select(
        "messages",
        f"?conversation_id=eq.{conversation_id}&select=id",
        user_token=user_token,
    )
    index = len(count_rows)

    await db.db_insert(
        "messages",
        {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": "user",
            "content": content,
            "message_index": index,
        },
        user_token=user_token,
    )

    await db.db_update(
        "conversations",
        f"?id=eq.{conversation_id}",
        {"updated_at": _now_iso()},
        user_token=user_token,
    )

    return index


async def add_assistant_message(
    conversation_id: str,
    user_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any],
    user_token: str,
):
    count_rows = await db.db_select(
        "messages",
        f"?conversation_id=eq.{conversation_id}&select=id",
        user_token=user_token,
    )
    index = len(count_rows)

    await db.db_insert(
        "messages",
        {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": "assistant",
            "stage1": stage1,
            "stage2": stage2,
            "stage3": stage3,
            "message_index": index,
        },
        user_token=user_token,
    )

    await db.db_update(
        "conversations",
        f"?id=eq.{conversation_id}",
        {"updated_at": _now_iso()},
        user_token=user_token,
    )


async def update_conversation_title(conversation_id: str, title: str, user_token: str):
    await db.db_update(
        "conversations",
        f"?id=eq.{conversation_id}",
        {"title": title},
        user_token=user_token,
    )


async def get_user_api_key(user_id: str, provider: str, user_token: str) -> Optional[str]:
    rows = await db.db_select(
        "user_api_keys",
        f"?user_id=eq.{user_id}&provider=eq.{provider}&select=encrypted_key",
        user_token=user_token,
    )
    if not rows:
        return None

    encrypted = rows[0]["encrypted_key"]
    try:
        decrypted = await db.db_rpc(
            "decrypt_api_key",
            {"encrypted_value": encrypted, "secret": db.ENCRYPTION_SECRET},
        )
        return decrypted
    except Exception:
        return None


async def save_user_api_key(user_id: str, provider: str, key_value: str, user_token: str):
    encrypted = await db.db_rpc(
        "encrypt_api_key",
        {"key_value": key_value, "secret": db.ENCRYPTION_SECRET},
    )

    await db.db_upsert(
        "user_api_keys",
        {
            "user_id": user_id,
            "provider": provider,
            "encrypted_key": encrypted,
        },
        on_conflict="user_id,provider",
        user_token=user_token,
    )


async def delete_user_api_key(user_id: str, provider: str, user_token: str):
    await db.db_delete(
        "user_api_keys",
        f"?user_id=eq.{user_id}&provider=eq.{provider}",
        user_token=user_token,
    )


async def list_user_api_keys(user_id: str, user_token: str) -> List[str]:
    rows = await db.db_select(
        "user_api_keys",
        f"?user_id=eq.{user_id}&select=provider",
        user_token=user_token,
    )
    return [r["provider"] for r in rows]


async def get_user_council_config(user_id: str, user_token: str) -> Optional[Dict[str, Any]]:
    rows = await db.db_select(
        "user_council_config",
        f"?user_id=eq.{user_id}&select=*",
        user_token=user_token,
    )
    if not rows:
        return None
    return rows[0]


async def save_user_council_config(
    user_id: str,
    council_models: List[str],
    chairman_model: str,
    user_token: str,
):
    await db.db_upsert(
        "user_council_config",
        {
            "user_id": user_id,
            "council_models": council_models,
            "chairman_model": chairman_model,
        },
        on_conflict="user_id",
        user_token=user_token,
    )
