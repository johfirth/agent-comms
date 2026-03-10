import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse
from app.services.auth import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    body: WorkspaceCreate, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)
):
    existing = await db.execute(select(Workspace).where(Workspace.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Workspace name already taken")

    workspace = Workspace(name=body.name, description=body.description)
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    logger.info("Workspace created: %s (id=%s)", workspace.name, workspace.id)
    return workspace


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Workspace).order_by(Workspace.created_at.desc()).limit(limit).offset(offset)
    )
    return result.scalars().all()


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(workspace_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace
