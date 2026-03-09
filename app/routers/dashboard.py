from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.database import get_db
from app.models.agent import Agent
from app.models.membership import Membership
from app.models.mention import Mention
from app.models.message import Message
from app.models.thread import Thread
from app.models.work_item import WorkItem
from app.models.workspace import Workspace

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview")
async def dashboard_overview(db: AsyncSession = Depends(get_db)):
    """Workspace-level stats: totals and per-workspace breakdowns."""

    # Global counts
    total_ws = (await db.execute(select(func.count(Workspace.id)))).scalar()
    total_agents = (await db.execute(select(func.count(Agent.id)))).scalar()
    total_threads = (await db.execute(select(func.count(Thread.id)))).scalar()
    total_messages = (await db.execute(select(func.count(Message.id)))).scalar()
    total_work_items = (await db.execute(select(func.count(WorkItem.id)))).scalar()

    # Per-workspace breakdowns via subqueries
    member_count_sq = (
        select(
            Membership.workspace_id,
            func.count(Membership.id).label("member_count"),
        )
        .group_by(Membership.workspace_id)
        .subquery()
    )

    thread_count_sq = (
        select(
            Thread.workspace_id,
            func.count(Thread.id).label("thread_count"),
        )
        .group_by(Thread.workspace_id)
        .subquery()
    )

    message_count_sq = (
        select(
            Thread.workspace_id,
            func.count(Message.id).label("message_count"),
        )
        .join(Message, Message.thread_id == Thread.id)
        .group_by(Thread.workspace_id)
        .subquery()
    )

    work_item_count_sq = (
        select(
            WorkItem.workspace_id,
            func.count(WorkItem.id).label("work_item_count"),
        )
        .group_by(WorkItem.workspace_id)
        .subquery()
    )

    ws_result = await db.execute(
        select(
            Workspace.id,
            Workspace.name,
            func.coalesce(member_count_sq.c.member_count, 0).label("member_count"),
            func.coalesce(thread_count_sq.c.thread_count, 0).label("thread_count"),
            func.coalesce(message_count_sq.c.message_count, 0).label("message_count"),
            func.coalesce(work_item_count_sq.c.work_item_count, 0).label("work_item_count"),
        )
        .outerjoin(member_count_sq, member_count_sq.c.workspace_id == Workspace.id)
        .outerjoin(thread_count_sq, thread_count_sq.c.workspace_id == Workspace.id)
        .outerjoin(message_count_sq, message_count_sq.c.workspace_id == Workspace.id)
        .outerjoin(work_item_count_sq, work_item_count_sq.c.workspace_id == Workspace.id)
    )

    workspaces = [
        {
            "id": str(ws.id),
            "name": ws.name,
            "member_count": ws.member_count,
            "thread_count": ws.thread_count,
            "message_count": ws.message_count,
            "work_item_count": ws.work_item_count,
        }
        for ws in ws_result.all()
    ]

    return {
        "total_workspaces": total_ws,
        "total_agents": total_agents,
        "total_threads": total_threads,
        "total_messages": total_messages,
        "total_work_items": total_work_items,
        "workspaces": workspaces,
    }


@router.get("/recent-messages")
async def recent_messages(
    limit: int = Query(50, ge=1, le=200),
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Recent messages across all threads, with author and thread info joined."""

    stmt = (
        select(Message, Agent, Thread)
        .join(Agent, Message.author_id == Agent.id)
        .join(Thread, Message.thread_id == Thread.id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )

    if workspace_id is not None:
        stmt = stmt.where(Thread.workspace_id == workspace_id)

    result = await db.execute(stmt)

    return [
        {
            "id": str(msg.id),
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
            "author_name": agent.name,
            "author_display_name": agent.display_name,
            "thread_id": str(msg.thread_id),
            "thread_title": thread.title,
            "workspace_id": str(thread.workspace_id),
        }
        for msg, agent, thread in result.all()
    ]


@router.get("/work-items")
async def dashboard_work_items(
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Work items in a workspace with assigned agent name."""

    stmt = (
        select(WorkItem, Agent)
        .outerjoin(Agent, WorkItem.assigned_agent_id == Agent.id)
        .where(WorkItem.workspace_id == workspace_id)
        .order_by(WorkItem.created_at.desc())
    )

    result = await db.execute(stmt)

    return [
        {
            "id": str(wi.id),
            "type": wi.type.value,
            "title": wi.title,
            "description": wi.description,
            "status": wi.status.value,
            "parent_id": str(wi.parent_id) if wi.parent_id else None,
            "assigned_agent_name": agent.display_name if agent else None,
            "created_at": wi.created_at.isoformat(),
        }
        for wi, agent in result.all()
    ]


@router.get("/threads")
async def dashboard_threads(
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Threads in a workspace with message count and last message time."""

    msg_stats_sq = (
        select(
            Message.thread_id,
            func.count(Message.id).label("message_count"),
            func.max(Message.created_at).label("last_message_at"),
        )
        .group_by(Message.thread_id)
        .subquery()
    )

    stmt = (
        select(
            Thread.id,
            Thread.title,
            Thread.description,
            Thread.created_at,
            Agent.display_name.label("creator_name"),
            func.coalesce(msg_stats_sq.c.message_count, 0).label("message_count"),
            msg_stats_sq.c.last_message_at,
        )
        .join(Agent, Thread.created_by == Agent.id)
        .outerjoin(msg_stats_sq, msg_stats_sq.c.thread_id == Thread.id)
        .where(Thread.workspace_id == workspace_id)
        .order_by(Thread.created_at.desc())
    )

    result = await db.execute(stmt)

    return [
        {
            "id": str(row.id),
            "title": row.title,
            "description": row.description,
            "created_at": row.created_at.isoformat(),
            "creator_name": row.creator_name,
            "message_count": row.message_count,
            "last_message_at": row.last_message_at.isoformat() if row.last_message_at else None,
        }
        for row in result.all()
    ]


@router.get("/mentions")
async def dashboard_mentions(
    workspace_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Mentions with context: who was mentioned, by whom, and the message content."""

    mentioned_agent = aliased(Agent, name="mentioned_agent")
    author_agent = aliased(Agent, name="author_agent")

    stmt = (
        select(
            Mention.id,
            Mention.message_id,
            mentioned_agent.display_name.label("mentioned_agent_name"),
            author_agent.display_name.label("author_name"),
            Message.content,
            Message.created_at,
        )
        .join(Message, Mention.message_id == Message.id)
        .join(mentioned_agent, Mention.mentioned_agent_id == mentioned_agent.id)
        .join(author_agent, Message.author_id == author_agent.id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )

    if workspace_id is not None:
        stmt = stmt.where(Mention.workspace_id == workspace_id)

    result = await db.execute(stmt)

    return [
        {
            "id": str(row.id),
            "message_id": str(row.message_id),
            "mentioned_agent_name": row.mentioned_agent_name,
            "author_name": row.author_name,
            "content": row.content[:200] if row.content else None,
            "created_at": row.created_at.isoformat(),
        }
        for row in result.all()
    ]
