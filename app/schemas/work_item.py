from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Literal


class WorkItemCreate(BaseModel):
    type: Literal["epic", "feature", "story", "task"]
    title: str
    description: str | None = None
    parent_id: UUID | None = None
    assigned_agent_id: UUID | None = None


class WorkItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
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
