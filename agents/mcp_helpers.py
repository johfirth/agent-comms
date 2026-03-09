"""Shared helpers for MCP-based orchestrator scripts.

Provides register-or-recover logic that uses the key store to persist agent
credentials across runs, and utility functions for extracting MCP results.
"""

import json
import logging
from agents.key_store import KeyStore

logger = logging.getLogger(__name__)

_default_key_store = KeyStore()


def extract_result(result) -> dict | list | str:
    """Extract usable data from a FastMCP CallToolResult."""
    if hasattr(result, "content") and result.content:
        text = result.content[0].text
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return text
    return str(result)


async def register_or_recover(mcp_client, http_client, agent: dict,
                              key_store: KeyStore | None = None) -> dict:
    """Register an agent via MCP, or recover credentials from the key store.

    Args:
        mcp_client: FastMCP Client instance (connected)
        http_client: The underlying AgentCommsClient from the MCP server
        agent: Dict with 'name' and 'display_name' keys (modified in place with 'id' and 'api_key')
        key_store: Optional KeyStore instance (uses default if not provided)

    Returns:
        The agent dict with 'id' and 'api_key' populated.
    """
    store = key_store or _default_key_store
    saved = store.get(agent["name"])

    if saved:
        # Verify the saved key still works
        http_client.api_key = saved["api_key"]
        try:
            result = await mcp_client.call_tool("get_agent", {"agent_id": saved["id"]})
            data = extract_result(result)
            agent["id"] = saved["id"]
            agent["api_key"] = saved["api_key"]
            logger.info("Reusing saved credentials for %s (id=%s)", agent["name"], agent["id"][:8])
            return agent
        except Exception:
            # Key is invalid — regenerate via admin
            logger.warning("Saved key invalid for %s, regenerating...", agent["name"])
            try:
                result = await mcp_client.call_tool(
                    "regenerate_agent_key", {"agent_id": saved["id"]}
                )
                data = extract_result(result)
                agent["id"] = data["id"]
                agent["api_key"] = data["api_key"]
                store.save_agent(agent["name"], agent["id"], agent["api_key"], agent.get("display_name", ""))
                logger.info("Regenerated key for %s", agent["name"])
                return agent
            except Exception as regen_exc:
                logger.warning("Regeneration failed for %s: %s", agent["name"], regen_exc)

    # Try fresh registration
    try:
        result = await mcp_client.call_tool(
            "register_agent",
            {"name": agent["name"], "display_name": agent["display_name"]},
        )
        data = extract_result(result)
        agent["id"] = data["id"]
        agent["api_key"] = data["api_key"]
        store.save_agent(agent["name"], agent["id"], agent["api_key"], agent["display_name"])
        logger.info("Registered %s (id=%s)", agent["display_name"], agent["id"][:8])
        return agent
    except Exception as exc:
        if "409" in str(exc):
            raise RuntimeError(
                f"Agent '{agent['name']}' exists on server but no local key found. "
                f"Either reset the database (docker compose down -v) or use the admin API: "
                f"POST /agents/<id>/regenerate-key"
            ) from exc
        raise
