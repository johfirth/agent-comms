"""MCP tools for threads and messages."""

from typing import Annotated

from fastmcp import FastMCP

from mcp_server.client import AgentCommsClient


def register_thread_tools(mcp: FastMCP, client: AgentCommsClient):
    """Register thread and message tools on the MCP server."""

    @mcp.tool()
    async def create_thread(
        workspace_id: Annotated[str, "UUID of the workspace"],
        title: Annotated[str, "Thread title"],
        description: Annotated[str, "Optional thread description"] = "",
        work_item_id: Annotated[str, "Optional UUID of a work item to link this thread to"] = "",
    ) -> dict:
        """Create a new discussion thread in a workspace."""
        body: dict = {"title": title}
        if description:
            body["description"] = description
        if work_item_id:
            body["work_item_id"] = work_item_id
        return await client.post(f"/workspaces/{workspace_id}/threads", json=body)

    @mcp.tool()
    async def list_threads(
        workspace_id: Annotated[str, "UUID of the workspace"],
        work_item_id: Annotated[str, "Optionally filter threads by linked work item UUID"] = "",
    ) -> list[dict]:
        """List threads in a workspace."""
        params: dict = {}
        if work_item_id:
            params["work_item_id"] = work_item_id
        return await client.get(f"/workspaces/{workspace_id}/threads", params=params or None)

    @mcp.tool()
    async def get_thread(
        workspace_id: Annotated[str, "UUID of the workspace"],
        thread_id: Annotated[str, "UUID of the thread"],
    ) -> dict:
        """Get thread details."""
        return await client.get(f"/workspaces/{workspace_id}/threads/{thread_id}")

    @mcp.tool()
    async def post_message(
        thread_id: Annotated[str, "UUID of the thread"],
        content: Annotated[str, "Message content. Use @agent_name to mention other agents."],
    ) -> dict:
        """Post a message to a thread.

        Any @agent_name patterns in the content will automatically create
        mention records and trigger webhook notifications.
        """
        return await client.post(f"/threads/{thread_id}/messages", json={"content": content})

    @mcp.tool()
    async def list_messages(
        thread_id: Annotated[str, "UUID of the thread"],
        limit: Annotated[int, "Max messages to return (1-200)"] = 50,
        offset: Annotated[int, "Number of messages to skip"] = 0,
    ) -> list[dict]:
        """List messages in a thread with pagination."""
        return await client.get(
            f"/threads/{thread_id}/messages",
            params={"limit": limit, "offset": offset},
        )
