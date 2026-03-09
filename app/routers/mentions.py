from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.mention import Mention
from app.schemas.mention import MentionResponse

router = APIRouter(prefix="/mentions", tags=["mentions"])


@router.get("", response_model=list[MentionResponse])
async def search_mentions(
    agent_id: UUID = Query(..., description="Agent to search mentions for"),
    workspace_id: UUID | None = Query(None, description="Optionally filter by workspace"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Mention).where(Mention.mentioned_agent_id == agent_id)
    if workspace_id:
        query = query.where(Mention.workspace_id == workspace_id)
    result = await db.execute(query.limit(limit).offset(offset))
    return result.scalars().all()
