from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db, get_db
from app.routers import automations_router, agents_router, activity_router, settings_router
from app.models import Settings
from sqlalchemy import select


async def seed_env_settings():
    """Seed database settings from environment variables on startup."""
    env_keys = {
        "n8n_base_url": os.getenv("N8N_BASE_URL", ""),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
    }
    async for db in get_db():
        for key, env_value in env_keys.items():
            if not env_value:
                continue
            result = await db.execute(select(Settings).where(Settings.key == key))
            existing = result.scalar_one_or_none()
            if not existing:
                db.add(Settings(key=key, value=env_value))
        await db.commit()
        break


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_env_settings()
    yield


app = FastAPI(
    title="Helden Automation Backend",
    description="FastAPI backend for Helden Automation Control Center",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(automations_router)
app.include_router(agents_router)
app.include_router(activity_router)
app.include_router(settings_router)


@app.get("/")
async def root():
    return {
        "service": "Helden Automation Backend",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "helden-backend"}


@app.get("/api/config")
async def get_public_config():
    """Public config — safe values the frontend needs on load."""
    return {
        "n8n_url": os.getenv("N8N_BASE_URL", ""),
        "backend_version": "1.0.0",
    }
