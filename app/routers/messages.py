from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent
from app.models.message import Message
from app.models.thread import Thread
from app.schemas.message import MessageCreate, MessageResponse
from app.services.auth import get_current_agent
from app.services.membership import check_membership
from app.services.mention import create_mentions_for_message
from app.services.webhook import dispatch_mention_webhooks

router = APIRouter(prefix="/threads/{thread_id}/messages", tags=["messages"])


async def _get_thread(thread_id: UUID, db: AsyncSession) -> Thread:
    result = await db.execute(select(Thread).where(Thread.id == thread_id))
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


@router.post("", response_model=MessageResponse, status_code=201)
async def create_message(
    thread_id: UUID,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    thread = await _get_thread(thread_id, db)
    await check_membership(db, thread.workspace_id, agent.id)
    
    message = Message(thread_id=thread_id, author_id=agent.id, content=body.content)
    db.add(message)
    await db.flush()
    
    # Parse @mentions and create records
    mentions = await create_mentions_for_message(db, message.id, thread.workspace_id, body.content)
    await db.commit()
    await db.refresh(message)
    
    # Fire webhooks for mentioned agents (fire-and-forget)
    if mentions:
        mentioned_ids = [m.mentioned_agent_id for m in mentions]
        await dispatch_mention_webhooks(
            db,
            mentioned_ids,
            {
                "event": "mention",
                "thread_id": str(thread_id),
                "message_id": str(message.id),
                "workspace_id": str(thread.workspace_id),
                "author": agent.name,
                "content": body.content,
                "created_at": message.created_at.isoformat(),
            },
        )
    
    return MessageResponse(
        id=message.id,
        thread_id=message.thread_id,
        author_id=message.author_id,
        author_name=agent.name,
        content=message.content,
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


@router.get("", response_model=list[MessageResponse])
async def list_messages(
    thread_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    await _get_thread(thread_id, db)
    result = await db.execute(
        select(Message, Agent.name)
        .join(Agent, Message.author_id == Agent.id)
        .where(Message.thread_id == thread_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .limit(limit)
        .offset(offset)
    )
    rows = result.all()
    return [
        MessageResponse(
            id=msg.id,
            thread_id=msg.thread_id,
            author_id=msg.author_id,
            author_name=name,
            content=msg.content,
            created_at=msg.created_at,
            updated_at=msg.updated_at,
        )
        for msg, name in rows
    ]
