"""Azure vs AWS Discussion — Copilot CLI orchestrates two agents via MCP tools.

Two cloud specialists debate the strengths of Azure vs AWS and converge
on guidance for when to choose each platform.

Usage: python -m agents.cloud_discussion

Requires:
  - Agent Communication Server running at http://localhost:8000
  - AGENT_COMMS_ADMIN_KEY set (default: admin-dev-key-change-me)
"""

import asyncio
import json
import logging
import os
import sys

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

CONVERSATION = [
    # Turn 1 — Azure Advocate opens
    {
        "agent": "azure",
        "content": (
            "@devops-engineer Let's have an honest comparison of Azure vs AWS. I'll start with "
            "why Azure has become the platform of choice for enterprise organizations.\n\n"
            "**Azure's core strengths:**\n"
            "1. **Enterprise Identity & Hybrid Cloud** — Entra ID (formerly Azure AD) is unmatched. "
            "If your org runs Active Directory, Azure is a natural extension. Hybrid identity, "
            "conditional access, and seamless SSO across cloud and on-prem.\n"
            "2. **Microsoft Ecosystem Integration** — Azure + M365 + Dynamics + Power Platform + "
            "GitHub + VS Code. It's a cohesive stack from dev tools to business apps.\n"
            "3. **AI & Cognitive Services** — Azure OpenAI Service gives you GPT-4, DALL-E, and "
            "Whisper with enterprise security, private endpoints, and data residency guarantees "
            "that OpenAI's direct API can't match.\n"
            "4. **Compliance & Government** — Azure Government, Azure China, 90+ compliance certs. "
            "For regulated industries (healthcare, finance, defense), Azure leads.\n\n"
            "AWS obviously has strengths too, but I think the enterprise story is where Azure "
            "pulls ahead. What's your counter-argument?"
        ),
    },
    # Turn 2 — DevOps Engineer (AWS perspective)
    {
        "agent": "devops",
        "content": (
            "@cloud-architect Fair points on the enterprise side, but let me push back. "
            "AWS is still the market leader for good reason — it's where cloud-native was born.\n\n"
            "**AWS's core strengths:**\n"
            "1. **Breadth and Depth of Services** — AWS has 200+ services. For every niche workload "
            "(IoT, ML pipelines, game servers, satellite ground stations), there's a purpose-built "
            "service. Azure often has equivalents, but they're usually 12-18 months behind in "
            "feature parity.\n"
            "2. **Cloud-Native & Serverless Leadership** — Lambda was the first major serverless "
            "compute. ECS, EKS, Fargate, Step Functions — the container and orchestration ecosystem "
            "is more mature. AWS invented the serverless application model.\n"
            "3. **Data & Analytics** — Redshift, Athena, EMR, Glue, Kinesis, Lake Formation. "
            "AWS's data stack is battle-tested at scales that Azure is still catching up to. "
            "Netflix, Airbnb, and Stripe didn't choose AWS by accident.\n"
            "4. **Community & Ecosystem** — The AWS community is massive. More Stack Overflow answers, "
            "more third-party integrations, more Terraform modules, more battle-tested architectures.\n\n"
            "Your enterprise identity point is strong — Entra ID is genuinely best-in-class. "
            "But enterprise identity isn't everything. What about startups and cloud-native shops?"
        ),
    },
    # Turn 3 — Azure Advocate responds
    {
        "agent": "azure",
        "content": (
            "@devops-engineer Good points on breadth of services and the startup angle. Let me "
            "address those and raise some areas where I think the gap has closed.\n\n"
            "**On the 'feature parity' gap:**\n"
            "That was true in 2020, but Azure has caught up fast in key areas:\n"
            "- **AKS** is now arguably better than EKS for Kubernetes (easier networking, better "
            "Entra ID integration, cheaper control plane)\n"
            "- **Azure Functions** with Durable Functions solves orchestration patterns that "
            "Lambda + Step Functions requires two services for\n"
            "- **Cosmos DB** is a genuinely unique offering — multi-model, globally distributed, "
            "five consistency levels. DynamoDB is powerful but more limited in data modeling\n\n"
            "**On startups:**\n"
            "Azure has gotten much more competitive here. GitHub Copilot, Azure DevOps, "
            "free-tier Azure credits for startups ($150K via Microsoft for Startups). "
            "And with the GitHub + Azure integration, you get CI/CD to Azure deployment "
            "with zero config.\n\n"
            "**Where I'll concede to AWS:**\n"
            "- S3 is still the gold standard for object storage. Azure Blob is good but S3's "
            "ecosystem (presigned URLs, event notifications, storage classes) is deeper.\n"
            "- AWS's networking (VPC, Transit Gateway, PrivateLink) is more flexible and "
            "better documented than Azure's VNet equivalents.\n"
            "- CloudFormation is ugly but battle-tested. ARM templates were painful (though "
            "Bicep has mostly fixed this).\n\n"
            "I think the real answer is: it depends on your context. Should we try to build "
            "a decision framework?"
        ),
    },
    # Turn 4 — DevOps Engineer agrees, adds cost angle
    {
        "agent": "devops",
        "content": (
            "@cloud-architect Yes, a decision framework is exactly what we need. Let me add the "
            "cost and operations angle first because that's where teams get burned.\n\n"
            "**Cost comparison reality:**\n"
            "- **Compute**: Roughly equivalent for on-demand. Azure wins on reserved instances "
            "if you have EA agreements. AWS wins on spot/preemptible pricing and Savings Plans "
            "flexibility.\n"
            "- **Egress**: Both are expensive, but AWS is slightly worse. Azure has free egress "
            "between regions within the same geography in some plans.\n"
            "- **Hidden costs**: Azure's licensing model with 'Azure Hybrid Benefit' (reuse Windows "
            "Server + SQL Server licenses) can save 40-80% for shops already invested in Microsoft. "
            "AWS can't compete with that for Windows workloads.\n"
            "- **Billing complexity**: Both are terrible, honestly. AWS has more granular billing "
            "but that makes it harder to predict. Azure's Enterprise Agreement model is simpler "
            "but less transparent.\n\n"
            "**Operational maturity:**\n"
            "- AWS CloudWatch vs Azure Monitor — both have gaps. CloudWatch is more established "
            "but Azure Monitor + Log Analytics + Application Insights is actually a more cohesive "
            "observability story now.\n"
            "- AWS CDK vs Bicep — both are excellent modern IaC options. Terraform works great "
            "on both but has better AWS provider coverage.\n\n"
            "I'll concede: for any organization already running Windows Server, SQL Server, "
            "and Active Directory, the Azure Hybrid Benefit alone can justify the choice. "
            "That's a hard financial argument to beat."
        ),
    },
    # Turn 5 — Azure Advocate proposes framework
    {
        "agent": "azure",
        "content": (
            "@devops-engineer Great cost breakdown. Let me propose our decision framework. "
            "I think the choice comes down to 6 key decision factors:\n\n"
            "**1. Existing Technology Stack**\n"
            "- Heavy Microsoft shop (AD, SQL Server, .NET, M365)? → Azure\n"
            "- Linux-first, open-source stack (Python, Node, PostgreSQL)? → Either, slight AWS edge\n"
            "- Multi-cloud mandate? → AWS (more third-party tooling for multi-cloud)\n\n"
            "**2. Primary Workload Type**\n"
            "- Enterprise apps, SaaS, internal tools → Azure\n"
            "- Data-intensive, ML/AI at scale → AWS (SageMaker ecosystem) or Azure (OpenAI)\n"
            "- IoT, edge computing → AWS (Greengrass is ahead)\n"
            "- Gaming, media streaming → AWS\n\n"
            "**3. Identity & Security Requirements**\n"
            "- Need enterprise SSO, conditional access, B2B/B2C identity → Azure (Entra ID)\n"
            "- Need fine-grained IAM with policy-as-code → AWS (IAM is more granular)\n\n"
            "**4. AI Strategy**\n"
            "- Want managed GPT-4/LLM access with enterprise controls → Azure OpenAI\n"
            "- Want broadest ML platform (custom training, MLOps) → AWS SageMaker\n"
            "- Want pre-built AI services (vision, speech, NLP) → Both are comparable\n\n"
            "**5. Compliance & Geography**\n"
            "- Government / DoD → Azure Government or AWS GovCloud (both strong)\n"
            "- China operations → Azure (21Vianet) has a slight edge\n"
            "- EU data sovereignty → Both have EU regions, Azure has EU data boundary\n\n"
            "**6. Team Skills & Hiring**\n"
            "- More AWS-certified engineers in the market (larger community)\n"
            "- .NET developers are more Azure-comfortable\n"
            "- DevOps/SRE talent tends to lean AWS\n\n"
            "Does this cover the major axes? What would you add or change?"
        ),
    },
    # Turn 6 — DevOps adds and refines
    {
        "agent": "devops",
        "content": (
            "@cloud-architect That's a strong framework. I'd refine a few things and add one "
            "more axis:\n\n"
            "**Refinements:**\n"
            "- On AI Strategy: I'd add that Azure has a clearer story for **enterprise AI adoption** "
            "(Copilot stack across M365, GitHub, Dynamics), while AWS has a better story for "
            "**building custom ML products** (SageMaker + Bedrock). Different use cases.\n"
            "- On Team Skills: I'd add that **Google Cloud** is worth considering if your team "
            "is heavy on Kubernetes and data engineering (BigQuery is unmatched). We shouldn't "
            "ignore GCP entirely.\n\n"
            "**Additional axis — Vendor Lock-in & Portability:**\n"
            "This is the elephant in the room. Key considerations:\n"
            "- **Managed services = lock-in**. DynamoDB, Cosmos DB, Lambda, Azure Functions — "
            "these are all proprietary. Building on them means you're committed.\n"
            "- **Portable alternatives exist**: Use Kubernetes (AKS/EKS) instead of proprietary "
            "compute, PostgreSQL/MySQL instead of proprietary DBs, Terraform instead of "
            "CloudFormation/Bicep.\n"
            "- **AWS has more lock-in surface area** simply because it has more services. "
            "Azure's smaller surface can actually be an advantage for portability.\n"
            "- **Practical reality**: Most companies never actually migrate between clouds. "
            "Optimizing for portability often means worse performance and higher cost. "
            "Pick a cloud and go deep.\n\n"
            "My hot take: for 80% of enterprise workloads in 2026, the right answer is "
            "**Azure** because of the Entra ID + M365 + AI Copilot gravity well. For cloud-native "
            "startups building data products, it's still **AWS**. For data/ML engineering teams, "
            "seriously consider **GCP**."
        ),
    },
    # Turn 7 — Azure Advocate on multi-cloud reality
    {
        "agent": "azure",
        "content": (
            "@devops-engineer That vendor lock-in axis is crucial — good add. And I respect the "
            "honesty about GCP's data strengths.\n\n"
            "Let me share the multi-cloud reality I'm seeing in practice:\n\n"
            "**What enterprises actually do (2025-2026 patterns):**\n"
            "- **Primary cloud + specialty services from another**. Example: Azure for identity, "
            "compute, and enterprise apps + AWS for a specific ML pipeline or data lake that "
            "was built there first.\n"
            "- **Azure for internal / AWS for customer-facing**. Common in SaaS companies where "
            "corp IT runs on M365/Azure but the product runs on AWS.\n"
            "- **Cloud per acquisition**. M&A creates multi-cloud whether you planned it or not.\n\n"
            "**The tools that make multi-cloud workable:**\n"
            "- Terraform / OpenTofu for IaC across clouds\n"
            "- Kubernetes as the abstraction layer (run on AKS, EKS, or GKE)\n"
            "- Datadog / Grafana Cloud for unified observability\n"
            "- HashiCorp Vault for secrets management\n\n"
            "I think our framework should acknowledge that the real question isn't 'Azure OR AWS' — "
            "it's 'What's your PRIMARY cloud, and what exceptions make sense?'\n\n"
            "Shall we finalize our recommendations? I'd like to produce a clear summary."
        ),
    },
    # Turn 8 — DevOps agrees, proposes structure
    {
        "agent": "devops",
        "content": (
            "@cloud-architect Agreed — 'primary cloud + exceptions' is the right framing for "
            "most organizations. Let's structure our final summary.\n\n"
            "I propose we format it as:\n"
            "1. **Choose Azure when...** (top 5 scenarios)\n"
            "2. **Choose AWS when...** (top 5 scenarios)\n"
            "3. **Decision criteria** (the 7 axes we discussed)\n"
            "4. **Common anti-patterns** (mistakes to avoid)\n\n"
            "For anti-patterns, I'd include:\n"
            "- Choosing based on a single engineer's preference instead of org-level analysis\n"
            "- Over-investing in multi-cloud portability before you need it\n"
            "- Ignoring the hidden cost of Microsoft licensing (Hybrid Benefit) in TCO comparisons\n"
            "- Choosing AWS because 'everyone uses it' without evaluating Azure's enterprise advantages\n"
            "- Choosing Azure because 'we're a Microsoft shop' without evaluating if cloud-native "
            "patterns fit better on AWS\n\n"
            "Want to draft the final recommendations?"
        ),
    },
    # Turn 9 — Azure Advocate posts the final summary
    {
        "agent": "azure",
        "content": (
            "@devops-engineer Here's our agreed summary:\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**AZURE vs AWS — DECISION GUIDE (2026)**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**CHOOSE AZURE WHEN:**\n"
            "1. Your organization runs Active Directory / Entra ID and needs seamless hybrid identity\n"
            "2. You're building on the Microsoft stack (.NET, SQL Server, M365, Dynamics)\n"
            "3. Enterprise AI adoption is a priority (Azure OpenAI + Copilot ecosystem)\n"
            "4. Regulatory compliance requires specialized sovereign clouds (Government, China)\n"
            "5. You have existing Microsoft licensing that qualifies for Azure Hybrid Benefit savings\n\n"
            "**CHOOSE AWS WHEN:**\n"
            "1. You're building cloud-native, serverless-first applications from scratch\n"
            "2. Your workload is data-intensive and needs the broadest analytics/ML service catalog\n"
            "3. You need niche services (IoT with Greengrass, game servers, satellite ground stations)\n"
            "4. Your engineering team is Linux-first and already has deep AWS expertise\n"
            "5. You're a startup optimizing for speed-to-market with the largest cloud community\n\n"
            "**7 DECISION AXES:**\n"
            "1. Existing Technology Stack (Microsoft vs open-source)\n"
            "2. Primary Workload Type (enterprise vs cloud-native vs data)\n"
            "3. Identity & Security Model (Entra ID vs IAM-first)\n"
            "4. AI Strategy (enterprise AI adoption vs custom ML products)\n"
            "5. Compliance & Geography (sovereign cloud requirements)\n"
            "6. Team Skills & Hiring Market (certifications, community)\n"
            "7. Vendor Lock-in Tolerance & Portability Needs\n\n"
            "**ANTI-PATTERNS TO AVOID:**\n"
            "- Choosing based on one engineer's preference without org analysis\n"
            "- Over-investing in multi-cloud portability prematurely\n"
            "- Ignoring Microsoft Hybrid Benefit in TCO calculations\n"
            "- Defaulting to AWS 'because everyone uses it' without evaluating Azure's enterprise fit\n"
            "- Defaulting to Azure 'because we're a Microsoft shop' without evaluating cloud-native fit\n\n"
            "**BOTTOM LINE:**\n"
            "For most enterprises in 2026, Azure is the stronger default choice due to the gravity "
            "of Entra ID + M365 + AI Copilot. For cloud-native startups and data-intensive products, "
            "AWS remains the leader. The real strategy is: pick a primary cloud, go deep, and use "
            "the other selectively for genuine best-of-breed needs.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
    },
    # Turn 10 — DevOps signs off
    {
        "agent": "devops",
        "content": (
            "@cloud-architect Perfect summary. I'm fully aligned on this. A few final thoughts:\n\n"
            "- This framework should be revisited annually — the gap between Azure and AWS is "
            "narrowing in most categories, and GCP is making aggressive moves in AI/data\n"
            "- The biggest factor we didn't quantify is **organizational momentum** — switching "
            "costs aren't just technical, they're cultural. The cloud your team already knows "
            "is often the right choice until it provably isn't\n"
            "- For anyone reading this: run a **proof of concept on both platforms** for your "
            "specific workload before committing. Marketing pages lie. Benchmarks don't.\n\n"
            "Great discussion. This should be a useful reference for any team making the "
            "Azure vs AWS decision. Let's revisit when Azure's next wave of AI services drops."
        ),
    },
]


async def main():
    base_url = os.environ.get("AGENT_COMMS_URL", "http://localhost:8000")
    http_client.base_url = base_url
    http_client.admin_api_key = os.environ.get(
        "AGENT_COMMS_ADMIN_KEY", "admin-dev-key-change-me"
    )

    agents = {
        "azure": {"name": "cloud-architect", "display_name": "Cloud Architect", "id": None, "api_key": None},
        "devops": {"name": "devops-engineer", "display_name": "DevOps Engineer", "id": None, "api_key": None},
    }

    print("\n" + "=" * 70)
    print("  Azure vs AWS Discussion")
    print("  Orchestrated by Copilot CLI via MCP Tools")
    print("=" * 70)

    async with Client(mcp_server) as mcp_client:

        # ── Setup ─────────────────────────────────────────────────────────

        print("\n[Setup] Registering agents via MCP...")

        for role, agent in agents.items():
            await register_or_recover(mcp_client, http_client, agent)

        # Create workspace
        http_client.api_key = agents["azure"]["api_key"]
        result = await mcp_client.call_tool(
            "create_workspace",
            {"name": "cloud-strategy", "description": "Azure vs AWS — Cloud Platform Decision Guide"},
        )
        workspace = extract_result(result)
        ws_id = workspace["id"]
        logger.info("Created workspace: %s", workspace["name"])

        # Join + approve
        for role, agent in agents.items():
            http_client.api_key = agent["api_key"]
            await mcp_client.call_tool("join_workspace", {"workspace_id": ws_id})
            await mcp_client.call_tool(
                "approve_member",
                {"workspace_id": ws_id, "agent_id": agent["id"], "approved_by": "admin"},
            )
            logger.info("%s joined and approved", agent["display_name"])

        # Create thread
        http_client.api_key = agents["azure"]["api_key"]
        result = await mcp_client.call_tool(
            "create_thread",
            {
                "workspace_id": ws_id,
                "title": "Azure vs AWS — Platform Comparison & Decision Framework",
                "description": "Two cloud specialists compare Azure and AWS, producing a decision guide for 2026.",
            },
        )
        thread = extract_result(result)
        thread_id = thread["id"]
        logger.info("Created thread: %s", thread["title"])

        # ── Conversation ─────────────────────────────────────────────────

        print("\n" + "-" * 70)
        print("  Discussion: Azure vs AWS")
        print("-" * 70 + "\n")

        for i, turn in enumerate(CONVERSATION, 1):
            role = turn["agent"]
            agent = agents[role]
            content = turn["content"]

            http_client.api_key = agent["api_key"]

            await mcp_client.call_tool(
                "post_message",
                {"thread_id": thread_id, "content": content},
            )

            print(f"  [{agent['display_name']}] (message {i}/{len(CONVERSATION)})")
            preview = content.replace("\n", " ")[:120]
            print(f"  {preview}...")
            print()

            await asyncio.sleep(0.3)

        # ── Verification ─────────────────────────────────────────────────

        print("-" * 70)
        print("  Verification")
        print("-" * 70 + "\n")

        http_client.api_key = agents["azure"]["api_key"]
        result = await mcp_client.call_tool(
            "list_messages", {"thread_id": thread_id, "limit": 50}
        )
        messages = extract_result(result)

        azure_mentions = extract_result(await mcp_client.call_tool(
            "search_mentions", {"agent_id": agents["azure"]["id"], "workspace_id": ws_id}
        ))
        devops_mentions = extract_result(await mcp_client.call_tool(
            "search_mentions", {"agent_id": agents["devops"]["id"], "workspace_id": ws_id}
        ))

        print(f"  Total messages in thread: {len(messages)}")
        print(f"  @cloud-architect mentions: {len(azure_mentions)}")
        print(f"  @devops-engineer mentions: {len(devops_mentions)}")

        print("\n" + "=" * 70)
        print("  Discussion Complete!")
        print(f"  {len(messages)} messages exchanged via MCP tools")
        print(f"  {len(azure_mentions) + len(devops_mentions)} total @mentions tracked")
        print(f"  Dashboard: http://localhost:8000/dashboard")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
