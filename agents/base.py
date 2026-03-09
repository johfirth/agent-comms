"""Base agent class that communicates via MCP tools."""

import json
import logging
from mcp_server.client import AgentCommsClient

logger = logging.getLogger(__name__)


class BaseAgent:
    """An agent that communicates through the Agent Communication Server."""

    def __init__(self, name: str, display_name: str, client: AgentCommsClient):
        self.name = name
        self.display_name = display_name
        self.client = client
        self.agent_id: str | None = None
        self.api_key: str | None = None

    async def register(self) -> dict:
        """Register this agent and store its credentials."""
        data = await self.client.post("/agents", json={"name": self.name, "display_name": self.display_name})
        self.agent_id = data["id"]
        self.api_key = data["api_key"]
        self.client.api_key = self.api_key
        logger.info("[%s] Registered (id=%s)", self.name, self.agent_id)
        return data

    def _use_key(self):
        """Ensure requests use this agent's API key."""
        self.client.api_key = self.api_key

    # -- Workspace helpers --

    async def join_workspace(self, workspace_id: str) -> dict:
        self._use_key()
        data = await self.client.post(f"/workspaces/{workspace_id}/join")
        logger.info("[%s] Requested to join workspace %s", self.name, workspace_id)
        return data

    # -- Thread helpers --

    async def create_thread(self, workspace_id: str, title: str, description: str = "", work_item_id: str = "") -> dict:
        self._use_key()
        body = {"title": title}
        if description:
            body["description"] = description
        if work_item_id:
            body["work_item_id"] = work_item_id
        data = await self.client.post(f"/workspaces/{workspace_id}/threads", json=body)
        logger.info("[%s] Created thread '%s'", self.name, title)
        return data

    async def post_message(self, thread_id: str, content: str) -> dict:
        self._use_key()
        data = await self.client.post(f"/threads/{thread_id}/messages", json={"content": content})
        logger.info("[%s] Posted: %s", self.name, content[:80])
        return data

    async def list_messages(self, thread_id: str, limit: int = 50) -> list[dict]:
        self._use_key()
        return await self.client.get(f"/threads/{thread_id}/messages", params={"limit": limit})

    # -- Work item helpers --

    async def create_work_item(self, workspace_id: str, item_type: str, title: str,
                               description: str = "", parent_id: str = "",
                               assigned_agent_id: str = "") -> dict:
        self._use_key()
        body: dict = {"type": item_type, "title": title}
        if description:
            body["description"] = description
        if parent_id:
            body["parent_id"] = parent_id
        if assigned_agent_id:
            body["assigned_agent_id"] = assigned_agent_id
        data = await self.client.post(f"/workspaces/{workspace_id}/work-items", json=body)
        logger.info("[%s] Created %s: '%s'", self.name, item_type, title)
        return data

    async def update_work_item(self, workspace_id: str, item_id: str, **kwargs) -> dict:
        self._use_key()
        body = {k: v for k, v in kwargs.items() if v}
        data = await self.client.patch(f"/workspaces/{workspace_id}/work-items/{item_id}", json=body)
        logger.info("[%s] Updated work item %s: %s", self.name, item_id[:8], body)
        return data

    async def list_work_items(self, workspace_id: str, **filters) -> list[dict]:
        self._use_key()
        params = {k: v for k, v in filters.items() if v}
        return await self.client.get(f"/workspaces/{workspace_id}/work-items", params=params)

    # -- Mention helpers --

    async def check_mentions(self, workspace_id: str = "") -> list[dict]:
        self._use_key()
        params = {"agent_id": self.agent_id}
        if workspace_id:
            params["workspace_id"] = workspace_id
        return await self.client.get("/mentions", params=params)
