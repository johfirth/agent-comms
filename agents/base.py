"""Base agent class — turn-based communication through the Agent Comms Server.

Core pattern for every agent interaction:
  1. READ  — fetch thread history / mentions from the server
  2. THINK — decide what to say (done by the orchestrator / LLM)
  3. POST  — write one message to the server
  4. VERIFY — read back to confirm

The server is the single source of truth. Agents have no local conversation
state — they read everything from the server each turn. This means
conversations are resumable, new agents can join at any time, and the
conversation history is always consistent.
"""

import json
import logging
from mcp_server.client import AgentCommsClient
from agents.key_store import KeyStore

logger = logging.getLogger(__name__)

_default_key_store = KeyStore()


class BaseAgent:
    """An agent that communicates through the Agent Communication Server.

    All conversation state lives on the server. The agent reads from the
    server before every action and writes back one message at a time.
    """

    def __init__(self, name: str, display_name: str, client: AgentCommsClient,
                 key_store: KeyStore | None = None):
        self.name = name
        self.display_name = display_name
        self.client = client
        self.key_store = key_store or _default_key_store
        self.agent_id: str | None = None
        self.api_key: str | None = None

        # Restore credentials from key store if available
        saved = self.key_store.get(self.name)
        if saved:
            self.agent_id = saved["id"]
            self.api_key = saved["api_key"]
            logger.info("[%s] Loaded credentials from key store", self.name)

    def _use_key(self):
        """Set this agent's API key on the shared HTTP client."""
        self.client.api_key = self.api_key

    # ── Registration & Recovery ───────────────────────────────────────────

    async def register(self) -> dict:
        """Register this agent or recover if already registered.

        Uses the key store for persistence. If the agent exists on the server
        and we have a saved key, verifies it. If the key is invalid,
        regenerates via admin API.
        """
        if self.agent_id and self.api_key:
            try:
                self.client.api_key = self.api_key
                data = await self.client.get(f"/agents/{self.agent_id}")
                logger.info("[%s] Verified existing credentials (id=%s)", self.name, self.agent_id[:8])
                return data
            except Exception:
                logger.warning("[%s] Saved key invalid, regenerating...", self.name)
                data = await self.client.post(
                    f"/agents/{self.agent_id}/regenerate-key", admin=True
                )
                self.api_key = data["api_key"]
                self.agent_id = data["id"]
                self.client.api_key = self.api_key
                self.key_store.save_agent(self.name, self.agent_id, self.api_key, self.display_name)
                return data

        try:
            data = await self.client.post("/agents", json={"name": self.name, "display_name": self.display_name})
        except Exception as exc:
            if "409" in str(exc):
                raise RuntimeError(
                    f"Agent '{self.name}' exists on server but no local key. "
                    f"Use admin API: POST /agents/<id>/regenerate-key"
                ) from exc
            raise

        self.agent_id = data["id"]
        self.api_key = data["api_key"]
        self.client.api_key = self.api_key
        self.key_store.save_agent(self.name, self.agent_id, self.api_key, self.display_name)
        logger.info("[%s] Registered (id=%s)", self.name, self.agent_id)
        return data

    # ── Workspace ─────────────────────────────────────────────────────────

    async def join_workspace(self, workspace_id: str) -> dict:
        self._use_key()
        data = await self.client.post(f"/workspaces/{workspace_id}/join")
        logger.info("[%s] Requested to join workspace %s", self.name, workspace_id)
        return data

    # ── READ: Fetch state from server ─────────────────────────────────────

    async def read_thread(self, thread_id: str, limit: int = 100) -> list[dict]:
        """Read the full conversation history from the server.

        Returns messages in chronological order. This is the primary way
        an agent understands what has been said so far.
        """
        self._use_key()
        messages = await self.client.get(
            f"/threads/{thread_id}/messages", params={"limit": limit}
        )
        return messages

    async def get_my_mentions(self, workspace_id: str = "") -> list[dict]:
        """Check the server for any @mentions of this agent."""
        self._use_key()
        params = {"agent_id": self.agent_id}
        if workspace_id:
            params["workspace_id"] = workspace_id
        return await self.client.get("/mentions", params=params)

    async def list_threads(self, workspace_id: str) -> list[dict]:
        """List all threads in a workspace from the server."""
        self._use_key()
        return await self.client.get(f"/workspaces/{workspace_id}/threads")

    async def list_work_items(self, workspace_id: str, **filters) -> list[dict]:
        """List work items from the server."""
        self._use_key()
        params = {k: v for k, v in filters.items() if v}
        return await self.client.get(f"/workspaces/{workspace_id}/work-items", params=params)

    # ── WRITE: Post to server (one message at a time) ─────────────────────

    async def post_message(self, thread_id: str, content: str) -> dict:
        """Post a single message to a thread.

        This is a write operation — the agent has already read the thread
        and decided what to say. @mentions in the content are parsed
        automatically by the server.
        """
        self._use_key()
        data = await self.client.post(
            f"/threads/{thread_id}/messages", json={"content": content}
        )
        logger.info("[%s] Posted message to thread %s", self.name, thread_id[:8])
        return data

    async def create_thread(self, workspace_id: str, title: str,
                            description: str = "", work_item_id: str = "") -> dict:
        self._use_key()
        body = {"title": title}
        if description:
            body["description"] = description
        if work_item_id:
            body["work_item_id"] = work_item_id
        data = await self.client.post(f"/workspaces/{workspace_id}/threads", json=body)
        logger.info("[%s] Created thread '%s'", self.name, title)
        return data

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
        logger.info("[%s] Updated work item %s", self.name, item_id[:8])
        return data

    # ── Utility ───────────────────────────────────────────────────────────

    def format_thread_history(self, messages: list[dict]) -> str:
        """Format thread messages into a readable conversation log.

        Useful for displaying conversation state or feeding to an LLM
        for context-aware response generation.
        """
        lines = []
        for msg in messages:
            author = msg.get("author_name", msg.get("author_id", "unknown"))
            content = msg.get("content", "")
            ts = msg.get("created_at", "")[:19]
            lines.append(f"[{ts}] {author}: {content}")
        return "\n\n".join(lines)
