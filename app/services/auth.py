import hashlib
import secrets

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent
from app.config import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key")


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    """Hash an API key using SHA256."""
    return hashlib.sha256(key.encode()).hexdigest()


async def get_current_agent(
    api_key: str = Security(API_KEY_HEADER), db: AsyncSession = Depends(get_db)
) -> Agent:
    """Validate API key and return the associated agent."""
    api_key_hash = hash_api_key(api_key)
    result = await db.execute(
        select(Agent).where(Agent.api_key_hash == api_key_hash)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return agent


async def require_admin(api_key: str = Security(API_KEY_HEADER)) -> None:
    """Validate admin API key."""
    if api_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
