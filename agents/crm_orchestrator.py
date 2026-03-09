"""CRM Discussion Orchestrator — Copilot CLI drives two agents via MCP tools.

Copilot CLI acts as the brain behind both agents. No external LLM API is used.
All communication flows through the Agent Comms Server via the MCP tool layer
(FastMCP Client → MCP Server → AgentCommsClient → REST API).

Usage: python -m agents.crm_orchestrator

Requires:
  - Agent Communication Server running at http://localhost:8000
  - AGENT_COMMS_ADMIN_KEY set (default: admin-dev-key-change-me)
"""

import asyncio
import json
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import Client
from mcp_server.server import mcp as mcp_server
from mcp_server.server import client as http_client
from agents.mcp_helpers import extract_result, register_or_recover

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Conversation content (authored by Copilot CLI) ────────────────────────

CONVERSATION = [
    # Turn 1 — Architect opens the discussion
    {
        "agent": "architect",
        "content": (
            "@developer-ai Let's kick off our CRM requirements discussion. I've been thinking about "
            "what makes a CRM system truly effective vs. just another contacts database. "
            "Here are the high-level categories I think we need to nail:\n\n"
            "1. **Contact & Account Management** — the core data model\n"
            "2. **Sales Pipeline / Deal Tracking** — stages, forecasting\n"
            "3. **Communication Tracking** — emails, calls, meetings logged automatically\n"
            "4. **Reporting & Analytics** — dashboards, KPIs, funnel analysis\n"
            "5. **Workflow Automation** — triggers, rules, follow-up sequences\n"
            "6. **Integration Ecosystem** — email, calendar, marketing, support tools\n\n"
            "That's my starting six. What's your take — am I missing anything fundamental? "
            "I want us to land on a definitive top 10."
        ),
    },
    # Turn 2 — Developer responds
    {
        "agent": "developer",
        "content": (
            "@architect-ai Good foundation, but I think you're skewing too heavily toward the sales side. "
            "A modern CRM needs to serve marketing, support, and CS teams equally. Here's what I'd add:\n\n"
            "7. **API-First Architecture** — this is non-negotiable. If the CRM can't be extended "
            "programmatically, it becomes a silo. REST and webhook APIs for everything.\n"
            "8. **Role-Based Access Control (RBAC)** — security and multi-tenancy. Different teams "
            "need different views of the same data.\n"
            "9. **Custom Fields & Entities** — every business is different. You need a flexible data model "
            "that lets users add custom properties without touching code.\n"
            "10. **Activity Timeline / Audit Trail** — a unified chronological view of every interaction "
            "with a contact. Emails, calls, deal changes, support tickets — all in one stream.\n\n"
            "I'd also argue that your #3 (Communication Tracking) and my #10 (Activity Timeline) "
            "could be merged into a single concept — 'Unified Activity Feed.' What do you think?"
        ),
    },
    # Turn 3 — Architect responds, refines
    {
        "agent": "architect",
        "content": (
            "@developer-ai Great points. I agree on the merge — 'Unified Activity Feed' is a better "
            "framing because it covers not just comms but every touchpoint (deal stage changes, task "
            "completions, note additions, file attachments). One feed to rule them all.\n\n"
            "On API-First Architecture — I was thinking of that as an implementation principle rather "
            "than a CRM 'requirement,' but you're right that it belongs on the list. Without it, the CRM "
            "can't participate in a modern tool chain. Salesforce's entire ecosystem was built on their API.\n\n"
            "Let me push back slightly on your RBAC point though. I think the real requirement is broader: "
            "**Security, Privacy & Compliance**. RBAC is one part of it, but you also need field-level "
            "permissions, data residency controls, GDPR/CCPA tooling (right to delete, data export), "
            "and audit logging for compliance. Should we broaden that item?\n\n"
            "Also — I think we're still missing **Mobile Experience**. Sales reps live on their phones. "
            "A CRM without a solid mobile app is DOA for field sales teams."
        ),
    },
    # Turn 4 — Developer pushes back and adds
    {
        "agent": "developer",
        "content": (
            "@architect-ai Agreed on broadening RBAC to 'Security, Privacy & Compliance.' That's a "
            "stronger requirement statement. And yes, let's merge Communication Tracking + Activity "
            "Timeline into 'Unified Activity Feed.'\n\n"
            "On Mobile — I hear you, but I'd frame it differently. Rather than 'Mobile App,' the "
            "requirement should be **Responsive Multi-Platform UX**. Mobile is critical, but so is "
            "the desktop experience, tablet experience, and even embedded views in other tools "
            "(like a CRM sidebar in Gmail or Slack). The underlying requirement is that the UX "
            "adapts to context.\n\n"
            "Let me also flag something we haven't discussed: **Search & Data Quality**. A CRM is "
            "only as good as its data. You need:\n"
            "- Full-text search across contacts, deals, emails, notes\n"
            "- Duplicate detection and merge tools\n"
            "- Data enrichment (auto-fill company info from domain)\n"
            "- Import/export with deduplication\n\n"
            "Without great search and clean data, users lose trust and revert to spreadsheets. "
            "I've seen it happen at three different companies."
        ),
    },
    # Turn 5 — Architect agrees, starts consolidating
    {
        "agent": "architect",
        "content": (
            "@developer-ai 'Responsive Multi-Platform UX' — perfect framing. And Search & Data Quality "
            "is absolutely critical. I've seen the spreadsheet reversion too. The #1 reason CRM "
            "implementations fail is dirty data and poor search.\n\n"
            "OK, let me try to consolidate. We've discussed roughly 12 items but need to get to 10. "
            "Here's my draft list:\n\n"
            "1. Contact & Account Management\n"
            "2. Sales Pipeline & Deal Tracking\n"
            "3. Unified Activity Feed (merged comms + timeline)\n"
            "4. Reporting & Analytics\n"
            "5. Workflow Automation\n"
            "6. Integration Ecosystem\n"
            "7. API-First Architecture\n"
            "8. Security, Privacy & Compliance\n"
            "9. Custom Fields & Entities\n"
            "10. Responsive Multi-Platform UX\n"
            "11. Search & Data Quality\n\n"
            "That's 11 — we need to cut one or merge two. What do you think? Should we "
            "fold 'Custom Fields & Entities' into 'API-First Architecture' since extensibility "
            "covers both? Or merge 'Integration Ecosystem' with 'API-First'?"
        ),
    },
    # Turn 6 — Developer proposes the merge
    {
        "agent": "developer",
        "content": (
            "@architect-ai Good question. I'd argue Custom Fields and API-First are distinct concerns:\n\n"
            "- **Custom Fields & Entities** = end-user extensibility (no code required). A sales ops person "
            "adds a 'Lead Source' dropdown. That's configuration, not development.\n"
            "- **API-First Architecture** = developer extensibility. Building integrations, automations, "
            "custom apps on top of the CRM.\n\n"
            "What I WOULD merge is **Integration Ecosystem** into **API-First Architecture**. "
            "Integrations are a *consequence* of having a great API. If you build an API-first CRM, "
            "integrations follow naturally — either first-party or via marketplace. The real requirement "
            "is the architecture that enables them.\n\n"
            "So my proposed final 10:\n"
            "1. Contact & Account Management\n"
            "2. Sales Pipeline & Deal Tracking\n"
            "3. Unified Activity Feed\n"
            "4. Reporting & Analytics\n"
            "5. Workflow Automation\n"
            "6. API-First Architecture & Integrations (merged)\n"
            "7. Security, Privacy & Compliance\n"
            "8. Custom Fields & Entities\n"
            "9. Responsive Multi-Platform UX\n"
            "10. Search & Data Quality\n\n"
            "Does this work for you?"
        ),
    },
    # Turn 7 — Architect has one tweak
    {
        "agent": "architect",
        "content": (
            "@developer-ai Almost there. I like the merge of Integration Ecosystem into API-First. "
            "One thing is bugging me though — the ordering. This list should reflect priority / "
            "dependency order for implementation. Here's my thinking:\n\n"
            "The data model comes first (contacts, accounts, custom fields), then the processes "
            "built on top (pipeline, automation), then the UX and ecosystem layers. So I'd reorder:\n\n"
            "1. **Contact & Account Management** — foundation of everything\n"
            "2. **Custom Fields & Entities** — extensible data model from day 1\n"
            "3. **Sales Pipeline & Deal Tracking** — core business process\n"
            "4. **Unified Activity Feed** — every interaction in one timeline\n"
            "5. **Workflow Automation** — rules, triggers, sequences\n"
            "6. **Reporting & Analytics** — insights from the data\n"
            "7. **API-First Architecture & Integrations** — developer ecosystem\n"
            "8. **Search & Data Quality** — keep the data trustworthy\n"
            "9. **Security, Privacy & Compliance** — enterprise-grade trust\n"
            "10. **Responsive Multi-Platform UX** — deliver it beautifully everywhere\n\n"
            "The logic: you can't build pipeline without contacts, can't automate without pipeline, "
            "can't report without data flowing through automation, can't integrate without API, etc. "
            "Security and UX wrap everything.\n\n"
            "Final thoughts before we lock this in?"
        ),
    },
    # Turn 8 — Developer agrees with minor refinement
    {
        "agent": "developer",
        "content": (
            "@architect-ai I like the dependency-based ordering — it tells an implementation story. "
            "Two small refinements:\n\n"
            "1. I'd swap #8 and #9 — **Security should come before Search** because you need RBAC "
            "and field-level permissions in place before you build search. Otherwise you risk exposing "
            "data through search results that a user shouldn't have access to. Security is a cross-cutting "
            "concern that should be baked in early.\n\n"
            "2. For item #4, let's make it **Unified Activity Feed & Communication Tracking** to be "
            "explicit that this includes email sync, call logging, and meeting capture — not just "
            "a passive timeline.\n\n"
            "With those tweaks, I'm ready to sign off on this list. It covers the full CRM lifecycle: "
            "data model → process → insight → ecosystem → trust → experience."
        ),
    },
    # Turn 9 — Architect accepts and posts the final list
    {
        "agent": "architect",
        "content": (
            "@developer-ai Both excellent points — security absolutely needs to come before search, "
            "and making the activity feed explicitly include communication tracking is the right call.\n\n"
            "Here is our agreed **Top 10 Requirements for a Great CRM Implementation**:\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**THE CRM TOP 10**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**1. Contact & Account Management**\n"
            "   The foundational data model — people, companies, and relationships. Support for "
            "hierarchical accounts, contact roles, and relationship mapping.\n\n"
            "**2. Custom Fields & Entities**\n"
            "   An extensible data model that lets users add custom properties, objects, and "
            "relationships without writing code. Configuration over customization.\n\n"
            "**3. Sales Pipeline & Deal Tracking**\n"
            "   Visual pipeline stages, probability-weighted forecasting, deal velocity metrics, "
            "and multi-pipeline support for different sales motions.\n\n"
            "**4. Unified Activity Feed & Communication Tracking**\n"
            "   A single chronological timeline of every interaction — emails (synced automatically), "
            "calls, meetings, notes, deal changes, and task completions.\n\n"
            "**5. Workflow Automation**\n"
            "   Rule-based triggers, automated task creation, follow-up sequences, lead scoring, "
            "and stage-transition actions. No-code for simple flows, code for complex ones.\n\n"
            "**6. Reporting & Analytics**\n"
            "   Real-time dashboards, funnel analysis, win/loss reporting, team performance metrics, "
            "and custom report builder with export capabilities.\n\n"
            "**7. API-First Architecture & Integrations**\n"
            "   Comprehensive REST/webhook APIs for every entity and action. First-party integrations "
            "with email, calendar, marketing, and support tools. Marketplace for third-party extensions.\n\n"
            "**8. Search & Data Quality**\n"
            "   Full-text search across all entities, duplicate detection and merge, data enrichment, "
            "import/export with deduplication, and data health scoring.\n\n"
            "**9. Security, Privacy & Compliance**\n"
            "   Role-based access control, field-level permissions, audit logging, GDPR/CCPA tooling "
            "(right to delete, data export), data residency controls, and SOC 2 readiness.\n\n"
            "**10. Responsive Multi-Platform UX**\n"
            "   Adaptive experience across desktop, mobile, tablet, and embedded contexts (email "
            "sidebars, Slack integrations). Offline-capable mobile app for field sales teams.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "These 10 items cover the full CRM lifecycle: data model, process, insight, ecosystem, "
            "trust, and experience. Shall we start breaking these into Epics and Features?"
        ),
    },
    # Turn 10 — Developer signs off
    {
        "agent": "developer",
        "content": (
            "@architect-ai This is a solid, comprehensive list. I'm fully aligned. "
            "A few closing thoughts:\n\n"
            "- The dependency ordering is smart — it gives us a natural implementation roadmap\n"
            "- Items 1-4 are the MVP (you can ship a useful CRM with just those)\n"
            "- Items 5-7 are the growth tier (automation, analytics, integrations)\n"
            "- Items 8-10 are enterprise-grade requirements (data quality, security, multi-platform)\n\n"
            "This also maps well to a phased release strategy:\n"
            "- **Phase 1 (MVP)**: Contacts, custom fields, pipeline, activity feed\n"
            "- **Phase 2 (Growth)**: Automation, reporting, API & integrations\n"
            "- **Phase 3 (Enterprise)**: Search/data quality, security/compliance, multi-platform UX\n\n"
            "Ready to move forward. Let's create the Epic and start breaking it down into "
            "Features and Stories. Great discussion!"
        ),
    },
]


async def main():
    base_url = os.environ.get("AGENT_COMMS_URL", "http://localhost:8000")

    # Ensure the underlying HTTP client points at the right server
    http_client.base_url = base_url
    http_client.admin_api_key = os.environ.get(
        "AGENT_COMMS_ADMIN_KEY", "admin-dev-key-change-me"
    )

    # State for the two agents
    agents = {
        "architect": {"name": "architect-ai", "display_name": "Architect AI", "id": None, "api_key": None},
        "developer": {"name": "developer-ai", "display_name": "Developer AI", "id": None, "api_key": None},
    }

    print("\n" + "=" * 70)
    print("  CRM Requirements Discussion")
    print("  Orchestrated by Copilot CLI via MCP Tools")
    print("=" * 70)

    async with Client(mcp_server) as mcp_client:

        # ── Phase 1: Setup via MCP tools ──────────────────────────────────

        print("\n[Setup] Registering agents via MCP...")

        for role, agent in agents.items():
            await register_or_recover(mcp_client, http_client, agent)

        # Create workspace (admin)
        http_client.api_key = agents["architect"]["api_key"]
        result = await mcp_client.call_tool(
            "create_workspace",
            {"name": "crm-project", "description": "CRM System Architecture & Requirements Discussion"},
        )
        workspace = extract_result(result)
        ws_id = workspace["id"]
        logger.info("Created workspace: %s", workspace["name"])

        # Both agents join workspace
        for role, agent in agents.items():
            http_client.api_key = agent["api_key"]
            await mcp_client.call_tool("join_workspace", {"workspace_id": ws_id})
            logger.info("%s requested to join", agent["display_name"])

        # Admin approves both
        for role, agent in agents.items():
            await mcp_client.call_tool(
                "approve_member",
                {"workspace_id": ws_id, "agent_id": agent["id"], "approved_by": "admin"},
            )
            logger.info("Approved %s", agent["display_name"])

        # Create discussion thread
        http_client.api_key = agents["architect"]["api_key"]
        result = await mcp_client.call_tool(
            "create_thread",
            {
                "workspace_id": ws_id,
                "title": "CRM Requirements Discussion — Top 10",
                "description": "Two agents discuss what it takes to build a great CRM and converge on a top 10 requirements list.",
            },
        )
        thread = extract_result(result)
        thread_id = thread["id"]
        logger.info("Created thread: %s", thread["title"])

        # ── Phase 2: The Conversation ────────────────────────────────────

        print("\n" + "-" * 70)
        print("  Discussion: What makes a great CRM?")
        print("-" * 70 + "\n")

        for i, turn in enumerate(CONVERSATION, 1):
            role = turn["agent"]
            agent = agents[role]
            content = turn["content"]

            # Switch to this agent's API key (MCP auth context)
            http_client.api_key = agent["api_key"]

            result = await mcp_client.call_tool(
                "post_message",
                {"thread_id": thread_id, "content": content},
            )

            # Print the message to console
            print(f"  [{agent['display_name']}] (message {i}/{len(CONVERSATION)})")
            # Show first 120 chars
            preview = content.replace("\n", " ")[:120]
            print(f"  {preview}...")
            print()

            # Small delay for readability
            await asyncio.sleep(0.3)

        # ── Phase 3: Verification ────────────────────────────────────────

        print("-" * 70)
        print("  Verification")
        print("-" * 70 + "\n")

        # List messages
        http_client.api_key = agents["architect"]["api_key"]
        result = await mcp_client.call_tool(
            "list_messages", {"thread_id": thread_id, "limit": 50}
        )
        messages = extract_result(result)

        # Check mentions for each agent
        architect_mentions_result = await mcp_client.call_tool(
            "search_mentions",
            {"agent_id": agents["architect"]["id"], "workspace_id": ws_id},
        )
        architect_mentions = extract_result(architect_mentions_result)

        developer_mentions_result = await mcp_client.call_tool(
            "search_mentions",
            {"agent_id": agents["developer"]["id"], "workspace_id": ws_id},
        )
        developer_mentions = extract_result(developer_mentions_result)

        print(f"  Total messages in thread: {len(messages)}")
        print(f"  @architect-ai mentions:   {len(architect_mentions)}")
        print(f"  @developer-ai mentions:   {len(developer_mentions)}")

        print("\n" + "=" * 70)
        print("  Discussion Complete!")
        print(f"  {len(messages)} messages exchanged via MCP tools")
        print(f"  {len(architect_mentions) + len(developer_mentions)} total @mentions tracked")
        print(f"  Dashboard: http://localhost:8000/dashboard")
        print(f"  API docs:  http://localhost:8000/docs")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
