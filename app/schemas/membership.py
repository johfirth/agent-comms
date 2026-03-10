from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Literal


class MembershipResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    agent_id: UUID
    status: str
    approved_by: str | None
    requested_at: datetime
    resolved_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class MembershipUpdate(BaseModel):
    status: Literal["approved", "rejected"]
    approved_by: str = Field(..., min_length=1, max_length=255)
