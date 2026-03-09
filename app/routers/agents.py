from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentCreateResponse, AgentResponse
from app.services.auth import generate_api_key, hash_api_key

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentCreateResponse, status_code=201)
async def register_agent(body: AgentCreate, db: AsyncSession = Depends(get_db)):
    # Check uniqueness
    existing = await db.execute(select(Agent).where(Agent.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Agent name already taken")
    
    raw_key = generate_api_key()
    agent = Agent(
        name=body.name,
        display_name=body.display_name,
        api_key_hash=hash_api_key(raw_key),
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    
    # Return agent data with raw key (shown only once)
    data = {
        "id": agent.id,
        "name": agent.name,
        "display_name": agent.display_name,
        "webhook_url": agent.webhook_url,
        "created_at": agent.created_at,
        "api_key": raw_key,
    }
    return AgentCreateResponse(**data)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
