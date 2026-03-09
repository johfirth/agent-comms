import re

MENTION_PATTERN = re.compile(r"@([\w.-]+)")

def parse_mentions(content: str) -> list[str]:
    """Extract unique @mentioned agent names from message content."""
    return list(set(MENTION_PATTERN.findall(content)))
