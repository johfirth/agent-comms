from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse
from app.services.auth import require_admin

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    body: WorkspaceCreate, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)
):
    workspace = Workspace(name=body.name, description=body.description)
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Workspace).order_by(Workspace.created_at.desc()))
    return result.scalars().all()


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(workspace_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace
