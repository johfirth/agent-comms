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

| File | Agent Type | Role |
|------|-----------|------|
| `cto.agent.md` | `cto` | Strategic tech decisions, architecture |
| `product-manager.agent.md` | `product-manager` | Requirements, scope, prioritisation |
| `developer.agent.md` | `developer` | Implementation, estimation, coding |
| `michael-scott.agent.md` | `michael-scott` | Regional Manager |
| `dwight-schrute.agent.md` | `dwight-schrute` | Assistant (to the) Regional Manager |
| `jim-halpert.agent.md` | `jim-halpert` | Witty sales rep |
| `pam-beesly.agent.md` | `pam-beesly` | Creative receptionist |
| `angela-martin.agent.md` | `angela-martin` | Strict accounting |
| `oscar-martinez.agent.md` | `oscar-martinez` | Rational accountant |
| `stanley-hudson.agent.md` | `stanley-hudson` | Does not care |
| `phyllis-vance.agent.md` | `phyllis-vance` | Sweet surface, sassy underneath |
| `darryl-philbin.agent.md` | `darryl-philbin` | Practical wisdom |
| `creed-bratton.agent.md` | `creed-bratton` | Mysterious QA |
| `stefan.agent.md` | `stefan` | New QA hire |
| `coffee-shop-owner.agent.md` | `coffee-shop-owner` | Non-technical customer persona |

To add a new persona, create a `.agent.md` file in `.github/agents/` following the existing format.