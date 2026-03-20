import json

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from mcp_server.server import mcp, client as mcp_http_client_instance


def _parse(result):
    return json.loads(result.content[0].text)


@pytest.fixture
def workspace_id():
    return "workspace-123"


async def test_list_work_items_invalid_type_raises_tool_error(workspace_id):
    async with Client(mcp) as mcp_client:
        with pytest.raises(ToolError, match="Invalid type 'invalid'"):
            await mcp_client.call_tool(
                "list_work_items",
                {"workspace_id": workspace_id, "type": "invalid"},
            )


async def test_list_work_items_invalid_status_raises_tool_error(workspace_id):
    async with Client(mcp) as mcp_client:
        with pytest.raises(ToolError, match="Invalid status 'invalid_status'"):
            await mcp_client.call_tool(
                "list_work_items",
                {"workspace_id": workspace_id, "status": "invalid_status"},
            )


async def test_list_work_items_returns_list_contract(workspace_id, monkeypatch):
    async def fake_get(path: str, params=None, admin: bool = False, api_key=None):
        assert path == f"/workspaces/{workspace_id}/work-items"
        assert params == {"type": "epic", "status": "backlog"}
        assert admin is False
        return [{"id": "item-1", "type": "epic", "status": "backlog", "title": "MCP Epic"}]

    monkeypatch.setattr(mcp_http_client_instance, "get", fake_get)
    async with Client(mcp) as mcp_client:
        result = await mcp_client.call_tool(
            "list_work_items",
            {"workspace_id": workspace_id, "type": "epic", "status": "backlog"},
        )
        payload = _parse(result)
        assert isinstance(payload, list)
        assert payload
        assert all(isinstance(item, dict) for item in payload)
