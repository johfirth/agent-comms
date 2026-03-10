"""High-level workflow tools for Copilot CLI agent communication.

These tools combine multiple API calls into single-step workflows that
make it easy for any Copilot CLI user to participate in agent conversations.
The key store persists agent credentials locally so agents survive across sessions.
"""

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP

from mcp_server.client import AgentCommsClient, AgentCommsError

# Key store path — at project root (agents/keys.json)
# This file contains plaintext API keys and MUST NOT be committed to git.
# It is listed in .gitignore.  On Unix, file permissions are set to 0600.
KEY_STORE_PATH = Path(__file__).parent.parent.parent / "agents" / "keys.json"


def _load_keys() -> dict:
    if KEY_STORE_PATH.exists():
        return json.loads(KEY_STORE_PATH.read_text(encoding="utf-8"))
    return {}


def _save_keys(data: dict):
    KEY_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    KEY_STORE_PATH.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    # Restrict file permissions to owner-only on platforms that support it
    try:
        KEY_STORE_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except OSError:
        pass  # Windows ACLs don't support POSIX modes; acceptable fallback


def register_workflow_tools(mcp: FastMCP, client: AgentCommsClient):
    """Register high-level workflow tools for easy Copilot CLI usage."""

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
        keys = _load_keys()

        # Check if already registered locally
        if name in keys:
            saved = keys[name]
            # Verify the key still works
            client.api_key = saved["api_key"]
            try:
                agent_data = await client.get(f"/agents/{saved['id']}")
                return {
                    "status": "recovered",
                    "message": f"Welcome back, {display_name}! Using saved credentials.",
                    "agent": agent_data,
                    "agent_id": saved["id"],
                }
            except Exception:
                # Key invalid — try to regenerate
                try:
                    data = await client.post(f"/agents/{saved['id']}/regenerate-key", admin=True)
                    keys[name] = {"id": data["id"], "api_key": data["api_key"], "display_name": display_name}
                    _save_keys(keys)
                    client.api_key = data["api_key"]
                    return {
                        "status": "key_regenerated",
                        "message": f"Regenerated API key for {display_name}.",
                        "agent_id": data["id"],
                    }
                except Exception:
                    pass  # Fall through to fresh registration

        # Fresh registration
        try:
            data = await client.post("/agents", json={"name": name, "display_name": display_name})
        except Exception as exc:
            if "409" in str(exc):
                return {
                    "status": "error",
                    "message": (
                        f"Agent '{name}' already exists on the server but you don't have "
                        f"the key locally. Ask an admin to run: POST /agents/<id>/regenerate-key"
                    ),
                }
            raise

        keys[name] = {"id": data["id"], "api_key": data["api_key"], "display_name": display_name}
        _save_keys(keys)
        client.api_key = data["api_key"]

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
        keys = _load_keys()
        if not keys:
            return {
                "status": "not_registered",
                "message": "No agent registered yet. Run setup_my_agent first.",
            }

        agents = []
        for name, info in keys.items():
            agents.append({
                "name": name,
                "display_name": info.get("display_name", ""),
                "id": info["id"],
            })

        # Use the first agent's key to check workspaces
        first = list(keys.values())[0]
        client.api_key = first["api_key"]
        try:
            workspaces = await client.get("/workspaces")
        except Exception:
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
        keys = _load_keys()
        if name not in keys:
            return {
                "status": "error",
                "message": f"Agent '{name}' not found in key store. Available: {list(keys.keys())}",
            }
        saved = keys[name]
        client.api_key = saved["api_key"]
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
        # Find existing workspace
        workspaces = await client.get("/workspaces")
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
            await client.post(f"/workspaces/{ws_id}/join")
        except Exception as exc:
            if "already" not in str(exc).lower() and "409" not in str(exc):
                raise

        # Auto-approve (admin)
        # Need to figure out our agent ID from the key store
        keys = _load_keys()
        agent_id = None
        for name, info in keys.items():
            if info["api_key"] == client.api_key:
                agent_id = info["id"]
                break

        if agent_id:
            try:
                await client.patch(
                    f"/workspaces/{ws_id}/members/{agent_id}",
                    json={"status": "approved", "approved_by": "auto"},
                    admin=True,
                )
            except Exception:
                pass  # Already approved

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
        messages = await client.get(
            f"/threads/{thread_id}/messages",
            params={"limit": limit},
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
        # Find workspace
        workspaces = await client.get("/workspaces")
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
        thread = await client.post(f"/workspaces/{ws_id}/threads", json=body)

        # Post first message
        message = await client.post(
            f"/threads/{thread['id']}/messages",
            json={"content": first_message},
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
        # Find our agent ID
        keys = _load_keys()
        agent_id = None
        agent_name = None
        for name, info in keys.items():
            if info["api_key"] == client.api_key:
                agent_id = info["id"]
                agent_name = name
                break

        if not agent_id:
            return {"status": "error", "message": "No active agent. Run setup_my_agent first."}

        params = {"agent_id": agent_id}

        if workspace_name:
            workspaces = await client.get("/workspaces")
            for ws in workspaces:
                if ws["name"] == workspace_name:
                    params["workspace_id"] = ws["id"]
                    break

        mentions = await client.get("/mentions", params=params)

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
        workspaces = await client.get("/workspaces")
        workspace = None
        for ws in workspaces:
            if ws["name"] == workspace_name:
                workspace = ws
                break

        if not workspace:
            return {"status": "error", "message": f"Workspace '{workspace_name}' not found."}

        threads = await client.get(f"/workspaces/{workspace['id']}/threads")

        return {
            "workspace": workspace_name,
            "workspace_id": workspace["id"],
            "thread_count": len(threads),
            "threads": threads,
        }
