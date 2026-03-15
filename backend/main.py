"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio

from . import storage
from .council import (
    run_full_council,
    generate_conversation_title,
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    calculate_aggregate_rankings,
)
from .auth import get_current_user, get_user_id
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL

app = FastAPI(title="LLM Council API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    return credentials.credentials


async def get_user_api_key_for_session(user_id: str, user_token: str) -> Optional[str]:
    """Get the user's OpenRouter API key, falling back to env key."""
    key = await storage.get_user_api_key(user_id, "openrouter", user_token)
    return key


async def get_user_council_models(user_id: str, user_token: str):
    """Get user's council models config, falling back to defaults."""
    config = await storage.get_user_council_config(user_id, user_token)
    if config:
        return config.get("council_models", COUNCIL_MODELS), config.get("chairman_model", CHAIRMAN_MODEL)
    return COUNCIL_MODELS, CHAIRMAN_MODEL


# ── Request / Response models ─────────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    content: str


class SaveApiKeyRequest(BaseModel):
    provider: str
    key: str


class CouncilConfigRequest(BaseModel):
    council_models: List[str]
    chairman_model: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "service": "LLM Council API"}


# ── User profile ──────────────────────────────────────────────────────────────

@app.get("/api/user/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {
        "id": user.get("id"),
        "email": user.get("email"),
        "display_name": user.get("user_metadata", {}).get("display_name"),
    }


# ── API Key management ────────────────────────────────────────────────────────

@app.get("/api/user/keys")
async def list_api_keys(
    user_id: str = Depends(get_user_id),
    token: str = Depends(get_token),
):
    providers = await storage.list_user_api_keys(user_id, token)
    return {"providers": providers}


@app.post("/api/user/keys")
async def save_api_key(
    request: SaveApiKeyRequest,
    user_id: str = Depends(get_user_id),
    token: str = Depends(get_token),
):
    await storage.save_user_api_key(user_id, request.provider, request.key, token)
    return {"success": True, "provider": request.provider}


@app.delete("/api/user/keys/{provider}")
async def delete_api_key(
    provider: str,
    user_id: str = Depends(get_user_id),
    token: str = Depends(get_token),
):
    await storage.delete_user_api_key(user_id, provider, token)
    return {"success": True, "provider": provider}


# ── Council config ────────────────────────────────────────────────────────────

@app.get("/api/user/council-config")
async def get_council_config(
    user_id: str = Depends(get_user_id),
    token: str = Depends(get_token),
):
    config = await storage.get_user_council_config(user_id, token)
    if config:
        return {
            "council_models": config["council_models"],
            "chairman_model": config["chairman_model"],
        }
    return {
        "council_models": COUNCIL_MODELS,
        "chairman_model": CHAIRMAN_MODEL,
    }


@app.post("/api/user/council-config")
async def save_council_config(
    request: CouncilConfigRequest,
    user_id: str = Depends(get_user_id),
    token: str = Depends(get_token),
):
    if len(request.council_models) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 council models")
    await storage.save_user_council_config(
        user_id, request.council_models, request.chairman_model, token
    )
    return {"success": True}


# ── Conversations ─────────────────────────────────────────────────────────────

@app.get("/api/conversations")
async def list_conversations(
    user_id: str = Depends(get_user_id),
    token: str = Depends(get_token),
):
    return await storage.list_conversations(token)


@app.post("/api/conversations")
async def create_conversation(
    user_id: str = Depends(get_user_id),
    token: str = Depends(get_token),
):
    return await storage.create_conversation(user_id, token)


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(get_user_id),
    token: str = Depends(get_token),
):
    conversation = await storage.get_conversation(conversation_id, token)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    user_id: str = Depends(get_user_id),
    token: str = Depends(get_token),
):
    conversation = await storage.get_conversation(conversation_id, token)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    is_first_message = len(conversation["messages"]) == 0
    await storage.add_user_message(conversation_id, user_id, request.content, token)

    api_key = await get_user_api_key_for_session(user_id, token)
    council_models, chairman_model = await get_user_council_models(user_id, token)

    if is_first_message:
        title = await generate_conversation_title(request.content, api_key=api_key)
        await storage.update_conversation_title(conversation_id, title, token)

    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content,
        council_models=council_models,
        chairman_model=chairman_model,
        api_key=api_key,
    )

    await storage.add_assistant_message(
        conversation_id, user_id, stage1_results, stage2_results, stage3_result, token
    )

    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata,
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(
    conversation_id: str,
    request: SendMessageRequest,
    user_id: str = Depends(get_user_id),
    token: str = Depends(get_token),
):
    conversation = await storage.get_conversation(conversation_id, token)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    is_first_message = len(conversation["messages"]) == 0

    api_key = await get_user_api_key_for_session(user_id, token)
    council_models, chairman_model = await get_user_council_models(user_id, token)

    async def event_generator():
        try:
            await storage.add_user_message(conversation_id, user_id, request.content, token)

            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(
                    generate_conversation_title(request.content, api_key=api_key)
                )

            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(
                request.content, council_models=council_models, api_key=api_key
            )
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(
                request.content, stage1_results, council_models=council_models, api_key=api_key
            )
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(
                request.content, stage1_results, stage2_results,
                chairman_model=chairman_model, api_key=api_key
            )
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            if title_task:
                title = await title_task
                await storage.update_conversation_title(conversation_id, title, token)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            await storage.add_assistant_message(
                conversation_id, user_id, stage1_results, stage2_results, stage3_result, token
            )

            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
