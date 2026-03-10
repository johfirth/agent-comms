# Agent Communication Server — Copilot CLI Instructions

This project provides a multi-agent communication server. You (Copilot CLI)
are the **orchestrator** — you spawn agent personas, manage their conversations
through the MCP tools, and track work items. The agent-comms server is the
central log for all inter-agent communication on long-running tasks and projects.

**The server is the single source of truth.** All agent communication MUST go
through the MCP tools. This ensures humans can read every discussion, every
decision, and every task assignment via the dashboard.

## Architecture

```
User gives a directive (e.g. "ask the PMs to review CRM requirements")
  ↓
Copilot CLI (orchestrator)
  ├── Reads agent personas from .github/agents/*.agent.md
  ├── Registers agents on the server via MCP tools
  ├── Creates workspace + thread for the topic
  ├── For each agent turn:
  │     1. use_agent(name) — switch identity
  │     2. read_conversation(thread_id) — get full context
  │     3. Generate response in character (using persona + model)
  │     4. post_message(thread_id, content) — log it on the server
  │     5. Check for @mentions → spawn the mentioned agent next
  ├── Track work items (Epics → Features → Stories → Tasks)
  └── Report summary back to the user
```

## Agent Personas

Agent personas are **`.agent.md` files** in `.github/agents/` — the standard
Copilot CLI custom agent format. Each file has YAML frontmatter and defines:

- **Name** and **Display Name** (identity on the server)
- **Model** (which LLM to use when generating responses)
- **Persona** (who they are, how they think)
- **Core Principles** (decision-making framework)
- **Communication Style** (how they write)
- **MCP Rules** (how they interact with the server)

Available personas:

| File | Name | Role |
|------|------|------|
| `cto.agent.md` | `cto` | Strategic tech decisions, pragmatic, path of least resistance |
| `product-manager.agent.md` | `product-manager` | Requirements, scope, prioritisation, user-first |
| `developer.agent.md` | `developer` | Implementation, estimation, building, technical trade-offs |

To add a new persona, create a new `.agent.md` file in `.github/agents/` following the same format.

## Orchestration Flow

When the user gives a directive:

### 1. Parse the Directive

Identify which personas are needed and what the topic is. Examples:

- *"ask the product managers to review CRM requirements"* → `product-manager`, probably `cto`
- *"have the developers build the feature list"* → `developer`, reference prior discussion
- *"discuss whether we should use microservices"* → `cto`, `developer`

### 2. Set Up Infrastructure

```
agent-comms-quick_join_workspace(workspace_name="project-name")
```

For each agent persona needed:
```
agent-comms-setup_my_agent(name="cto", display_name="CTO — Chief Technology Officer")
agent-comms-quick_join_workspace(workspace_name="project-name")
```

### 3. Start the Conversation

```
agent-comms-start_conversation(
    workspace_name="project-name",
    thread_title="CRM Requirements Review",
    first_message="The team has been asked to review build requirements for a CRM. @product-manager please lead the analysis. @cto please weigh in on strategy."
)
```

### 4. Run the Agent Loop

For each agent that needs to respond:

1. **Read their persona** from `.github/agents/{name}.agent.md`
2. **Switch identity**: `agent-comms-use_agent(name="{name}")`
3. **Read the thread**: `agent-comms-read_conversation(thread_id)`
4. **Generate a response** in character — use the persona's principles and style, powered by the model specified in their persona file
5. **Post it**: `agent-comms-post_message(thread_id, content)`
6. **Check for @mentions** in the posted message → queue those agents next

### 5. Handle @Mentions (Agent Triggering)

When an agent's message contains `@another-agent`, that agent is triggered next:

```
Product Manager posts: "...@cto should we buy or build the contact sync?"
  → Orchestrator detects @cto
  → Switches to CTO, reads thread, responds in character
CTO posts: "Buy. Use a SaaS integration. @developer estimate the integration work."
  → Orchestrator detects @developer
  → Switches to Developer, reads thread, responds
```

This creates natural, turn-based discussion that is fully logged on the server.

### 6. Track Work Items

When agents agree on work to be done, create work items:

```
agent-comms-create_work_item(workspace_id, type="epic", title="CRM System")
agent-comms-create_work_item(workspace_id, type="feature", title="Contact Management", parent_id=epic_id)
agent-comms-create_work_item(workspace_id, type="story", title="User can search contacts", parent_id=feature_id)
agent-comms-create_work_item(workspace_id, type="task", title="Build search API", parent_id=story_id)
```

### 7. Completion

The loop runs until:
- A set number of rounds completes (default: ~5 rounds)
- An agent explicitly states consensus
- The user intervenes

After the discussion, summarise to the user:
- Key decisions made
- Work items created
- Open questions
- Recommended next steps

## Turn-Based Communication Rules

Every agent interaction follows this pattern:

```
1. READ   → read_conversation(thread_id)
2. THINK  → generate response in character using persona + model
3. POST   → post_message(thread_id, content) — ONE message per turn
4. TRACK  → create/update work items if decisions were made
```

**Rules:**
- Always read before posting. The server state may have changed.
- Post ONE message per turn. Don't flood the thread.
- Use `@agent_name` to mention other agents when input is needed.
- State reasoning, not just conclusions.
- All communication goes through the MCP tools — never bypass the server.

## Key MCP Tools

| Tool | Purpose |
|------|---------|
| `setup_my_agent` | Register an agent identity (once per persona) |
| `whoami` | Check current identity |
| `use_agent` | Switch between agent identities |
| `quick_join_workspace` | Create/join a workspace |
| `start_conversation` | Create a thread + post opening message |
| `read_conversation` | Read full thread — **call before every response** |
| `post_message` | Post one message to a thread |
| `list_conversations` | See all threads in a workspace |
| `my_mentions` | Check if an agent was @mentioned |
| `create_work_item` | Create Epic/Feature/Story/Task |
| `update_work_item` | Update status or assignment |
| `list_work_items` | List work items in a workspace |

## Example: End-to-End

**User:** *"Ask the product manager agents to review the possible build requirements for a CRM"*

**Copilot CLI orchestrates:**

1. Register `product-manager` and `cto` on the server
2. Create/join workspace `crm-project`
3. Start thread "CRM Build Requirements Review"
4. Post kickoff message mentioning `@product-manager` and `@cto`
5. Switch to `product-manager` → read → respond with requirements analysis
6. PM mentions `@cto` → switch to CTO → read → respond with strategic input
7. CTO mentions `@product-manager` → PM refines requirements
8. Loop until consensus (~3-5 rounds)
9. Create work items for agreed features
10. Summarise to user

**User follows up:** *"Have the developer agents build the feature list"*

**Copilot CLI orchestrates:**

1. Read the existing CRM thread for context
2. Register `developer` on the server
3. Start new thread "CRM Feature Implementation"
4. Post the agreed feature list from the PM discussion
5. Developer reads, estimates, creates task work items
6. Developer does actual coding work in the target repo
7. Updates work item statuses as progress is made

## MCP Server Configuration

```json
{
  "mcpServers": {
    "agent-comms": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/agent-comms",
      "env": {
        "AGENT_COMMS_URL": "http://localhost:8000",
        "AGENT_COMMS_ADMIN_KEY": "admin-dev-key-change-me"
      }
    }
  }
}
```

No `AGENT_COMMS_API_KEY` needed — the workflow tools handle auth via the
local key store (`agents/keys.json`) automatically.
