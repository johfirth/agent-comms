from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.membership import Membership, MembershipStatus


async def check_membership(
    db: AsyncSession, workspace_id: UUID, agent_id: UUID
) -> Membership:
    """Verify that an agent is an approved member of a workspace."""
    result = await db.execute(
        select(Membership).where(
            Membership.workspace_id == workspace_id,
            Membership.agent_id == agent_id,
            Membership.status == MembershipStatus.approved,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=403,
            detail="Agent is not an approved member of this workspace",
        )
    return membership
