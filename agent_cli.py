#!/usr/bin/env python
"""
agent_cli.py — CLI bridge for the Agent Communication Server.

Provides the same functionality as the MCP tools, but accessible via
command line. Sub-agents spawned by the `task` tool use this CLI via
`powershell` when MCP tools aren't directly available.

Usage:
    python agent_cli.py setup <name> <display_name>
    python agent_cli.py read <thread_id> [--limit N]
    python agent_cli.py post <agent_name> <thread_id> [content | --file path | --stdin]
    python agent_cli.py join <agent_name> <workspace_name>
    python agent_cli.py threads <workspace_name>
    python agent_cli.py mentions <agent_name> [--workspace <name>]

All output is JSON for easy parsing by agents.
"""

import argparse
import json
import os
import sys

import httpx

from agents.key_store import KeyStore

BASE_URL = os.environ.get("AGENT_COMMS_URL", "http://localhost:8000")
ADMIN_KEY = os.environ.get("AGENT_COMMS_ADMIN_KEY", "admin-dev-key-change-me")

_key_store = KeyStore()


def _out(data):
    """Print JSON output to stdout."""
    print(json.dumps(data, indent=2))


def _err(msg, exit_code=1):
    """Print error JSON to stderr and exit."""
    print(json.dumps({"error": msg}), file=sys.stderr)
    sys.exit(exit_code)


def get_agent(agent_name):
    """Look up agent credentials from the shared key store."""
    saved = _key_store.get(agent_name)
    if not saved:
        available = sorted(_key_store.list_agents().keys())
        _err(f"Agent '{agent_name}' not found in keys.json. "
             f"Available: {', '.join(available)}")
    return saved


def _headers(api_key):
    return {"X-API-Key": api_key, "Content-Type": "application/json"}


def _admin_headers():
    return {"X-API-Key": ADMIN_KEY, "Content-Type": "application/json"}


def _find_workspace(name):
    """Find a workspace by name, return its ID."""
    r = httpx.get(f"{BASE_URL}/workspaces", timeout=10)
    r.raise_for_status()
    for ws in r.json():
        if ws["name"] == name:
            return ws
    _err(f"Workspace '{name}' not found")


# ── Commands ──────────────────────────────────────────────────────────


def cmd_setup(args):
    """Register or recover agent credentials."""
    saved = _key_store.get(args.name)

    if saved:
        try:
            r = httpx.get(f"{BASE_URL}/agents/{saved['id']}", timeout=10)
            if r.status_code == 200:
                _out({
                    "status": "recovered",
                    "agent_id": saved["id"],
                    "name": args.name,
                    "display_name": saved.get("display_name", ""),
                })
                return
        except Exception:
            pass

    try:
        r = httpx.post(
            f"{BASE_URL}/agents",
            json={"name": args.name, "display_name": args.display_name},
            timeout=10,
        )
        if r.status_code == 201:
            data = r.json()
            _key_store.save_agent(args.name, data["id"], data["api_key"], args.display_name)
            _out({"status": "registered", "agent_id": data["id"], "name": args.name})
        elif r.status_code == 409:
            _err(f"Agent name '{args.name}' already taken on server")
        else:
            _err(f"HTTP {r.status_code}: {r.text}")
    except httpx.ConnectError:
        _err(f"Cannot connect to agent-comms server at {BASE_URL}")


def cmd_read(args):
    """Read conversation from a thread."""
    try:
        r = httpx.get(
            f"{BASE_URL}/threads/{args.thread_id}/messages",
            params={"limit": args.limit},
            timeout=30,
        )
        r.raise_for_status()
        messages = r.json()
        formatted = [
            {
                "author": m.get("author_name", "unknown"),
                "content": m["content"],
                "timestamp": m.get("created_at", ""),
            }
            for m in messages
        ]
        _out({
            "thread_id": args.thread_id,
            "message_count": len(formatted),
            "messages": formatted,
        })
    except httpx.ConnectError:
        _err(f"Cannot connect to agent-comms server at {BASE_URL}")
    except httpx.HTTPStatusError as e:
        _err(f"HTTP {e.response.status_code}: {e.response.text}")


def cmd_post(args):
    """Post a message to a thread."""
    agent = get_agent(args.agent_name)

    # Resolve content: --file > --stdin > positional arg
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
        except (FileNotFoundError, OSError) as e:
            _err(f"Cannot read file '{args.file}': {e}")
    elif args.stdin:
        content = sys.stdin.read()
    elif args.content:
        content = args.content
    else:
        # Try reading from stdin if it's piped
        if not sys.stdin.isatty():
            content = sys.stdin.read()
        else:
            _err("No message content provided. Use positional arg, --file, or --stdin")

    if not content.strip():
        _err("Empty message content")

    try:
        r = httpx.post(
            f"{BASE_URL}/threads/{args.thread_id}/messages",
            json={"content": content},
            headers=_headers(agent["api_key"]),
            timeout=30,
        )
        if r.status_code == 201:
            data = r.json()
            _out({
                "status": "posted",
                "message_id": data["id"],
                "thread_id": args.thread_id,
                "author": data.get("author_name", args.agent_name),
            })
        else:
            _err(f"HTTP {r.status_code}: {r.text}")
    except httpx.ConnectError:
        _err(f"Cannot connect to agent-comms server at {BASE_URL}")


def cmd_join(args):
    """Join a workspace by name."""
    agent = get_agent(args.agent_name)
    ws = _find_workspace(args.workspace_name)
    ws_id = ws["id"]

    try:
        # Request to join
        r = httpx.post(
            f"{BASE_URL}/workspaces/{ws_id}/join",
            headers=_headers(agent["api_key"]),
            timeout=10,
        )
        r.raise_for_status()
        # Auto-approve via admin
        r = httpx.patch(
            f"{BASE_URL}/workspaces/{ws_id}/members/{agent['id']}",
            json={"status": "approved", "approved_by": "auto"},
            headers=_admin_headers(),
            timeout=10,
        )
        r.raise_for_status()
        _out({
            "status": "joined",
            "workspace_id": ws_id,
            "workspace_name": args.workspace_name,
        })
    except httpx.ConnectError:
        _err(f"Cannot connect to agent-comms server at {BASE_URL}")
    except httpx.HTTPStatusError as e:
        _err(f"HTTP {e.response.status_code}: {e.response.text}")


def cmd_threads(args):
    """List threads in a workspace."""
    ws = _find_workspace(args.workspace_name)
    try:
        r = httpx.get(
            f"{BASE_URL}/workspaces/{ws['id']}/threads",
            timeout=10,
        )
        r.raise_for_status()
        threads = r.json()
        _out({
            "workspace": args.workspace_name,
            "thread_count": len(threads),
            "threads": [
                {"id": t["id"], "title": t["title"], "created_at": t.get("created_at", "")}
                for t in threads
            ],
        })
    except httpx.ConnectError:
        _err(f"Cannot connect to agent-comms server at {BASE_URL}")


def cmd_mentions(args):
    """Check mentions for an agent."""
    agent = get_agent(args.agent_name)
    params = {"agent_id": agent["id"]}

    if args.workspace:
        ws = _find_workspace(args.workspace)
        params["workspace_id"] = ws["id"]

    try:
        r = httpx.get(f"{BASE_URL}/mentions", params=params, timeout=10)
        r.raise_for_status()
        mentions = r.json()
        _out({
            "agent": args.agent_name,
            "mention_count": len(mentions),
            "mentions": mentions,
        })
    except httpx.ConnectError:
        _err(f"Cannot connect to agent-comms server at {BASE_URL}")
    except httpx.HTTPStatusError as e:
        _err(f"HTTP {e.response.status_code}: {e.response.text}")


# ── Argument Parser ──────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Agent Communication CLI — bridge for sub-agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # setup
    p = sub.add_parser("setup", help="Register or recover agent credentials")
    p.add_argument("name", help="Agent name (for @mentions)")
    p.add_argument("display_name", help="Human-readable display name")

    # read
    p = sub.add_parser("read", help="Read conversation from a thread")
    p.add_argument("thread_id", help="Thread UUID")
    p.add_argument("--limit", type=int, default=50, help="Max messages (default: 50)")

    # post
    p = sub.add_parser("post", help="Post a message to a thread")
    p.add_argument("agent_name", help="Agent name to post as")
    p.add_argument("thread_id", help="Thread UUID")
    p.add_argument("content", nargs="?", default=None, help="Message content")
    p.add_argument("--file", "-f", dest="file", help="Read content from file")
    p.add_argument("--stdin", action="store_true", help="Read content from stdin")

    # join
    p = sub.add_parser("join", help="Join a workspace by name")
    p.add_argument("agent_name", help="Agent name")
    p.add_argument("workspace_name", help="Workspace name")

    # threads
    p = sub.add_parser("threads", help="List threads in a workspace")
    p.add_argument("workspace_name", help="Workspace name")

    # mentions
    p = sub.add_parser("mentions", help="Check @mentions for an agent")
    p.add_argument("agent_name", help="Agent name")
    p.add_argument("--workspace", help="Filter by workspace name")

    args = parser.parse_args()

    commands = {
        "setup": cmd_setup,
        "read": cmd_read,
        "post": cmd_post,
        "join": cmd_join,
        "threads": cmd_threads,
        "mentions": cmd_mentions,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
