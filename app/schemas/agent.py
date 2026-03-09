from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class AgentCreate(BaseModel):
    name: str  # max_length=100
    display_name: str


class AgentResponse(BaseModel):
    id: UUID
    name: str
    display_name: str
    webhook_url: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentCreateResponse(AgentResponse):
    api_key: str
