from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import Settings


router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    settings: dict[str, str]


class SettingCreate(BaseModel):
    key: str
    value: str


# Default settings
DEFAULT_SETTINGS = {
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


@router.get("")
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settings))
    settings = result.scalars().all()
    
    # Merge with defaults
    all_settings = DEFAULT_SETTINGS.copy()
    all_settings.update({s.key: s.value for s in settings})
    
    return all_settings


@router.put("")
async def bulk_update_settings(data: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    for key, value in data.settings.items():
        result = await db.execute(select(Settings).where(Settings.key == key))
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.value = value
        else:
            new_setting = Settings(key=key, value=value)
            db.add(new_setting)
    
    await db.commit()
    return {"message": "Settings updated", "count": len(data.settings)}


@router.post("")
async def create_setting(data: SettingCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settings).where(Settings.key == data.key))
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.value = data.value
    else:
        new_setting = Settings(key=data.key, value=data.value)
        db.add(new_setting)
    
    await db.commit()
    return {"message": "Setting saved", "key": data.key}


@router.put("/{key}")
async def update_setting(key: str, data: SettingCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settings).where(Settings.key == key))
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.value = data.value
    else:
        new_setting = Settings(key=key, value=data.value)
        db.add(new_setting)
    
    await db.commit()
    return {"message": "Setting updated", "key": key}


@router.delete("/{key}")
async def delete_setting(key: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settings).where(Settings.key == key))
    existing = result.scalar_one_or_none()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    await db.delete(existing)
    await db.commit()
    return {"message": "Setting deleted"}
