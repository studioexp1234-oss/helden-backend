import httpx
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.models.models import Automation, AgentConversation, ActivityLog, Settings
from app.schemas.schemas import (
    AutomationCreate, AutomationUpdate, AutomationResponse,
    ActivityLogCreate, SettingsCreate, SettingsUpdate, ChatRequest, TriggerRequest
)
from app.agents.config import AGENT_CONFIG, VALID_AGENTS
from app.agents.prompts import AGENT_PROMPTS
from datetime import datetime
from typing import Optional


# Settings Service
class SettingsService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get(self, key: str) -> Optional[str]:
        result = await self.db.execute(select(Settings).where(Settings.key == key))
        setting = result.scalar_one_or_none()
        return setting.value if setting else None
    
    async def get_all(self) -> dict:
        result = await self.db.execute(select(Settings))
        settings = result.scalars().all()
        return {s.key: s.value for s in settings}
    
    async def set(self, key: str, value: str):
        result = await self.db.execute(select(Settings).where(Settings.key == key))
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = value
        else:
            new_setting = Settings(key=key, value=value)
            self.db.add(new_setting)
        await self.db.commit()
    
    async def bulk_set(self, settings_dict: dict):
        for key, value in settings_dict.items():
            await self.set(key, value)
    
    async def delete(self, key: str):
        await self.db.execute(delete(Settings).where(Settings.key == key))
        await self.db.commit()


# Activity Log Service
class ActivityService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, type: str, message: str, category: Optional[str] = None, 
                   automation_slug: Optional[str] = None) -> ActivityLog:
        log = ActivityLog(
            type=type,
            message=message,
            category=category,
            automation_slug=automation_slug
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log
    
    async def get_recent(self, limit: int = 50, category: Optional[str] = None) -> list[ActivityLog]:
        query = select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(limit)
        if category:
            query = query.where(ActivityLog.category == category)
        result = await self.db.execute(query)
        return list(result.scalars().all())


# Automation Service
class AutomationService:
    def __init__(self, db: AsyncSession, settings_service: SettingsService, activity_service: ActivityService):
        self.db = db
        self.settings = settings_service
        self.activity = activity_service
    
    async def get_all(self) -> tuple[list[Automation], int]:
        result = await self.db.execute(select(Automation))
        automations = list(result.scalars().all())
        return automations, len(automations)
    
    async def get_by_slug(self, slug: str) -> Optional[Automation]:
        result = await self.db.execute(select(Automation).where(Automation.slug == slug))
        return result.scalar_one_or_none()
    
    async def create(self, data: AutomationCreate) -> Automation:
        automation = Automation(**data.model_dump())
        self.db.add(automation)
        await self.db.commit()
        await self.db.refresh(automation)
        await self.activity.create(
            type="success",
            message=f"Automation created: {automation.name}",
            category=automation.category,
            automation_slug=automation.slug
        )
        return automation
    
    async def update(self, slug: str, data: AutomationUpdate) -> Optional[Automation]:
        automation = await self.get_by_slug(slug)
        if not automation:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(automation, key, value)
        
        await self.db.commit()
        await self.db.refresh(automation)
        return automation
    
    async def delete(self, slug: str) -> bool:
        automation = await self.get_by_slug(slug)
        if not automation:
            return False
        
        await self.db.delete(automation)
        await self.db.commit()
        return True
    
    async def trigger(self, slug: str, payload: Optional[dict] = None) -> dict:
        automation = await self.get_by_slug(slug)
        if not automation:
            await self.activity.create(
                type="error",
                message=f"Automation not found: {slug}",
            )
            return {"status": "error", "message": f"Automation not found: {slug}"}
        
        if automation.status != "active":
            await self.activity.create(
                type="error",
                message=f"Automation not active: {automation.name}",
                category=automation.category,
                automation_slug=slug
            )
            return {"status": "error", "message": f"Automation '{slug}' is not active (status: {automation.status})"}
        
        # Get n8n URL from settings
        n8n_url = await self.settings.get("n8n_base_url")
        if not n8n_url:
            await self.activity.create(
                type="error",
                message=f"n8n not configured",
                category=automation.category,
                automation_slug=slug
            )
            return {"status": "error", "message": "n8n not configured. Set n8n_base_url in settings."}
        
        # Trigger n8n webhook
        try:
            async with httpx.AsyncClient() as client:
                webhook_url = f"{n8n_url}/webhook/{slug}"
                response = await client.post(webhook_url, json=payload or {}, timeout=30.0)
                
                n8n_response = response.json() if response.status_code == 200 else None
                
                if response.status_code in [200, 201, 202]:
                    # Update runs count
                    automation.runs += 1
                    automation.last_run = datetime.now().strftime("%Y-%m-%d %H:%M")
                    await self.db.commit()
                    
                    await self.activity.create(
                        type="success",
                        message=f"Triggered: {automation.name}",
                        category=automation.category,
                        automation_slug=slug
                    )
                    return {
                        "status": "triggered",
                        "automation": slug,
                        "n8n_response": n8n_response
                    }
                else:
                    await self.activity.create(
                        type="error",
                        message=f"n8n error ({response.status_code}): {automation.name}",
                        category=automation.category,
                        automation_slug=slug
                    )
                    return {"status": "error", "message": f"n8n returned {response.status_code}"}
        except httpx.ConnectError:
            await self.activity.create(
                type="error",
                message=f"n8n unreachable at {n8n_url}",
                category=automation.category,
                automation_slug=slug
            )
            return {"status": "error", "message": f"n8n unreachable at {n8n_url}"}
        except Exception as e:
            await self.activity.create(
                type="error",
                message=f"Trigger failed: {str(e)}",
                category=automation.category,
                automation_slug=slug
            )
            return {"status": "error", "message": str(e)}


# Agent Chat Service
class AgentService:
    def __init__(self, db: AsyncSession, settings_service: SettingsService, activity_service: ActivityService):
        self.db = db
        self.settings = settings_service
        self.activity = activity_service
    
    async def get_or_create_conversation(self, agent_id: str) -> AgentConversation:
        result = await self.db.execute(
            select(AgentConversation).where(AgentConversation.agent_id == agent_id)
            .order_by(AgentConversation.created_at.desc())
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            conversation = AgentConversation(
                agent_id=agent_id,
                messages=json.dumps([])
            )
            self.db.add(conversation)
            await self.db.commit()
            await self.db.refresh(conversation)
        
        return conversation
    
    async def get_conversation_by_id(self, conversation_id: int) -> Optional[AgentConversation]:
        result = await self.db.execute(
            select(AgentConversation).where(AgentConversation.id == conversation_id)
        )
        return result.scalar_one_or_none()
    
    async def chat(self, agent_id: str, message: str, conversation_id: Optional[int] = None) -> dict:
        # Validate agent
        if agent_id not in VALID_AGENTS:
            return {"error": f"Invalid agent_id. Must be one of: {VALID_AGENTS}"}
        
        # Get conversation
        if conversation_id:
            conversation = await self.get_conversation_by_id(conversation_id)
            if not conversation or conversation.agent_id != agent_id:
                conversation = await self.get_or_create_conversation(agent_id)
        else:
            conversation = await self.get_or_create_conversation(agent_id)
        
        # Get current messages
        messages = json.loads(conversation.messages)
        messages.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Get agent config
        config = AGENT_CONFIG.get(agent_id, {})
        provider = config.get("provider", "anthropic")
        model = config.get("model", "claude-sonnet-4-20250514")
        
        # Get LLM response
        response_text = await self._call_llm(provider, model, agent_id, messages)
        
        # Add assistant response
        messages.append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        })
        
        # Save conversation
        conversation.messages = json.dumps(messages)
        await self.db.commit()
        
        # Log activity
        category_map = {
            "intake": "INBOUND",
            "outreach": "OUTBOUND",
            "aftersales": "AFTERSALES",
            "mining": "OUTBOUND"
        }
        await self.activity.create(
            type="success",
            message=f"Chat with {agent_id}: {message[:50]}...",
            category=category_map.get(agent_id)
        )
        
        return {
            "conversation_id": conversation.id,
            "agent_id": agent_id,
            "response": response_text,
            "model": model
        }
    
    async def _call_llm(self, provider: str, model: str, agent_id: str, messages: list) -> str:
        """Call the appropriate LLM based on provider."""
        
        if provider == "anthropic":
            api_key = await self.settings.get("anthropic_api_key")
            if not api_key:
                return "Anthropic API key not configured. Please set anthropic_api_key in settings."
            
            system_prompt = AGENT_PROMPTS.get(agent_id, "")
            
            # Convert messages to Anthropic format
            anthropic_messages = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]
            
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": api_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json"
                        },
                        json={
                            "model": model,
                            "max_tokens": 1024,
                            "system": system_prompt,
                            "messages": anthropic_messages
                        },
                        timeout=60.0
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["content"][0]["text"]
                    else:
                        return f"Anthropic API error: {resp.status_code}"
            except Exception as e:
                return f"Connection error: {str(e)}"
        
        elif provider == "openai":
            api_key = await self.settings.get("openai_api_key")
            if not api_key:
                return "OpenAI API key not configured. Please set openai_api_key in settings."
            
            system_prompt = AGENT_PROMPTS.get(agent_id, "")
            
            # Convert messages to OpenAI format
            openai_messages = [{"role": "system", "content": system_prompt}]
            openai_messages.extend([{"role": m["role"], "content": m["content"]} for m in messages if m["role"] not in ["system", "system_prompt"]])
            
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "content-type": "application/json"
                        },
                        json={
                            "model": model,
                            "messages": openai_messages,
                            "max_tokens": 1024
                        },
                        timeout=60.0
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        return f"OpenAI API error: {resp.status_code}"
            except Exception as e:
                return f"Connection error: {str(e)}"
        
        elif provider == "ollama":
            ollama_url = await self.settings.get("ollama_base_url") or "http://ollama:11434"
            system_prompt = AGENT_PROMPTS.get(agent_id, "")
            
            # Convert messages to Ollama format
            ollama_messages = [{"role": "system", "content": system_prompt}]
            ollama_messages.extend([{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"])
            
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{ollama_url}/api/chat",
                        json={
                            "model": model,
                            "messages": ollama_messages,
                            "stream": False
                        },
                        timeout=60.0
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["message"]["content"]
                    else:
                        return f"Ollama error: {resp.status_code}"
            except Exception as e:
                return f"Ollama unreachable at {ollama_url}. Make sure Ollama is running."
        
        return f"Unknown provider: {provider}"
    
    async def get_conversation_history(self, agent_id: str) -> list[dict]:
        conversation = await self.get_or_create_conversation(agent_id)
        return json.loads(conversation.messages)
