import asyncio
import uuid
from typing import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.base import Base

TEST_DATABASE_URL = settings.database_url

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _override_get_db():
    async with test_session() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db

ADMIN_KEY = settings.admin_api_key


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def admin_headers() -> dict:
    return {"X-API-Key": ADMIN_KEY}


@pytest_asyncio.fixture
async def registered_agent(client: httpx.AsyncClient) -> dict:
    """Register an agent and return {id, name, api_key, headers}."""
    name = f"test-agent-{uuid.uuid4().hex[:8]}"
    resp = await client.post("/agents", json={"name": name, "display_name": f"Test Agent {name}"})
    assert resp.status_code == 201
    data = resp.json()
    return {
        "id": data["id"],
        "name": data["name"],
        "api_key": data["api_key"],
        "headers": {"X-API-Key": data["api_key"]},
    }


@pytest_asyncio.fixture
async def workspace(client: httpx.AsyncClient, admin_headers: dict) -> dict:
    """Create a workspace and return its data."""
    name = f"test-ws-{uuid.uuid4().hex[:8]}"
    resp = await client.post("/workspaces", json={"name": name, "description": "Test workspace"}, headers=admin_headers)
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture
async def approved_agent(client: httpx.AsyncClient, admin_headers: dict, registered_agent: dict, workspace: dict) -> dict:
    """Register agent, join workspace, approve membership. Returns agent dict with workspace_id."""
    # Join
    resp = await client.post(f"/workspaces/{workspace['id']}/join", headers=registered_agent["headers"])
    assert resp.status_code == 201
    # Approve
    resp = await client.patch(
        f"/workspaces/{workspace['id']}/members/{registered_agent['id']}",
        json={"status": "approved", "approved_by": "admin"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    return {**registered_agent, "workspace_id": workspace["id"]}
