from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, init_db
from app.schemas.schemas import (
    AutomationCreate, AutomationUpdate, AutomationResponse, AutomationListResponse,
    ActivityLogListResponse, ActivityLogResponse, ActivityLogCreate,
    SettingsCreate, SettingsUpdate, SettingsResponse,
    ChatRequest, ChatResponse, TriggerRequest, TriggerResponse, BulkSettingsUpdate
)
from app.services.services import (
    AutomationService, ActivityService, SettingsService, AgentService
)
from typing import Optional

router = APIRouter()


# Initialize database on startup
@router.on_event("startup")
async def startup():
    await init_db()


# Health check
@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "helden-backend"}


# ==================== AUTOMATIONS ====================

@router.get("/api/automations", response_model=AutomationListResponse)
async def get_automations(db: AsyncSession = Depends(get_db)):
    settings_service = SettingsService(db)
    activity_service = ActivityService(db)
    automation_service = AutomationService(db, settings_service, activity_service)
    
    automations, total = await automation_service.get_all()
    return AutomationListResponse(
        automations=[AutomationResponse.model_validate(a) for a in automations],
        total=total
    )


@router.get("/api/automations/{slug}", response_model=AutomationResponse)
async def get_automation(slug: str, db: AsyncSession = Depends(get_db)):
    settings_service = SettingsService(db)
    activity_service = ActivityService(db)
    automation_service = AutomationService(db, settings_service, activity_service)
    
    automation = await automation_service.get_by_slug(slug)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    return AutomationResponse.model_validate(automation)


@router.post("/api/automations", response_model=AutomationResponse, status_code=201)
async def create_automation(data: AutomationCreate, db: AsyncSession = Depends(get_db)):
    settings_service = SettingsService(db)
    activity_service = ActivityService(db)
    automation_service = AutomationService(db, settings_service, activity_service)
    
    automation = await automation_service.create(data)
    return AutomationResponse.model_validate(automation)


@router.put("/api/automations/{slug}", response_model=AutomationResponse)
async def update_automation(slug: str, data: AutomationUpdate, db: AsyncSession = Depends(get_db)):
    settings_service = SettingsService(db)
    activity_service = ActivityService(db)
    automation_service = AutomationService(db, settings_service, activity_service)
    
    automation = await automation_service.update(slug, data)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    return AutomationResponse.model_validate(automation)


@router.delete("/api/automations/{slug}", status_code=204)
async def delete_automation(slug: str, db: AsyncSession = Depends(get_db)):
    settings_service = SettingsService(db)
    activity_service = ActivityService(db)
    automation_service = AutomationService(db, settings_service, activity_service)
    
    success = await automation_service.delete(slug)
    if not success:
        raise HTTPException(status_code=404, detail="Automation not found")


# ==================== TRIGGER ====================

@router.post("/api/automations/{slug}/trigger", response_model=TriggerResponse)
async def trigger_automation(
    slug: str, 
    request: Optional[TriggerRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    settings_service = SettingsService(db)
    activity_service = ActivityService(db)
    automation_service = AutomationService(db, settings_service, activity_service)
    
    payload = request.payload if request else None
    result = await automation_service.trigger(slug, payload)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    
    return TriggerResponse(**result)


# ==================== AGENT CHAT ====================

@router.post("/api/agents/{agent_id}/chat", response_model=ChatResponse)
async def agent_chat(
    agent_id: str,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    settings_service = SettingsService(db)
    activity_service = ActivityService(db)
    agent_service = AgentService(db, settings_service, activity_service)
    
    result = await agent_service.chat(agent_id, request.message, request.conversation_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return ChatResponse(**result)


@router.get("/api/agents/{agent_id}/chat")
async def get_chat_history(agent_id: str, db: AsyncSession = Depends(get_db)):
    settings_service = SettingsService(db)
    activity_service = ActivityService(db)
    agent_service = AgentService(db, settings_service, activity_service)
    
    history = await agent_service.get_conversation_history(agent_id)
    return {"agent_id": agent_id, "messages": history}


# ==================== ACTIVITY ====================

@router.get("/api/activity", response_model=ActivityLogListResponse)
async def get_activity(
    limit: int = Query(50, ge=1, le=100),
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    activity_service = ActivityService(db)
    activities = await activity_service.get_recent(limit, category)
    return ActivityLogListResponse(
        activities=[ActivityLogResponse.model_validate(a) for a in activities],
        total=len(activities)
    )


@router.post("/api/activity", response_model=ActivityLogResponse, status_code=201)
async def create_activity(data: ActivityLogCreate, db: AsyncSession = Depends(get_db)):
    """For n8n to post activity results back."""
    activity_service = ActivityService(db)
    log = await activity_service.create(
        type=data.type,
        message=data.message,
        category=data.category,
        automation_slug=data.automation_slug
    )
    return ActivityLogResponse.model_validate(log)


# ==================== SETTINGS ====================

@router.get("/api/settings")
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Get all settings as key-value object."""
    settings_service = SettingsService(db)
    settings = await settings_service.get_all()
    
    # Return defaults if not set
    defaults = {
        "n8n_base_url": "",
        "hubspot_api_key": "",
        "anthropic_api_key": "",
        "openai_api_key": "",
        "ollama_base_url": "http://ollama:11434",
        "agent_intake_url": "",
        "agent_outreach_url": "",
        "agent_aftersales_url": "",
        "agent_mining_url": ""
    }
    for key, value in defaults.items():
        if key not in settings:
            settings[key] = value
    
    return settings


@router.put("/api/settings")
async def bulk_update_settings(data: BulkSettingsUpdate, db: AsyncSession = Depends(get_db)):
    """Bulk update settings."""
    settings_service = SettingsService(db)
    await settings_service.bulk_set(data.settings)
    return {"message": "Settings updated", "count": len(data.settings)}


@router.post("/api/settings")
async def create_setting(data: SettingsCreate, db: AsyncSession = Depends(get_db)):
    settings_service = SettingsService(db)
    await settings_service.set(data.key, data.value)
    return {"message": "Setting saved"}


@router.put("/api/settings/{key}")
async def update_setting(key: str, data: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    settings_service = SettingsService(db)
    await settings_service.set(key, data.value)
    return {"message": "Setting updated"}


@router.delete("/api/settings/{key}")
async def delete_setting(key: str, db: AsyncSession = Depends(get_db)):
    settings_service = SettingsService(db)
    await settings_service.delete(key)
    return {"message": "Setting deleted"}
