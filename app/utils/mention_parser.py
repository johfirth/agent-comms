import re

MENTION_PATTERN = re.compile(r"@([\w.-]{1,100})")

# Limit content scanned for mentions to prevent regex abuse on huge payloads
MAX_MENTION_SCAN_LENGTH = 50000

def parse_mentions(content: str) -> list[str]:
    """Extract unique @mentioned agent names from message content."""
    return list(set(MENTION_PATTERN.findall(content[:MAX_MENTION_SCAN_LENGTH])))
