from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routers import automations_router, agents_router, activity_router, settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database
    await init_db()
    yield
    # Shutdown (if needed)


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
