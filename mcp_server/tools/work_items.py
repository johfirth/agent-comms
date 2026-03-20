"""MCP tools for work item management."""

from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from mcp_server.client import AgentCommsClient

VALID_WORK_ITEM_TYPES = {"epic", "feature", "story", "task"}
VALID_WORK_ITEM_STATUSES = {"backlog", "in_progress", "review", "done", "cancelled"}


def register_work_item_tools(mcp: FastMCP, client: AgentCommsClient):
    """Register work-item-related MCP tools."""

    @mcp.tool()
    async def create_work_item(
        workspace_id: Annotated[str, "UUID of the workspace"],
        type: Annotated[str, "Work item type: epic, feature, story, or task"],
        title: Annotated[str, "Title of the work item"],
        description: Annotated[str, "Optional description"] = "",
        parent_id: Annotated[
            str,
            "UUID of the parent work item. Required for feature (parent must be epic), "
            "story (parent must be feature), task (parent must be story). "
            "Epics must NOT have a parent.",
        ] = "",
        assigned_agent_id: Annotated[str, "UUID of an agent to assign this work item to"] = "",
    ) -> dict:
        """Create a new work item in a workspace.

        Work items follow a strict hierarchy:
          Epic  (no parent)
            → Feature  (parent must be an Epic)
              → Story  (parent must be a Feature)
                → Task  (parent must be a Story)

        Valid types: epic, feature, story, task.
        parent_id is required for feature, story, and task; it must be omitted
        (or left empty) for epics.
        assigned_agent_id optionally assigns the work item to an agent on creation.
        """
        if type not in VALID_WORK_ITEM_TYPES:
            return {
                "status": "error",
                "message": f"Invalid type '{type}'. Must be one of: {', '.join(sorted(VALID_WORK_ITEM_TYPES))}",
            }
        body: dict = {"type": type, "title": title}
        if description:
            body["description"] = description
        if parent_id:
            body["parent_id"] = parent_id
        if assigned_agent_id:
            body["assigned_agent_id"] = assigned_agent_id
        return await client.post(f"/workspaces/{workspace_id}/work-items", json=body)

    @mcp.tool()
    async def list_work_items(
        workspace_id: Annotated[str, "UUID of the workspace"],
        type: Annotated[str, "Filter by type: epic, feature, story, task"] = "",
        status: Annotated[str, "Filter by status: backlog, in_progress, review, done, cancelled"] = "",
        parent_id: Annotated[str, "Filter by parent work item UUID"] = "",
    ) -> list[dict]:
        """List work items in a workspace with optional filters.

        Filters (all optional):
          type      – epic, feature, story, or task
          status    – backlog, in_progress, review, done, or cancelled
          parent_id – return only direct children of this work item

        Returns a list of work item objects.
        Raises ToolError for invalid filter values.
        """
        params: dict = {}
        if type:
            if type not in VALID_WORK_ITEM_TYPES:
                raise ToolError(
                    f"Invalid type '{type}'. Must be one of: {', '.join(sorted(VALID_WORK_ITEM_TYPES))}"
                )
            params["type"] = type
        if status:
            if status not in VALID_WORK_ITEM_STATUSES:
                raise ToolError(
                    f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_WORK_ITEM_STATUSES))}"
                )
            params["status"] = status
        if parent_id:
            params["parent_id"] = parent_id
        return await client.get(
            f"/workspaces/{workspace_id}/work-items",
            params=params or None,
        )

    @mcp.tool()
    async def get_work_item(
        workspace_id: Annotated[str, "UUID of the workspace"],
        item_id: Annotated[str, "UUID of the work item"],
    ) -> dict:
        """Get full details of a single work item by its ID.

        Returns the work item object including its type, title, description,
        status, parent_id, assigned_agent_id, and timestamps.
        """
        return await client.get(f"/workspaces/{workspace_id}/work-items/{item_id}")

    @mcp.tool()
    async def update_work_item(
        workspace_id: Annotated[str, "UUID of the workspace"],
        item_id: Annotated[str, "UUID of the work item to update"],
        title: Annotated[str, "New title"] = "",
        description: Annotated[str, "New description"] = "",
        status: Annotated[
            str,
            "New status: backlog, in_progress, review, done, or cancelled",
        ] = "",
        assigned_agent_id: Annotated[str, "UUID of agent to assign (or empty to keep current)"] = "",
    ) -> dict:
        """Update one or more fields of an existing work item.

        Only the fields you supply (non-empty) will be changed; all other
        fields remain untouched.

        Updatable fields:
          title             – new title string
          description       – new description string
          status            – backlog, in_progress, review, done, or cancelled
          assigned_agent_id – UUID of the agent to assign
        """
        body: dict = {}
        if title:
            body["title"] = title
        if description:
            body["description"] = description
        if status:
            if status not in VALID_WORK_ITEM_STATUSES:
                return {
                    "status": "error",
                    "message": f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_WORK_ITEM_STATUSES))}",
                }
            body["status"] = status
        if assigned_agent_id:
            body["assigned_agent_id"] = assigned_agent_id
        return await client.patch(
            f"/workspaces/{workspace_id}/work-items/{item_id}",
            json=body,
        )
