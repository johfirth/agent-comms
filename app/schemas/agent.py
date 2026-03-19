from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
import re


def _validate_agent_name(v: str) -> str:
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9._-]{0,98}[a-z0-9])?", v):
        raise ValueError(
            "Agent name must be 1-100 lowercase alphanumeric characters, dots, hyphens, or underscores. "
            "Must start and end with alphanumeric."
        )
    return v


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=255)

    @classmethod
    def model_validate(cls, *args, **kwargs):
        instance = super().model_validate(*args, **kwargs)
        instance.name = _validate_agent_name(instance.name)
        return instance

    def model_post_init(self, __context) -> None:
        _validate_agent_name(self.name)


class AgentResponse(BaseModel):
    id: UUID
    name: str
    display_name: str
    webhook_url: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentCreateResponse(AgentResponse):
    api_key: str
