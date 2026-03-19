from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime


class ThreadCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(None, max_length=2000)
    work_item_id: UUID | None = None


class ThreadResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    description: str | None
    work_item_id: UUID | None
    created_by: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
