# Agent Communication Server — Copilot Instructions

> **Canonical instructions live at [.github/copilot-instructions.md](.github/copilot-instructions.md).**
> GitHub Copilot automatically reads that file. This file exists for discoverability.

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for:

- Strict sub-agent delegation rules
- Orchestration flow
- MCP tool reference
- Sub-agent prompt template
- Available agent personas

## Agent Personas

Agent personas are `.agent.md` files in `.github/agents/`. Each defines a
name, display name, persona, core principles, and communication style.

> **This table is auto-generated.** Run `python sync_agents.py --write` to
> regenerate it after adding or removing agent files.

<!-- BEGIN AGENT TABLE -->

| File | Agent Type | Role |
|------|-----------|------|
| `angela-martin.agent.md` | `angela-martin` | Angela Martin — Head of the Accounting Department at Dunder Mifflin. Strict, ... |
| `coffee-shop-owner.agent.md` | `coffee-shop-owner` | A small business customer persona — a coffee shop owner who needs a CRM but isn |
| `creed-bratton.agent.md` | `creed-bratton` | Creed Bratton — Quality Assurance at Dunder Mifflin. Mysterious, possibly cri... |
| `cto.agent.md` | `cto` | A pragmatic CTO agent that makes strategic technology decisions. Always favou... |
| `darryl-philbin.agent.md` | `darryl-philbin` | Darryl Philbin — Warehouse Manager (later VP of Sales) at Dunder Mifflin. Pra... |
| `developer.agent.md` | `developer` | A senior full-stack developer agent that implements features, estimates work,... |
| `dwight-schrute.agent.md` | `dwight-schrute` | Dwight K. Schrute — Assistant (to the) Regional Manager at Dunder Mifflin. Be... |
| `jim-halpert.agent.md` | `jim-halpert` | Jim Halpert — Sales rep at Dunder Mifflin. Witty, sarcastic, laid-back. The o... |
| `legal-customer.agent.md` | `legal-customer` | A legal operations customer persona — a Director of Legal Operations at a mid... |
| `michael-scott.agent.md` | `michael-scott` | Michael Scott — Regional Manager of Dunder Mifflin Scranton. Desperate to be ... |
| `oscar-martinez.agent.md` | `oscar-martinez` | Oscar Martinez — Accountant at Dunder Mifflin. The smartest person in the roo... |
| `pam-beesly.agent.md` | `pam-beesly` | Pam Beesly — Receptionist and aspiring artist at Dunder Mifflin. Quiet, creat... |
| `phyllis-vance.agent.md` | `phyllis-vance` | Phyllis Vance (née Lapin) — Sales rep at Dunder Mifflin. Sweet and motherly o... |
| `pm-ai-driven.agent.md` | `pm-ai-driven` | An AI-Driven Product Manager who identifies opportunities to apply AI and aut... |
| `pm-architect.agent.md` | `pm-architect` | An Architect-minded Product Manager who thinks in systems, data models, and s... |
| `pm-aspirational.agent.md` | `pm-aspirational` | An Aspirational Goals Product Manager who thinks big, dreams boldly, and push... |
| `pm-curmudgeon.agent.md` | `pm-curmudgeon` | A skeptical, battle-scarred Product Manager who has seen every hype cycle and... |
| `pm-customer-obsessed.agent.md` | `pm-customer-obsessed` | A Customer-Obsessed Product Manager who never lets the team forget who they |
| `product-manager.agent.md` | `product-manager` | A senior Product Manager agent that defines requirements, prioritises scope, ... |
| `stanley-hudson.agent.md` | `stanley-hudson` | Stanley Hudson — Sales rep at Dunder Mifflin. Does not care. Waiting for reti... |
| `stefan.agent.md` | `stefan` | Stefan — New Quality Assurance hire at Dunder Mifflin. Sits across from Creed... |

<!-- END AGENT TABLE -->

To add a new persona:
1. Create a `.agent.md` file in `.github/agents/` following the existing format
2. Run `python sync_agents.py --write` to update this table and `.github/copilot-instructions.md`
3. Restart the Copilot CLI session for the new agent to be available