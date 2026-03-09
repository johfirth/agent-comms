"""Base agent class that communicates via MCP tools."""

import json
import logging
from mcp_server.client import AgentCommsClient
from agents.key_store import KeyStore

logger = logging.getLogger(__name__)

_default_key_store = KeyStore()


class BaseAgent:
    """An agent that communicates through the Agent Communication Server."""

    def __init__(self, name: str, display_name: str, client: AgentCommsClient,
                 key_store: KeyStore | None = None):
        self.name = name
        self.display_name = display_name
        self.client = client
        self.key_store = key_store or _default_key_store
        self.agent_id: str | None = None
        self.api_key: str | None = None

        # Try to restore credentials from the key store
        saved = self.key_store.get(self.name)
        if saved:
            self.agent_id = saved["id"]
            self.api_key = saved["api_key"]
            logger.info("[%s] Loaded credentials from key store", self.name)

    async def register(self) -> dict:
        """Register this agent or recover if already registered.

        If the agent name is already taken on the server AND we have a saved key,
        reuse the existing credentials. If the key is missing, regenerate it via
        the admin API.
        """
        if self.agent_id and self.api_key:
            # Verify the saved key still works
            try:
                self.client.api_key = self.api_key
                data = await self.client.get(f"/agents/{self.agent_id}")
                logger.info("[%s] Reusing saved credentials (id=%s)", self.name, self.agent_id[:8])
                return data
            except Exception:
                logger.warning("[%s] Saved key invalid, will regenerate", self.name)
                data = await self.client.post(
                    f"/agents/{self.agent_id}/regenerate-key", admin=True
                )
                self.api_key = data["api_key"]
                self.agent_id = data["id"]
                self.client.api_key = self.api_key
                self.key_store.save_agent(self.name, self.agent_id, self.api_key, self.display_name)
                logger.info("[%s] Regenerated key (id=%s)", self.name, self.agent_id[:8])
                return data

        # Try to register fresh
        try:
            data = await self.client.post("/agents", json={"name": self.name, "display_name": self.display_name})
        except Exception as exc:
            if "409" in str(exc):
                logger.warning("[%s] Already registered but no saved key — cannot recover automatically", self.name)
                raise RuntimeError(
                    f"Agent '{self.name}' exists on server but no local key found. "
                    f"Use admin API to regenerate: POST /agents/<id>/regenerate-key"
                ) from exc
            raise

        self.agent_id = data["id"]
        self.api_key = data["api_key"]
        self.client.api_key = self.api_key
        self.key_store.save_agent(self.name, self.agent_id, self.api_key, self.display_name)
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
