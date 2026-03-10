from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.models import ActivityLog


router = APIRouter(prefix="/api/activity", tags=["activity"])


class ActivityCreate(BaseModel):
    type: str
    message: str
    category: Optional[str] = None
    automation_slug: Optional[str] = None


@router.get("")
async def get_activity(
    limit: int = Query(50, ge=1, le=100),
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(limit)
    if category:
        query = query.where(ActivityLog.category == category)
    
    result = await db.execute(query)
    activities = result.scalars().all()
    
    return {
        "activities": [
            {
                "id": a.id,
                "type": a.type,
                "message": a.message,
                "category": a.category,
                "automation_slug": a.automation_slug,
                "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in activities
        ],
        "total": len(activities)
    }


@router.post("")
async def create_activity(data: ActivityCreate, db: AsyncSession = Depends(get_db)):
    """Voor n8n om activity results terug te posten."""
    log = ActivityLog(
        type=data.type,
        message=data.message,
        category=data.category,
        automation_slug=data.automation_slug
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    
    return {
        "id": log.id,
        "status": "created"
    }
