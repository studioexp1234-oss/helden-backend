from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel
import json
from datetime import datetime

from app.database import get_db
from app.models import AgentConversation, Settings, ActivityLog
from app.agents.config import AGENT_CONFIG, VALID_AGENTS
from app.agents.llm_client import chat_completion


router = APIRouter(prefix="/api/agents", tags=["agents"])


# Pydantic schemas
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None


class ChatResponse(BaseModel):
    conversation_id: int
    agent_id: str
    response: str
    model: str


@router.post("/{agent_id}/chat")
async def agent_chat(
    agent_id: str,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    # Validate agent
    if agent_id not in VALID_AGENTS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid agent_id. Must be one of: {VALID_AGENTS}"
        )
    
    # Get or create conversation
    conversation = None
    if request.conversation_id:
        result = await db.execute(
            select(AgentConversation).where(
                AgentConversation.id == request.conversation_id,
                AgentConversation.agent_id == agent_id
            )
        )
        conversation = result.scalar_one_or_none()
    
    if not conversation:
        conversation = AgentConversation(
            agent_id=agent_id,
            messages=json.dumps([])
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
    
    # Get current messages
    messages = json.loads(conversation.messages)
    messages.append({
        "role": "user",
        "content": request.message,
        "timestamp": datetime.now().isoformat()
    })
    
    # Get agent config
    config = AGENT_CONFIG.get(agent_id, {})
    provider = config.get("provider", "anthropic")
    model = config.get("model", "claude-sonnet-4-20250514")
    
    # Get API keys from settings
    settings_result = await db.execute(select(Settings))
    settings = {s.key: s.value for s in settings_result.scalars().all()}
    
    api_key = settings.get(f"{provider}_api_key") or settings.get("anthropic_api_key") or settings.get("openai_api_key")
    base_url = settings.get("ollama_base_url")
    
    # Call LLM
    response_text = await chat_completion(
        provider=provider,
        model=model,
        messages=messages,
        api_key=api_key,
        base_url=base_url,
        agent_id=agent_id
    )
    
    # Add assistant response
    messages.append({
        "role": "assistant",
        "content": response_text,
        "timestamp": datetime.now().isoformat()
    })
    
    # Save conversation
    conversation.messages = json.dumps(messages)
    await db.commit()
    
    # Log activity
    category_map = {
        "intake": "INBOUND",
        "outreach": "OUTBOUND",
        "aftersales": "AFTERSALES",
        "mining": "OUTBOUND"
    }
    log = ActivityLog(
        type="success",
        message=f"Chat with {agent_id}: {request.message[:50]}...",
        category=category_map.get(agent_id)
    )
    db.add(log)
    await db.commit()
    
    return {
        "conversation_id": conversation.id,
        "agent_id": agent_id,
        "response": response_text,
        "model": model
    }


@router.get("/{agent_id}/chat")
async def get_chat_history(agent_id: str, db: AsyncSession = Depends(get_db)):
    if agent_id not in VALID_AGENTS:
        raise HTTPException(status_code=400, detail=f"Invalid agent_id")
    
    result = await db.execute(
        select(AgentConversation)
        .where(AgentConversation.agent_id == agent_id)
        .order_by(AgentConversation.created_at.desc())
    )
    conversations = result.scalars().all()
    
    if not conversations:
        return {"agent_id": agent_id, "messages": []}
    
    # Return most recent conversation
    latest = conversations[0]
    return {
        "agent_id": agent_id,
        "conversation_id": latest.id,
        "messages": json.loads(latest.messages)
    }
