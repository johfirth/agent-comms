from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Literal


class WorkItemCreate(BaseModel):
    type: Literal["epic", "feature", "story", "task"]
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(None, max_length=5000)
    parent_id: UUID | None = None
    assigned_agent_id: UUID | None = None


class WorkItemUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = Field(None, max_length=5000)
    status: Literal["backlog", "in_progress", "review", "done", "cancelled"] | None = None
    assigned_agent_id: UUID | None = None


class WorkItemResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    type: str
    title: str
    description: str | None
    status: str
    parent_id: UUID | None
    assigned_agent_id: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
