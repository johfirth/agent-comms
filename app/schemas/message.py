from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: UUID
    thread_id: UUID
    author_id: UUID
    content: str
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
