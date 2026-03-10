from app.routers.automations import router as automations_router
from app.routers.agents import router as agents_router
from app.routers.activity import router as activity_router
from app.routers.settings import router as settings_router

__all__ = ["automations_router", "agents_router", "activity_router", "settings_router"]
