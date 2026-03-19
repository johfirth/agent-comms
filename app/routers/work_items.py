import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent
from app.models.work_item import HIERARCHY_RULES, WorkItem, WorkItemStatus, WorkItemType
from app.schemas.work_item import WorkItemCreate, WorkItemResponse, WorkItemUpdate
from app.services.auth import get_current_agent
from app.services.membership import check_membership

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces/{workspace_id}/work-items", tags=["work items"])


async def _validate_hierarchy(db: AsyncSession, item_type: str, parent_id: UUID | None, workspace_id: UUID):
    """Enforce Epic -> Feature -> Story -> Task hierarchy."""
    wi_type = WorkItemType(item_type)
    required_parent_type = HIERARCHY_RULES[wi_type]
    
    if required_parent_type is None:
        if parent_id is not None:
            raise HTTPException(status_code=400, detail=f"{wi_type.value} must not have a parent")
        return
    
    if parent_id is None:
        raise HTTPException(status_code=400, detail=f"{wi_type.value} requires a parent of type {required_parent_type.value}")
    
    result = await db.execute(select(WorkItem).where(WorkItem.id == parent_id, WorkItem.workspace_id == workspace_id))
    parent = result.scalar_one_or_none()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent work item not found")
    if parent.type != required_parent_type:
        raise HTTPException(
            status_code=400,
            detail=f"{wi_type.value} parent must be a {required_parent_type.value}, got {parent.type.value}",
        )


async def _validate_assigned_agent(db: AsyncSession, agent_id: UUID | None) -> None:
    """Verify the assigned agent exists."""
    if agent_id is None:
        return
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Assigned agent not found")


@router.post("", response_model=WorkItemResponse, status_code=201)
async def create_work_item(
    workspace_id: UUID,
    body: WorkItemCreate,
    db: AsyncSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    await check_membership(db, workspace_id, agent.id)
    await _validate_hierarchy(db, body.type, body.parent_id, workspace_id)
    await _validate_assigned_agent(db, body.assigned_agent_id)
    
    work_item = WorkItem(
        workspace_id=workspace_id,
        type=WorkItemType(body.type),
        title=body.title,
        description=body.description,
        parent_id=body.parent_id,
        assigned_agent_id=body.assigned_agent_id,
    )
    db.add(work_item)
    await db.commit()
    await db.refresh(work_item)
    return work_item


@router.get("", response_model=list[WorkItemResponse])
async def list_work_items(
    workspace_id: UUID,
    type: str | None = Query(None, pattern="^(epic|feature|story|task)$"),
    status: str | None = Query(None, pattern="^(backlog|in_progress|review|done|cancelled)$"),
    parent_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(WorkItem).where(WorkItem.workspace_id == workspace_id)
    if type:
        query = query.where(WorkItem.type == WorkItemType(type))
    if status:
        query = query.where(WorkItem.status == WorkItemStatus(status))
    if parent_id:
        query = query.where(WorkItem.parent_id == parent_id)
    result = await db.execute(query.order_by(WorkItem.created_at.desc()).limit(limit).offset(offset))
    return result.scalars().all()


@router.get("/{item_id}", response_model=WorkItemResponse)
async def get_work_item(workspace_id: UUID, item_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkItem).where(WorkItem.id == item_id, WorkItem.workspace_id == workspace_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Work item not found")
    return item


@router.patch("/{item_id}", response_model=WorkItemResponse)
async def update_work_item(
    workspace_id: UUID,
    item_id: UUID,
    body: WorkItemUpdate,
    db: AsyncSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    await check_membership(db, workspace_id, agent.id)
    result = await db.execute(
        select(WorkItem).where(WorkItem.id == item_id, WorkItem.workspace_id == workspace_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Work item not found")
    
    update_data = body.model_dump(exclude_unset=True)
    if "assigned_agent_id" in update_data:
        await _validate_assigned_agent(db, update_data["assigned_agent_id"])
    if "status" in update_data:
        update_data["status"] = WorkItemStatus(update_data["status"])
    ALLOWED_FIELDS = {"title", "description", "status", "assigned_agent_id"}
    for field, value in update_data.items():
        if field in ALLOWED_FIELDS:
            setattr(item, field, value)
    
    await db.commit()
    await db.refresh(item)
    return item
