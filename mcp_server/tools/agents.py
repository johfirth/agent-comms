from typing import Annotated

from fastmcp import FastMCP

from mcp_server.client import AgentCommsClient


def register_agent_tools(mcp: FastMCP, client: AgentCommsClient):
    """Register agent management tools on the MCP server."""

    @mcp.tool()
    async def register_agent(
        name: Annotated[str, "Unique agent name (used for @mentions, max 100 chars)"],
        display_name: Annotated[str, "Human-readable display name"],
    ) -> dict:
        """Register a new agent and receive its API key.

        WARNING: The API key is returned only once in the response.
        The agent must save it immediately — it cannot be retrieved again.
        """
        return await client.post(
            "/agents", json={"name": name, "display_name": display_name}
        )

    @mcp.tool()
    async def get_agent(
        agent_id: Annotated[str, "UUID of the agent"],
    ) -> dict:
        """Get an agent's profile by ID. Does not include the API key."""
        return await client.get(f"/agents/{agent_id}")

    @mcp.tool()
    async def set_webhook(
        agent_id: Annotated[str, "UUID of the agent (must be your own)"],
        webhook_url: Annotated[str, "URL to receive webhook notifications"],
    ) -> dict:
        """Set the webhook URL for an agent to receive @mention notifications."""
        return await client.put(
            f"/agents/{agent_id}/webhook", json={"webhook_url": webhook_url}
        )

    @mcp.tool()
    async def search_mentions(
        agent_id: Annotated[str, "UUID of the agent to search mentions for"],
        workspace_id: Annotated[str, "Optionally filter by workspace UUID"] = "",
    ) -> list[dict]:
        """Search all @mentions of a specific agent.

        This is how agents check if they have been tagged in a conversation.
        Optionally filter results to a single workspace.
        """
        params: dict = {"agent_id": agent_id}
        if workspace_id:
            params["workspace_id"] = workspace_id
        return await client.get("/mentions", params=params)
