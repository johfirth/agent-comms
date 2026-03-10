from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent
from app.models.membership import Membership, MembershipStatus
from app.models.workspace import Workspace
from app.schemas.membership import MembershipResponse, MembershipUpdate
from app.services.auth import get_current_agent, require_admin

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["memberships"])


async def _get_workspace(workspace_id: UUID, db: AsyncSession) -> Workspace:
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


@router.post("/join", response_model=MembershipResponse, status_code=201)
async def request_join(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    await _get_workspace(workspace_id, db)
    
    existing = await db.execute(
        select(Membership).where(
            Membership.workspace_id == workspace_id, Membership.agent_id == agent.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Join request already exists")
    
    membership = Membership(workspace_id=workspace_id, agent_id=agent.id)
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return membership


@router.get("/members", response_model=list[MembershipResponse])
async def list_members(
    workspace_id: UUID,
    status: str | None = Query(None, pattern="^(pending|approved|rejected)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    await _get_workspace(workspace_id, db)
    query = select(Membership).where(Membership.workspace_id == workspace_id)
    if status:
        query = query.where(Membership.status == MembershipStatus(status))
    result = await db.execute(
        query.order_by(Membership.requested_at.desc()).limit(limit).offset(offset)
    )
    return result.scalars().all()


@router.patch("/members/{agent_id}", response_model=MembershipResponse)
async def update_membership(
    workspace_id: UUID,
    agent_id: UUID,
    body: MembershipUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    result = await db.execute(
        select(Membership).where(
            Membership.workspace_id == workspace_id, Membership.agent_id == agent_id
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    
    membership.status = MembershipStatus(body.status)
    membership.approved_by = body.approved_by
    membership.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(membership)
    return membership
