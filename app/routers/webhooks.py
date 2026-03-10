from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent
from app.schemas.agent import AgentResponse
from app.services.auth import get_current_agent

router = APIRouter(prefix="/agents", tags=["webhooks"])


class WebhookUpdate(BaseModel):
    webhook_url: str = Field(..., min_length=1, max_length=2048, pattern=r"^https?://")


@router.put("/{agent_id}/webhook", response_model=AgentResponse)
async def set_webhook(
    agent_id: UUID,
    body: WebhookUpdate,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    if current_agent.id != agent_id:
        raise HTTPException(status_code=403, detail="Can only update your own webhook URL")
    
    current_agent.webhook_url = body.webhook_url
    await db.commit()
    await db.refresh(current_agent)
    return current_agent
