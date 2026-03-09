"""Demo: Two agents collaborating on a software project via the Agent Communication Server.

Usage: python -m agents.run_demo

Requires:
  - Agent Communication Server running at http://localhost:8000
  - AGENT_COMMS_ADMIN_KEY set (default: admin-dev-key-change-me)
"""

import asyncio
import logging
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.client import AgentCommsClient
from agents.architect import ArchitectAgent
from agents.developer import DeveloperAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main():
    base_url = os.environ.get("AGENT_COMMS_URL", "http://localhost:8000")
    admin_key = os.environ.get("AGENT_COMMS_ADMIN_KEY", "admin-dev-key-change-me")

    # Each agent gets its own client instance (different API keys)
    architect_client = AgentCommsClient(base_url=base_url, admin_api_key=admin_key)
    developer_client = AgentCommsClient(base_url=base_url, admin_api_key=admin_key)

    architect = ArchitectAgent("architect-ai", "Architect AI", architect_client)
    developer = DeveloperAgent("developer-ai", "Developer AI", developer_client)

    print("\n" + "=" * 60)
    print("  Agent Communication Demo")
    print("  Two AI agents collaborating on a software project")
    print("=" * 60 + "\n")

    # --- Phase 1: Setup ---
    print("📋 Phase 1: Setup\n")

    # Register agents
    await architect.register()
    await developer.register()

    # Admin creates workspace
    ws = await architect_client.post("/workspaces", json={
        "name": "auth-project",
        "description": "Authentication System Development"
    }, admin=True)
    workspace_id = ws["id"]
    logger.info("Created workspace: %s", ws["name"])

    # Agents join workspace
    await architect.join_workspace(workspace_id)
    await developer.join_workspace(workspace_id)

    # Admin approves both
    await architect_client.patch(
        f"/workspaces/{workspace_id}/members/{architect.agent_id}",
        json={"status": "approved", "approved_by": "admin"}, admin=True
    )
    await developer_client.patch(
        f"/workspaces/{workspace_id}/members/{developer.agent_id}",
        json={"status": "approved", "approved_by": "admin"}, admin=True
    )
    logger.info("Both agents approved in workspace")

    print("\n" + "-" * 60)
    print("📐 Phase 2: Project Planning\n")

    # Architect plans the project
    plan = await architect.plan_project(workspace_id, developer.agent_id, developer.name)
    main_thread_id = plan["thread"]["id"]
    tasks = plan["tasks"]

    print("\n" + "-" * 60)
    print("💬 Phase 3: Agent Conversation\n")

    # Developer acknowledges and asks questions
    await developer.acknowledge_plan(main_thread_id, architect.name)

    # Developer picks up first task (JWT utility — last in the list)
    jwt_task = tasks[3]  # "Create JWT utility module"
    await developer.start_task(workspace_id, jwt_task, main_thread_id, architect.name)

    # Architect reviews and opens code review thread
    review_thread = await architect.review_and_respond(
        main_thread_id, developer.name, tasks, workspace_id
    )

    # Developer responds to code review
    await developer.respond_to_review(review_thread["id"], architect.name)

    # Developer posts progress
    await developer.post_progress(main_thread_id, architect.name, jwt_task["title"])

    # Developer completes the task
    await developer.complete_task(workspace_id, jwt_task, main_thread_id, architect.name)

    # Developer starts next task
    login_api_task = tasks[1]  # "Implement login API endpoint"
    await developer.start_task(workspace_id, login_api_task, main_thread_id, architect.name)

    # Developer asks a technical question
    await developer.ask_question(main_thread_id, architect.name)

    # Architect responds
    await architect.post_message(
        main_thread_id,
        f"@{developer.name} Great question! Let's go with option 2 (HttpOnly cookie) "
        f"for the refresh token. We'll be deploying on the same domain initially "
        f"(api.example.com serves both frontend and API behind a reverse proxy), "
        f"so CORS won't be an issue.\n\n"
        f"For the access token, return it in the response body — the frontend stores "
        f"it in memory (not localStorage). This gives us the best security profile."
    )

    print("\n" + "-" * 60)
    print("🔍 Phase 4: Verification\n")

    # Check mentions for each agent
    architect_mentions = await architect.check_mentions(workspace_id)
    developer_mentions = await developer.check_mentions(workspace_id)
    logger.info("Architect was @mentioned %d time(s)", len(architect_mentions))
    logger.info("Developer was @mentioned %d time(s)", len(developer_mentions))

    # List all messages in main thread
    all_messages = await architect.list_messages(main_thread_id)
    logger.info("Main thread has %d messages", len(all_messages))

    # List work items
    all_items = await architect.list_work_items(workspace_id)
    logger.info("Workspace has %d work items", len(all_items))

    # Summary
    print("\n" + "=" * 60)
    print("  ✅ Demo Complete!")
    print(f"  📊 {len(all_messages)} messages exchanged")
    print(f"  📋 {len(all_items)} work items created")
    print(f"  📢 {len(architect_mentions)} @mentions of architect")
    print(f"  📢 {len(developer_mentions)} @mentions of developer")
    print(f"  🧵 2 discussion threads")
    print("=" * 60 + "\n")
    print("All communications are logged in the Agent Communication Server.")
    print(f"API docs: {base_url}/docs")


if __name__ == "__main__":
    asyncio.run(main())
