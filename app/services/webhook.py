import asyncio
import ipaddress
import logging
import socket
import urllib.parse
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent

logger = logging.getLogger(__name__)

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_safe_url(url: str) -> bool:
    """Check that a webhook URL doesn't target internal networks."""
    try:
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False
        addr_info = socket.getaddrinfo(hostname, None)
        for family, _, _, _, sockaddr in addr_info:
            ip = ipaddress.ip_address(sockaddr[0])
            # Unwrap IPv4-mapped IPv6 addresses (e.g. ::ffff:127.0.0.1 → 127.0.0.1)
            if hasattr(ip, 'ipv4_mapped') and ip.ipv4_mapped:
                ip = ip.ipv4_mapped
            # Block unspecified addresses (0.0.0.0 and ::)
            if ip.is_unspecified:
                return False
            for network in BLOCKED_NETWORKS:
                if ip in network:
                    return False
        return True
    except (socket.gaierror, ValueError, OSError):
        return False


async def dispatch_mention_webhooks(
    db: AsyncSession, mentioned_agent_ids: list[UUID], payload: dict
) -> None:
    """Send webhook notifications to mentioned agents."""
    if not mentioned_agent_ids:
        return

    result = await db.execute(
        select(Agent).where(
            Agent.id.in_(mentioned_agent_ids), Agent.webhook_url.isnot(None)
        )
    )
    agents = result.scalars().all()

    safe_agents: list[tuple[str, str]] = []
    for agent in agents:
        webhook_url = agent.webhook_url
        if not webhook_url:
            continue
        if not _is_safe_url(webhook_url):
            logger.warning(
                "Blocked SSRF attempt: agent %s webhook %s targets internal network",
                agent.name,
                webhook_url,
            )
            continue
        safe_agents.append((agent.name, webhook_url))

    if not safe_agents:
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        responses = await asyncio.gather(
            *(client.post(webhook_url, json=payload) for _, webhook_url in safe_agents),
            return_exceptions=True,
        )

    for (agent_name, webhook_url), response in zip(safe_agents, responses):
        if isinstance(response, Exception):
            logger.warning(
                "Webhook delivery failed for agent %s at %s",
                agent_name,
                webhook_url,
            )
