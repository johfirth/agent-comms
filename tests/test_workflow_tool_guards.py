import json

import pytest
from fastmcp import Client

from mcp_server.server import mcp, client as mcp_http_client_instance
from mcp_server.tools import workflows as workflow_tools

NO_ACTIVE_AGENT_ERROR = {
    "status": "error",
    "message": "No active agent. Run setup_my_agent first.",
}


def _parse(result):
    return json.loads(result.content[0].text)


@pytest.fixture
def no_active_agent():
    workflow_tools._active_api_key.set(None)
    yield
    workflow_tools._active_api_key.set(None)


@pytest.fixture
def fail_on_api_call(monkeypatch):
    async def _fail(*_args, **_kwargs):
        raise AssertionError("Expected no API call when active agent is missing.")

    monkeypatch.setattr(mcp_http_client_instance, "get", _fail)
    monkeypatch.setattr(mcp_http_client_instance, "post", _fail)
    monkeypatch.setattr(mcp_http_client_instance, "patch", _fail)


@pytest.mark.parametrize(
    ("tool_name", "args"),
    [
        ("quick_join_workspace", {"workspace_name": "team-discussion"}),
        ("read_conversation", {"thread_id": "thread-123"}),
        (
            "start_conversation",
            {
                "workspace_name": "team-discussion",
                "thread_title": "Thread title",
                "first_message": "Hello team",
            },
        ),
        ("list_conversations", {"workspace_name": "team-discussion"}),
        ("my_mentions", {}),
    ],
)
async def test_workflow_tools_require_active_agent(no_active_agent, fail_on_api_call, tool_name, args):
    async with Client(mcp) as mcp_client:
        result = await mcp_client.call_tool(tool_name, args)

    assert _parse(result) == NO_ACTIVE_AGENT_ERROR
