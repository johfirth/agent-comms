#!/usr/bin/env python3
"""Sync agent registry from .agent.md files → copilot-instructions.md + AGENTS.md.

Scans .github/agents/*.agent.md, parses YAML frontmatter, and regenerates
the agent persona tables in both documentation files. This ensures the
`task` tool's available agent_types always match the actual .agent.md files.

Usage:
    python sync_agents.py          # Preview changes (dry run)
    python sync_agents.py --write  # Apply changes to files
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
AGENTS_DIR = REPO_ROOT / ".github" / "agents"
INSTRUCTIONS_FILE = REPO_ROOT / ".github" / "copilot-instructions.md"
AGENTS_MD_FILE = REPO_ROOT / "AGENTS.md"

# Markers that delimit the auto-generated table sections
INSTRUCTIONS_START = "<!-- BEGIN AGENT REGISTRY -->"
INSTRUCTIONS_END = "<!-- END AGENT REGISTRY -->"
AGENTS_MD_START = "<!-- BEGIN AGENT TABLE -->"
AGENTS_MD_END = "<!-- END AGENT TABLE -->"


def parse_agent_file(path: Path) -> dict | None:
    """Extract name and description from .agent.md YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    # Match YAML frontmatter between --- delimiters
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        print(f"  ⚠  Skipping {path.name}: no YAML frontmatter found")
        return None

    frontmatter = match.group(1)

    name_match = re.search(r'^name:\s*(.+)$', frontmatter, re.MULTILINE)
    desc_match = re.search(r'^description:\s*["\'](.+?)["\']', frontmatter, re.MULTILINE)

    if not name_match:
        print(f"  ⚠  Skipping {path.name}: no 'name' field in frontmatter")
        return None

    name = name_match.group(1).strip().strip('"').strip("'")
    # Truncate description for table display (max 80 chars)
    description = desc_match.group(1).strip() if desc_match else "No description"
    if len(description) > 80:
        description = description[:77] + "..."

    return {
        "name": name,
        "filename": path.name,
        "description": description,
    }


def discover_agents() -> list[dict]:
    """Find and parse all .agent.md files, sorted by name."""
    if not AGENTS_DIR.exists():
        print(f"Error: agents directory not found at {AGENTS_DIR}")
        sys.exit(1)

    agents = []
    for path in sorted(AGENTS_DIR.glob("*.agent.md")):
        agent = parse_agent_file(path)
        if agent:
            agents.append(agent)

    return agents


def generate_instructions_table(agents: list[dict]) -> str:
    """Generate the Markdown table for copilot-instructions.md."""
    lines = [
        INSTRUCTIONS_START,
        "",
        "| Agent Type | Role |",
        "|---|---|",
    ]
    for agent in agents:
        lines.append(f"| `{agent['name']}` | {agent['description']} |")
    lines.append("")
    lines.append(INSTRUCTIONS_END)
    return "\n".join(lines)


def generate_agents_md_table(agents: list[dict]) -> str:
    """Generate the Markdown table for AGENTS.md."""
    lines = [
        AGENTS_MD_START,
        "",
        "| File | Agent Type | Role |",
        "|------|-----------|------|",
    ]
    for agent in agents:
        lines.append(f"| `{agent['filename']}` | `{agent['name']}` | {agent['description']} |")
    lines.append("")
    lines.append(AGENTS_MD_END)
    return "\n".join(lines)


def replace_between_markers(content: str, start_marker: str, end_marker: str, replacement: str) -> str:
    """Replace content between start and end markers (inclusive)."""
    pattern = re.compile(
        re.escape(start_marker) + r".*?" + re.escape(end_marker),
        re.DOTALL,
    )
    if pattern.search(content):
        return pattern.sub(replacement, content)
    else:
        return None


def update_file(filepath: Path, start_marker: str, end_marker: str, new_table: str, dry_run: bool) -> bool:
    """Update a file's agent table between markers. Returns True if changes were made."""
    if not filepath.exists():
        print(f"  ⚠  File not found: {filepath}")
        return False

    content = filepath.read_text(encoding="utf-8")

    if start_marker not in content:
        print(f"  ⚠  Markers not found in {filepath.name} — needs manual migration")
        print(f"      Add {start_marker} and {end_marker} around the agent table")
        return False

    updated = replace_between_markers(content, start_marker, end_marker, new_table)
    if updated is None:
        print(f"  ⚠  Could not replace content in {filepath.name}")
        return False

    if updated == content:
        print(f"  ✓  {filepath.name} — already in sync")
        return False

    if dry_run:
        print(f"  ⟳  {filepath.name} — would update (dry run)")
    else:
        filepath.write_text(updated, encoding="utf-8")
        print(f"  ✓  {filepath.name} — updated")

    return True


def main():
    parser = argparse.ArgumentParser(description="Sync agent registry from .agent.md files")
    parser.add_argument("--write", action="store_true", help="Write changes to files (default: dry run)")
    args = parser.parse_args()

    dry_run = not args.write

    print("🔍 Scanning .github/agents/ for .agent.md files...\n")
    agents = discover_agents()
    print(f"\n   Found {len(agents)} agent(s):\n")
    for a in agents:
        print(f"   • {a['name']:30s} ({a['filename']})")

    print()

    if dry_run:
        print("📋 DRY RUN — no files will be modified. Use --write to apply.\n")

    # Generate tables
    instructions_table = generate_instructions_table(agents)
    agents_md_table = generate_agents_md_table(agents)

    # Update files
    changed = False
    changed |= update_file(INSTRUCTIONS_FILE, INSTRUCTIONS_START, INSTRUCTIONS_END, instructions_table, dry_run)
    changed |= update_file(AGENTS_MD_FILE, AGENTS_MD_START, AGENTS_MD_END, agents_md_table, dry_run)

    print()
    if not changed:
        print("✅ Everything is in sync — no changes needed.")
    elif dry_run:
        print("⟳  Run with --write to apply changes.")
    else:
        print("✅ Agent registry synced successfully.")
        print("   ⚠  Restart your Copilot CLI session for changes to take effect.")


if __name__ == "__main__":
    main()
