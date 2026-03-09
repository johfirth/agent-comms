"""Entry point for the Agent Communication MCP Server.

Run with:  python -m mcp_server
Or:        fastmcp run mcp_server/server.py

Environment variables:
  AGENT_COMMS_URL       - Base URL of the Agent Communication Server (default: http://localhost:8000)
  AGENT_COMMS_API_KEY   - API key for the authenticated agent
  AGENT_COMMS_ADMIN_KEY - Admin API key for administrative operations
"""

from mcp_server.server import mcp

if __name__ == "__main__":
    mcp.run()
