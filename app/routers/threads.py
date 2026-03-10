from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent
from app.models.thread import Thread
from app.models.work_item import WorkItem
from app.schemas.thread import ThreadCreate, ThreadResponse
from app.services.auth import get_current_agent
from app.services.membership import check_membership

router = APIRouter(prefix="/workspaces/{workspace_id}/threads", tags=["threads"])


@router.post("", response_model=ThreadResponse, status_code=201)
async def create_thread(
    workspace_id: UUID,
    body: ThreadCreate,
    db: AsyncSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    await check_membership(db, workspace_id, agent.id)

    if body.work_item_id is not None:
        result = await db.execute(
            select(WorkItem).where(
                WorkItem.id == body.work_item_id,
                WorkItem.workspace_id == workspace_id,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Work item not found in this workspace")

    thread = Thread(
        workspace_id=workspace_id,
        title=body.title,
        description=body.description,
        work_item_id=body.work_item_id,
        created_by=agent.id,
    )
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return thread


@router.get("", response_model=list[ThreadResponse])
async def list_threads(
    workspace_id: UUID,
    work_item_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Thread).where(Thread.workspace_id == workspace_id)
    if work_item_id:
        query = query.where(Thread.work_item_id == work_item_id)
    result = await db.execute(query.order_by(Thread.created_at.desc()).limit(limit).offset(offset))
    return result.scalars().all()


@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(workspace_id: UUID, thread_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Thread).where(Thread.id == thread_id, Thread.workspace_id == workspace_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread
