import logging
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent

logger = logging.getLogger(__name__)


async def dispatch_mention_webhooks(
    db: AsyncSession, mentioned_agent_ids: list[UUID], payload: dict
) -> None:
    """Send webhook notifications to mentioned agents."""
    if not mentioned_agent_ids:
        return

    result = await db.execute(
        select(Agent).where(
            Agent.id.in_(mentioned_agent_ids), Agent.webhook_url.isnot(None)
        )
    )
    agents = result.scalars().all()

    async with httpx.AsyncClient(timeout=10.0) as client:
        for agent in agents:
            try:
                await client.post(agent.webhook_url, json=payload)
            except Exception:
                logger.warning(
                    "Webhook delivery failed for agent %s at %s",
                    agent.name,
                    agent.webhook_url,
                )
