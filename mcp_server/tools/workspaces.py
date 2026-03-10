"""MCP tools for workspace management."""

from typing import Annotated

from fastmcp import FastMCP

from mcp_server.client import AgentCommsClient


def register_workspace_tools(mcp: FastMCP, client: AgentCommsClient):
    """Register workspace-related MCP tools."""

    @mcp.tool()
    async def list_workspaces() -> list[dict]:
        """List all available workspaces."""
        return await client.get("/workspaces")

    @mcp.tool()
    async def get_workspace(
        workspace_id: Annotated[str, "UUID of the workspace"],
    ) -> dict:
        """Get details of a specific workspace by its ID."""
        return await client.get(f"/workspaces/{workspace_id}")

    @mcp.tool()
    async def create_workspace(
        name: Annotated[str, "Unique workspace name"],
        description: Annotated[str, "Description of the workspace"] = "",
    ) -> dict:
        """Create a new workspace. Requires admin privileges."""
        return await client.post(
            "/workspaces",
            json={"name": name, "description": description},
            admin=True,
        )

    @mcp.tool()
    async def join_workspace(
        workspace_id: Annotated[str, "UUID of the workspace to join"],
    ) -> dict:
        """Request to join a workspace. Requires human approval before access is granted."""
        return await client.post(f"/workspaces/{workspace_id}/join")

    @mcp.tool()
    async def list_members(
        workspace_id: Annotated[str, "UUID of the workspace"],
        status: Annotated[str, "Filter by status: pending, approved, or rejected"] = "",
    ) -> list[dict]:
        """List members of a workspace, optionally filtered by membership status."""
        params = {}
        if status:
            params["status"] = status
        return await client.get(
            f"/workspaces/{workspace_id}/members",
            params=params or None,
        )

    @mcp.tool()
    async def approve_member(
        workspace_id: Annotated[str, "UUID of the workspace"],
        agent_id: Annotated[str, "UUID of the agent to approve"],
        approved_by: Annotated[str, "Name of the person approving"] = "admin",
    ) -> dict:
        """Approve an agent's request to join a workspace. Requires admin privileges."""
        return await client.patch(
            f"/workspaces/{workspace_id}/members/{agent_id}",
            json={"status": "approved", "approved_by": approved_by},
            admin=True,
        )

    @mcp.tool()
    async def reject_member(
        workspace_id: Annotated[str, "UUID of the workspace"],
        agent_id: Annotated[str, "UUID of the agent to reject"],
        rejected_by: Annotated[str, "Name of the person rejecting"] = "admin",
    ) -> dict:
        """Reject an agent's request to join a workspace. Requires admin privileges."""
        return await client.patch(
            f"/workspaces/{workspace_id}/members/{agent_id}",
            json={"status": "rejected", "approved_by": rejected_by},
            admin=True,
        )
