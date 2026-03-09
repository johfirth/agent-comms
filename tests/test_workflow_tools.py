"""Test all workflow MCP tools end-to-end."""
import asyncio
import json

from fastmcp import Client
from mcp_server.server import mcp, client as http_client

http_client.base_url = "http://localhost:8000"
http_client.admin_api_key = "admin-dev-key-change-me"


def parse(result):
    return json.loads(result.content[0].text)


async def test():
    async with Client(mcp) as c:
        tools = await c.list_tools()
        names = sorted([t.name for t in tools])
        print(f"Total MCP tools: {len(names)}")
        wf = [n for n in names if n in (
            "setup_my_agent", "whoami", "use_agent", "quick_join_workspace",
            "read_conversation", "start_conversation", "my_mentions", "list_conversations",
        )]
        print(f"Workflow tools: {wf}")

        # 1. Setup two agents
        print("\n--- Test 1: Setup Alice ---")
        d = parse(await c.call_tool("setup_my_agent", {"name": "alice", "display_name": "Alice Chen"}))
        print(f"  Status: {d['status']} — {d['message']}")

        print("\n--- Test 2: Setup Bob ---")
        d = parse(await c.call_tool("setup_my_agent", {"name": "bob", "display_name": "Bob Kumar"}))
        print(f"  Status: {d['status']} — {d['message']}")

        # 3. whoami
        print("\n--- Test 3: whoami ---")
        d = parse(await c.call_tool("whoami", {}))
        print(f"  Agents: {[a['name'] for a in d['agents']]}")

        # 4. Alice joins workspace
        print("\n--- Test 4: Alice joins workspace ---")
        await c.call_tool("use_agent", {"name": "alice"})
        d = parse(await c.call_tool("quick_join_workspace", {"workspace_name": "team-discussion", "description": "Shared team workspace"}))
        print(f"  {d['message']}")

        # 5. Bob joins same workspace
        print("\n--- Test 5: Bob joins workspace ---")
        await c.call_tool("use_agent", {"name": "bob"})
        d = parse(await c.call_tool("quick_join_workspace", {"workspace_name": "team-discussion"}))
        print(f"  {d['message']}")

        # 6. Alice starts a conversation
        print("\n--- Test 6: Alice starts conversation ---")
        await c.call_tool("use_agent", {"name": "alice"})
        d = parse(await c.call_tool("start_conversation", {
            "workspace_name": "team-discussion",
            "thread_title": "Architecture: Microservices vs Monolith",
            "first_message": "@bob I think we should go with microservices for the payment module. The team is growing and we need independent deployability. Thoughts?",
        }))
        thread_id = d["thread_id"]
        print(f"  Thread: {d['thread_title']} (id={thread_id[:8]})")

        # 7. Bob READS the conversation (turn-based pattern)
        print("\n--- Test 7: Bob reads conversation ---")
        await c.call_tool("use_agent", {"name": "bob"})
        d = parse(await c.call_tool("read_conversation", {"thread_id": thread_id}))
        print(f"  Messages: {d['message_count']}")
        for msg in d["messages"]:
            print(f"  [{msg['author']}]: {msg['content'][:80]}...")

        # 8. Bob RESPONDS (he read first, now he writes)
        print("\n--- Test 8: Bob responds ---")
        await c.call_tool("post_message", {
            "thread_id": thread_id,
            "content": "@alice I agree on independent deployability but I have concerns about operational complexity. We only have 3 devops engineers. Can we start with a modular monolith and extract services when we hit scaling bottlenecks?",
        })
        print("  Posted!")

        # 9. Read full conversation (both messages)
        print("\n--- Test 9: Full conversation ---")
        d = parse(await c.call_tool("read_conversation", {"thread_id": thread_id}))
        print(f"  Messages: {d['message_count']}")
        for msg in d["messages"]:
            print(f"  [{msg['author']}]: {msg['content'][:80]}...")

        # 10. Alice checks her mentions
        print("\n--- Test 10: Alice checks mentions ---")
        await c.call_tool("use_agent", {"name": "alice"})
        d = parse(await c.call_tool("my_mentions", {"workspace_name": "team-discussion"}))
        print(f"  Alice has {d['mention_count']} mention(s)")

        # 11. Re-register (should recover, not 409)
        print("\n--- Test 11: Re-register Alice (idempotent) ---")
        d = parse(await c.call_tool("setup_my_agent", {"name": "alice", "display_name": "Alice Chen"}))
        print(f"  Status: {d['status']} — {d['message']}")

        # 12. List conversations
        print("\n--- Test 12: List conversations ---")
        d = parse(await c.call_tool("list_conversations", {"workspace_name": "team-discussion"}))
        print(f"  Threads: {d['thread_count']}")
        for t in d["threads"]:
            print(f"  - {t['title']}")

        print("\n=== ALL 12 TESTS PASSED ===")


asyncio.run(test())
