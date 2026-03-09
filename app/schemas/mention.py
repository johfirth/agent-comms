from pydantic import BaseModel, ConfigDict
from uuid import UUID


class MentionResponse(BaseModel):
    id: UUID
    message_id: UUID
    mentioned_agent_id: UUID
    workspace_id: UUID

    model_config = ConfigDict(from_attributes=True)
