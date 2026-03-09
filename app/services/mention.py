from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.mention import Mention
from app.utils.mention_parser import parse_mentions


async def create_mentions_for_message(
    db: AsyncSession, message_id: UUID, workspace_id: UUID, content: str
) -> list[Mention]:
    """Create mention records for all agents mentioned in message content."""
    agent_names = parse_mentions(content)
    if not agent_names:
        return []

    result = await db.execute(select(Agent).where(Agent.name.in_(agent_names)))
    agents = result.scalars().all()

    mentions = []
    for agent in agents:
        mention = Mention(
            message_id=message_id,
            mentioned_agent_id=agent.id,
            workspace_id=workspace_id,
        )
        db.add(mention)
        mentions.append(mention)

    return mentions
