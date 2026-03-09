from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class ThreadCreate(BaseModel):
    title: str
    description: str | None = None
    work_item_id: UUID | None = None


class ThreadResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    description: str | None
    work_item_id: UUID | None
    created_by: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
