from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


# Automation schemas
class AutomationBase(BaseModel):
    slug: str = Field(..., max_length=100)
    name: str = Field(..., max_length=200)
    category: str = Field(..., max_length=50)
    channel: str = Field(..., max_length=50)
    status: str = Field(default="idea", max_length=20)
    runs: int = Field(default=0)
    conversions: int = Field(default=0)
    last_run: str = Field(default="—", max_length=50)
    output: Optional[str] = Field(None, max_length=50)
    trigger_desc: Optional[str] = None
    description: Optional[str] = None
    n8n_workflow_id: Optional[str] = Field(None, max_length=100)


class AutomationCreate(AutomationBase):
    pass


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


class AutomationResponse(AutomationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AutomationListResponse(BaseModel):
    automations: list[AutomationResponse]
    total: int


# Trigger schemas
class TriggerRequest(BaseModel):
    payload: Optional[dict] = None


class TriggerResponse(BaseModel):
    status: str
    automation: Optional[str] = None
    n8n_response: Optional[dict] = None
    message: Optional[str] = None


# Agent Conversation schemas
class Message(BaseModel):
    role: str
    content: str
    timestamp: str


class AgentConversationBase(BaseModel):
    agent_id: str = Field(..., max_length=50)
    messages: list[Message] = []


class AgentConversationCreate(AgentConversationBase):
    pass


class AgentConversationUpdate(BaseModel):
    messages: list[Message]


class AgentConversationResponse(AgentConversationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Chat schemas
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None


class ChatResponse(BaseModel):
    conversation_id: int
    agent_id: str
    response: str
    model: str


# Activity Log schemas
class ActivityLogBase(BaseModel):
    type: str = Field(..., max_length=20)
    message: str
    category: Optional[str] = Field(None, max_length=50)
    automation_slug: Optional[str] = Field(None, max_length=100)


class ActivityLogCreate(ActivityLogBase):
    pass


class ActivityLogResponse(ActivityLogBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ActivityLogListResponse(BaseModel):
    activities: list[ActivityLogResponse]
    total: int


# Settings schemas
class SettingsBase(BaseModel):
    key: str = Field(..., max_length=100)
    value: str


class SettingsCreate(SettingsBase):
    pass


class SettingsUpdate(BaseModel):
    value: str


class SettingsResponse(SettingsBase):
    updated_at: datetime

    class Config:
        from_attributes = True


class BulkSettingsUpdate(BaseModel):
    settings: dict[str, str]
