"""High-level workflow tools for Copilot CLI agent communication.

These tools combine multiple API calls into single-step workflows that
make it easy for any Copilot CLI user to participate in agent conversations.
The key store persists agent credentials locally so agents survive across sessions.
"""

import logging
from contextvars import ContextVar
from typing import Annotated

from fastmcp import FastMCP

from agents.key_store import KeyStore
from mcp_server.client import AgentCommsClient, AgentCommsError

logger = logging.getLogger(__name__)

# Shared key store instance (reads agents/keys.json)
_key_store = KeyStore()

# Active agent API key for the current session.
# Set by setup_my_agent / use_agent.  Passed per-request to avoid
# relying solely on mutable client.api_key (see issue #7).
_active_api_key: ContextVar[str | None] = ContextVar('_active_api_key', default=None)


def register_workflow_tools(mcp: FastMCP, client: AgentCommsClient):
    """Register high-level workflow tools for easy Copilot CLI usage."""

    def _set_active_key(api_key: str):
        """Set the active agent key for this async context."""
        _active_api_key.set(api_key)
        # Also set on client for backward compat with non-workflow tools
        # (e.g. post_message in threads.py).  TODO(#7): remove once all
        # tool modules accept per-request api_key.
        client.api_key = api_key

    def _no_active_agent_error() -> dict:
        return {"status": "error", "message": "No active agent. Run setup_my_agent first."}

    def _get_active_agent() -> tuple[str, dict] | None:
        active_api_key = _active_api_key.get()
        if not active_api_key:
            return None

        for agent_name, info in _key_store.list_agents().items():
            if info["api_key"] == active_api_key:
                return agent_name, info

        return None

    @mcp.tool()
    async def setup_my_agent(
        name: Annotated[str, "Agent name for @mentions (e.g. 'john', 'alice-dev'). Lowercase, no spaces."],
        display_name: Annotated[str, "Human-readable name (e.g. 'John Firth', 'Alice - Developer')"],
    ) -> dict:
        """Register yourself as an agent (or recover existing credentials).

        Call this ONCE when you first connect. Your credentials are saved locally
        and reused automatically on future sessions. If you've already registered,
        this returns your existing agent info.

        After setup, your API key is stored in agents/keys.json and the MCP
        server will use it for all subsequent tool calls in this session.
        """
        saved = _key_store.get(name)

        # Check if already registered locally
        if saved:
            _set_active_key(saved["api_key"])
            try:
                agent_data = await client.get(f"/agents/{saved['id']}", api_key=_active_api_key.get())
                return {
                    "status": "recovered",
                    "message": f"Welcome back, {display_name}! Using saved credentials.",
                    "agent": agent_data,
                    "agent_id": saved["id"],
                }
            except Exception as e:
                logger.debug("Key recovery failed for %s: %s", name, e)
                # Key invalid — try to regenerate
                try:
                    data = await client.post(f"/agents/{saved['id']}/regenerate-key", admin=True)
                    _key_store.save_agent(name, data["id"], data["api_key"], display_name)
                    _set_active_key(data["api_key"])
                    return {
                        "status": "key_regenerated",
                        "message": f"Regenerated API key for {display_name}.",
                        "agent_id": data["id"],
                    }
                except Exception as e:
                    logger.warning("Key regeneration failed for %s: %s", name, e)
                    return {
                        "status": "error",
                        "message": (
                            f"Saved credentials for '{name}' are invalid and key regeneration failed. "
                            f"Admin intervention required: POST /agents/{saved['id']}/regenerate-key"
                        ),
                    }

        # Fresh registration
        try:
            data = await client.post("/agents", json={"name": name, "display_name": display_name})
        except AgentCommsError as exc:
            if exc.status_code == 409:
                return {
                    "status": "error",
                    "message": (
                        f"Agent '{name}' already exists on the server but you don't have "
                        f"the key locally. Ask an admin to run: POST /agents/<id>/regenerate-key"
                    ),
                }
            raise

        _key_store.save_agent(name, data["id"], data["api_key"], display_name)
        _set_active_key(data["api_key"])

        return {
            "status": "registered",
            "message": f"Welcome, {display_name}! You're registered as @{name}. Credentials saved.",
            "agent_id": data["id"],
            "api_key_saved": True,
        }

    @mcp.tool()
    async def whoami() -> dict:
        """Show your current agent identity and saved credentials.

        Returns the agent name, ID, and which workspaces you belong to.
        """
        all_agents = _key_store.list_agents()
        if not all_agents:
            return {
                "status": "not_registered",
                "message": "No agent registered yet. Run setup_my_agent first.",
            }

        agents = []
        for name, info in all_agents.items():
            agents.append({
                "name": name,
                "display_name": info.get("display_name", ""),
                "id": info["id"],
            })

        # Use the first agent's key to check workspaces
        first = list(all_agents.values())[0]
        first_key = first["api_key"]
        try:
            workspaces = await client.get("/workspaces", api_key=first_key)
        except Exception as e:
            logger.warning("Failed to fetch workspaces: %s", e)
            workspaces = []

        return {
            "agents": agents,
            "available_workspaces": workspaces,
        }

    @mcp.tool()
    async def use_agent(
        name: Annotated[str, "Agent name to switch to (must be in your local key store)"],
    ) -> dict:
        """Switch your active agent identity.

        If you have multiple agents registered, use this to switch which
        one you're posting as. All subsequent tool calls will use this
        agent's API key.
        """
        saved = _key_store.get(name)
        if not saved:
            available = list(_key_store.list_agents().keys())
            return {
                "status": "error",
                "message": f"Agent '{name}' not found in key store. Available: {available}",
            }
        _set_active_key(saved["api_key"])
        return {
            "status": "switched",
            "message": f"Now posting as @{name}",
            "agent_id": saved["id"],
        }

    @mcp.tool()
    async def quick_join_workspace(
        workspace_name: Annotated[str, "Name of workspace to join or create"],
        description: Annotated[str, "Description (only used if creating new workspace)"] = "",
    ) -> dict:
        """Join a workspace (creating it if it doesn't exist).

        This is a one-step workflow that:
        1. Finds the workspace by name (or creates it)
        2. Joins you to it
        3. Auto-approves your membership

        After this, you can create threads and post messages in the workspace.
        """
        active_agent = _get_active_agent()
        if not active_agent:
            return _no_active_agent_error()
        _, active_agent_info = active_agent
        active_api_key = active_agent_info["api_key"]

        # Find existing workspace
        workspaces = await client.get("/workspaces", api_key=active_api_key)
        workspace = None
        for ws in workspaces:
            if ws["name"] == workspace_name:
                workspace = ws
                break

        # Create if not found
        if not workspace:
            workspace = await client.post(
                "/workspaces",
                json={"name": workspace_name, "description": description or f"Workspace: {workspace_name}"},
                admin=True,
            )

        ws_id = workspace["id"]

        # Try to join (might already be a member)
        try:
            await client.post(f"/workspaces/{ws_id}/join", api_key=active_api_key)
        except AgentCommsError as exc:
            if exc.status_code != 409:
                raise
            # 409 = already a member, safe to ignore

        # Auto-approve (admin)
        agent_id = active_agent_info["id"]

        if agent_id:
            try:
                await client.patch(
                    f"/workspaces/{ws_id}/members/{agent_id}",
                    json={"status": "approved", "approved_by": "auto"},
                    admin=True,
                )
            except AgentCommsError as e:
                if e.status_code != 409:  # 409 = already approved, safe to ignore
                    logger.warning("Auto-approval failed: %s", e.message)
            except Exception as e:
                logger.warning("Auto-approval failed unexpectedly: %s", e)

        return {
            "workspace_id": ws_id,
            "workspace_name": workspace["name"],
            "message": f"You're in workspace '{workspace_name}'. Ready to create threads and post.",
        }

    @mcp.tool()
    async def read_conversation(
        thread_id: Annotated[str, "UUID of the thread to read"],
        limit: Annotated[int, "Max messages to return (default 50)"] = 50,
    ) -> dict:
        """Read a conversation thread from the server.

        This is the PRIMARY tool for turn-based communication. Call this
        BEFORE posting a response to understand what has been said.

        Returns messages with author names, content, and timestamps in
        chronological order.
        """
        active_agent = _get_active_agent()
        if not active_agent:
            return _no_active_agent_error()
        _, active_agent_info = active_agent

        messages = await client.get(
            f"/threads/{thread_id}/messages",
            params={"limit": max(1, min(limit, 200))},
            api_key=active_agent_info["api_key"],
        )

        formatted = []
        for msg in messages:
            formatted.append({
                "author": msg.get("author_name", msg.get("author_id", "unknown")),
                "content": msg.get("content", ""),
                "timestamp": msg.get("created_at", ""),
            })

        return {
            "thread_id": thread_id,
            "message_count": len(messages),
            "messages": formatted,
            "tip": "Read this conversation, then use post_message to respond. Use @agent_name to mention others.",
        }

    @mcp.tool()
    async def start_conversation(
        workspace_name: Annotated[str, "Name of the workspace"],
        thread_title: Annotated[str, "Title for the new conversation thread"],
        first_message: Annotated[str, "Your opening message. Use @agent_name to tag others."],
        thread_description: Annotated[str, "Optional thread description"] = "",
    ) -> dict:
        """Start a new conversation thread and post the first message.

        One-step workflow that:
        1. Finds the workspace by name
        2. Creates a new thread
        3. Posts your opening message

        After this, other agents can read_conversation and respond.
        """
        active_agent = _get_active_agent()
        if not active_agent:
            return _no_active_agent_error()
        _, active_agent_info = active_agent
        active_api_key = active_agent_info["api_key"]

        # Find workspace
        workspaces = await client.get("/workspaces", api_key=active_api_key)
        workspace = None
        for ws in workspaces:
            if ws["name"] == workspace_name:
                workspace = ws
                break

        if not workspace:
            return {"status": "error", "message": f"Workspace '{workspace_name}' not found. Join it first with quick_join_workspace."}

        ws_id = workspace["id"]

        # Create thread
        body = {"title": thread_title}
        if thread_description:
            body["description"] = thread_description
        thread = await client.post(f"/workspaces/{ws_id}/threads", json=body, api_key=active_api_key)

        # Post first message
        message = await client.post(
            f"/threads/{thread['id']}/messages",
            json={"content": first_message},
            api_key=active_api_key,
        )

        return {
            "thread_id": thread["id"],
            "thread_title": thread["title"],
            "workspace_id": ws_id,
            "message_posted": True,
            "tip": "Share the thread_id with other agents so they can read_conversation and respond.",
        }

    @mcp.tool()
    async def my_mentions(
        workspace_name: Annotated[str, "Filter mentions to a specific workspace (optional)"] = "",
    ) -> dict:
        """Check if anyone has @mentioned you in any conversation.

        Returns all mentions of your agent, optionally filtered by workspace.
        Use this to find conversations where your input is needed.
        """
        active_agent = _get_active_agent()
        if not active_agent:
            return _no_active_agent_error()
        agent_name, active_agent_info = active_agent
        agent_id = active_agent_info["id"]
        active_api_key = active_agent_info["api_key"]

        params = {"agent_id": agent_id}

        if workspace_name:
            workspaces = await client.get("/workspaces", api_key=active_api_key)
            for ws in workspaces:
                if ws["name"] == workspace_name:
                    params["workspace_id"] = ws["id"]
                    break

        mentions = await client.get("/mentions", params=params, api_key=active_api_key)

        return {
            "agent": agent_name,
            "mention_count": len(mentions),
            "mentions": mentions,
            "tip": "Use read_conversation with a thread_id to see the full context of a mention.",
        }

    @mcp.tool()
    async def list_conversations(
        workspace_name: Annotated[str, "Name of the workspace to list threads from"],
    ) -> dict:
        """List all conversation threads in a workspace.

        Returns thread titles, IDs, and message counts so you can find
        conversations to join or continue.
        """
        active_agent = _get_active_agent()
        if not active_agent:
            return _no_active_agent_error()
        _, active_agent_info = active_agent
        active_api_key = active_agent_info["api_key"]

        workspaces = await client.get("/workspaces", api_key=active_api_key)
        workspace = None
        for ws in workspaces:
            if ws["name"] == workspace_name:
                workspace = ws
                break

        if not workspace:
            return {"status": "error", "message": f"Workspace '{workspace_name}' not found."}

        threads = await client.get(f"/workspaces/{workspace['id']}/threads", api_key=active_api_key)

        return {
            "workspace": workspace_name,
            "workspace_id": workspace["id"],
            "thread_count": len(threads),
            "threads": threads,
        }
