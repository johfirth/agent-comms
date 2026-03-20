import socket
import urllib.parse
import uuid

import pytest

from app.services.webhook import _is_safe_url


async def test_set_webhook_success(client, registered_agent):
    """Authenticated agent can set their own webhook."""
    agent_id = registered_agent["id"]
    headers = registered_agent["headers"]
    resp = await client.put(
        f"/agents/{agent_id}/webhook",
        json={"webhook_url": "https://example.com/hook"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["webhook_url"] == "https://example.com/hook"


async def test_set_webhook_invalid_url(client, registered_agent):
    """Invalid URL format should be rejected."""
    agent_id = registered_agent["id"]
    headers = registered_agent["headers"]
    resp = await client.put(
        f"/agents/{agent_id}/webhook",
        json={"webhook_url": "ftp://invalid"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_set_webhook_other_agent_forbidden(client, registered_agent):
    """Agent cannot set another agent's webhook."""
    name2 = f"other-{uuid.uuid4().hex[:8]}"
    resp2 = await client.post(
        "/agents", json={"name": name2, "display_name": "Other"}
    )
    other_id = resp2.json()["id"]

    resp = await client.put(
        f"/agents/{other_id}/webhook",
        json={"webhook_url": "https://example.com/hook"},
        headers=registered_agent["headers"],
    )
    assert resp.status_code == 403


def _addrinfo(ip: str) -> tuple:
    if ":" in ip:
        return (
            socket.AF_INET6,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            (ip, 443, 0, 0),
        )
    return (
        socket.AF_INET,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        (ip, 443),
    )


@pytest.mark.parametrize(
    ("url", "resolved_ip"),
    [
        ("https://localhost/hook", "127.0.0.1"),
        ("https://private-10.example/hook", "10.1.2.3"),
        ("https://private-172.example/hook", "172.20.1.1"),
        ("https://private-192.example/hook", "192.168.2.5"),
        ("https://link-local-v4.example/hook", "169.254.10.20"),
        ("https://link-local-v6.example/hook", "fe80::1234"),
        ("https://unspecified-v4.example/hook", "0.0.0.0"),
        ("https://unspecified-v6.example/hook", "::"),
        ("https://[::1]/hook", "::1"),
        ("https://[::ffff:127.0.0.1]/hook", "::ffff:127.0.0.1"),
    ],
    ids=[
        "localhost",
        "private-10",
        "private-172",
        "private-192",
        "link-local-v4",
        "link-local-v6",
        "unspecified-v4",
        "unspecified-v6",
        "loopback-v6",
        "ipv4-mapped-ipv6",
    ],
)
def test_is_safe_url_blocks_ssrf_targets(monkeypatch, url, resolved_ip):
    parsed = urllib.parse.urlparse(url)
    assert parsed.hostname is not None

    def fake_getaddrinfo(hostname, _port):
        assert hostname == parsed.hostname
        return [_addrinfo(resolved_ip)]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    assert _is_safe_url(url) is False


def test_is_safe_url_allows_public_target(monkeypatch):
    url = "https://public.example/hook"

    def fake_getaddrinfo(hostname, _port):
        assert hostname == "public.example"
        return [
            _addrinfo("93.184.216.34"),
            _addrinfo("2606:2800:220:1:248:1893:25c8:1946"),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    assert _is_safe_url(url) is True
