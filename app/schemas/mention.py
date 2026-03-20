from pydantic import BaseModel, ConfigDict
from uuid import UUID


class MentionResponse(BaseModel):
    id: UUID
    message_id: UUID
    mentioned_agent_id: UUID | None
    workspace_id: UUID

    model_config = ConfigDict(from_attributes=True)
