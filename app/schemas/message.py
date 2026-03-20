from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000)


class MessageResponse(BaseModel):
    id: UUID
    thread_id: UUID
    author_id: UUID | None
    author_name: str | None = None
    content: str
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
