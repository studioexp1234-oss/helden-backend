from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel

from app.database import get_db, init_db
from app.models import Automation, ActivityLog, Settings
from app.services.n8n_client import trigger_webhook, create_workflow, get_workflow, get_workflow_executions


router = APIRouter(prefix="/api/automations", tags=["automations"])


# Pydantic schemas
class AutomationCreate(BaseModel):
    slug: str
    name: str
    category: str
    channel: str
    status: str = "idea"
    runs: int = 0
    conversions: int = 0
    last_run: str = "—"
    output: Optional[str] = None
    trigger_desc: Optional[str] = None
    description: Optional[str] = None
    n8n_workflow_id: Optional[str] = None
    create_n8n_workflow: bool = True  # Auto-create N8N workflow


class AutomationUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    channel: Optional[str] = None
    status: Optional[str] = None
    runs: Optional[int] = None
    conversions: Optional[int] = None
    last_run: Optional[str] = None
    output: Optional[str] = None
    trigger_desc: Optional[str] = None
    description: Optional[str] = None
    n8n_workflow_id: Optional[str] = None


class TriggerRequest(BaseModel):
    payload: Optional[dict] = None


# Endpoints
@router.get("")
async def get_automations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Automation))
    automations = result.scalars().all()
    return {
        "automations": [
            {
                "id": a.id,
                "slug": a.slug,
                "name": a.name,
                "category": a.category,
                "channel": a.channel,
                "status": a.status,
                "runs": a.runs,
                "conversions": a.conversions,
                "last_run": a.last_run,
                "output": a.output,
                "trigger_desc": a.trigger_desc,
                "description": a.description,
                "n8n_workflow_id": a.n8n_workflow_id,
                "n8n_workflow_url": f"https://helden-n8n.onrender.com/workflow/{a.n8n_workflow_id}" if a.n8n_workflow_id else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "updated_at": a.updated_at.isoformat() if a.updated_at else None
            }
            for a in automations
        ],
        "total": len(automations)
    }


@router.get("/{slug}")
async def get_automation(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Automation).where(Automation.slug == slug))
    automation = result.scalar_one_or_none()
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    n8n_workflow_url = None
    n8n_executions = []
    
    if automation.n8n_workflow_id:
        n8n_workflow_url = f"https://helden-n8n.onrender.com/workflow/{automation.n8n_workflow_id}"
        # Try to get execution history
        exec_result = await get_workflow_executions(automation.n8n_workflow_id, 5)
        if exec_result.get("status") == "success":
            n8n_executions = exec_result.get("executions", [])
    
    return {
        "id": automation.id,
        "slug": automation.slug,
        "name": automation.name,
        "category": automation.category,
        "channel": automation.channel,
        "status": automation.status,
        "runs": automation.runs,
        "conversions": automation.conversions,
        "last_run": automation.last_run,
        "output": automation.output,
        "trigger_desc": automation.trigger_desc,
        "description": automation.description,
        "n8n_workflow_id": automation.n8n_workflow_id,
        "n8n_workflow_url": n8n_workflow_url,
        "n8n_executions": n8n_executions
    }


@router.post("")
async def create_automation(data: AutomationCreate, db: AsyncSession = Depends(get_db)):
    n8n_workflow_id = data.n8n_workflow_id
    
    # Auto-create N8N workflow if requested
    if data.create_n8n_workflow and not n8n_workflow_id:
        n8n_result = await create_workflow(data.name)
        if n8n_result.get("status") == "success":
            n8n_workflow_id = n8n_result.get("workflow_id")
    
    automation = Automation(
        slug=data.slug,
        name=data.name,
        category=data.category,
        channel=data.channel,
        status=data.status,
        output=data.output,
        trigger_desc=data.trigger_desc,
        description=data.description,
        n8n_workflow_id=n8n_workflow_id
    )
    db.add(automation)
    await db.commit()
    await db.refresh(automation)
    
    # Log activity
    log = ActivityLog(
        type="success",
        message=f"Automation created: {automation.name}",
        category=automation.category,
        automation_slug=automation.slug
    )
    db.add(log)
    await db.commit()
    
    return {
        "id": automation.id,
        "slug": automation.slug,
        "n8n_workflow_id": n8n_workflow_id,
        "n8n_workflow_url": f"https://helden-n8n.onrender.com/workflow/{n8n_workflow_id}" if n8n_workflow_id else None
    }


@router.put("/{slug}")
async def update_automation(slug: str, data: AutomationUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Automation).where(Automation.slug == slug))
    automation = result.scalar_one_or_none()
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(automation, key, value)
    
    await db.commit()
    await db.refresh(automation)
    return {"slug": automation.slug, "status": "updated"}


@router.delete("/{slug}")
async def delete_automation(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Automation).where(Automation.slug == slug))
    automation = result.scalar_one_or_none()
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    await db.delete(automation)
    await db.commit()
    return {"status": "deleted", "slug": slug}


@router.post("/{slug}/trigger")
async def trigger_automation(
    slug: str,
    request: TriggerRequest = Body(default=TriggerRequest()),
    db: AsyncSession = Depends(get_db)
):
    # Haal automation op
    result = await db.execute(select(Automation).where(Automation.slug == slug))
    automation = result.scalar_one_or_none()
    
    if not automation:
        # Log error
        log = ActivityLog(
            type="error",
            message=f"Automation not found: {slug}"
        )
        db.add(log)
        await db.commit()
        raise HTTPException(status_code=404, detail=f"Automation not found: {slug}")
    
    if automation.status != "active":
        log = ActivityLog(
            type="error",
            message=f"Automation not active: {automation.name}",
            category=automation.category,
            automation_slug=slug
        )
        db.add(log)
        await db.commit()
        raise HTTPException(status_code=400, detail=f"Automation '{slug}' is not active (status: {automation.status})")
    
    # Haal n8n URL op uit settings
    settings_result = await db.execute(select(Settings).where(Settings.key == "n8n_base_url"))
    settings = settings_result.scalars().all()
    n8n_base_url = next((s.value for s in settings if s.key == "n8n_base_url"), None)
    
    if not n8n_base_url:
        log = ActivityLog(
            type="error",
            message="n8n not configured",
            category=automation.category,
            automation_slug=slug
        )
        db.add(log)
        await db.commit()
        raise HTTPException(status_code=400, detail="n8n not configured")
    
    # Trigger n8n webhook
    payload = request.payload if request.payload else None
    n8n_result = await trigger_webhook(n8n_base_url, slug, payload)
    
    if n8n_result.get("status") == "success":
        # Update runs counter
        automation.runs += 1
        from datetime import datetime
        automation.last_run = datetime.now().strftime("%Y-%m-%d %H:%M")
        await db.commit()
        
        # Log success
        log = ActivityLog(
            type="success",
            message=f"Triggered: {automation.name}",
            category=automation.category,
            automation_slug=slug
        )
        db.add(log)
        await db.commit()
        
        return {
            "status": "triggered",
            "automation": slug,
            "n8n_response": n8n_result.get("data")
        }
    else:
        # Log error
        log = ActivityLog(
            type="error",
            message=f"Trigger failed: {n8n_result.get('message')}",
            category=automation.category,
            automation_slug=slug
        )
        db.add(log)
        await db.commit()
        
        raise HTTPException(status_code=400, detail=n8n_result.get("message"))


@router.get("/{slug}/n8n-executions")
async def get_automation_n8n_executions(slug: str, db: AsyncSession = Depends(get_db)):
    """Get N8N execution history for an automation."""
    result = await db.execute(select(Automation).where(Automation.slug == slug))
    automation = result.scalar_one_or_none()
    
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    if not automation.n8n_workflow_id:
        return {"status": "no_workflow", "executions": []}
    
    exec_result = await get_workflow_executions(automation.n8n_workflow_id, 10)
    return exec_result
