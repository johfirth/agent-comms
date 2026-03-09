"""MCP Server for the Agent Communication Server.

Exposes all API functionality as MCP tools for AI agent integration.
"""

from fastmcp import FastMCP

from mcp_server.client import AgentCommsClient
from mcp_server.tools.workspaces import register_workspace_tools
from mcp_server.tools.agents import register_agent_tools
from mcp_server.tools.threads import register_thread_tools
from mcp_server.tools.work_items import register_work_item_tools

mcp = FastMCP(
    "Agent Communication Server",
    instructions=(
        "This MCP server provides tools for AI agents to collaborate in workspaces. "
        "Agents can join workspaces (with human approval), create threads to discuss issues, "
        "@mention each other, and manage software work items (Epics → Features → Stories → Tasks). "
        "Use the tools below to interact with the communication server."
    ),
)

client = AgentCommsClient()

register_workspace_tools(mcp, client)
register_agent_tools(mcp, client)
register_thread_tools(mcp, client)
register_work_item_tools(mcp, client)
