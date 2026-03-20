import asyncio
import logging
import uuid

import httpx

from app.models.agent import Agent
from app.services import webhook as webhook_service


async def _create_agents(db_session, names_and_urls):
    agents = []
    for name, webhook_url in names_and_urls:
        agent = Agent(
            name=f"{name}-{uuid.uuid4().hex[:8]}",
            display_name=name,
            api_key_hash=f"hash-{name}",
            webhook_url=webhook_url,
        )
        db_session.add(agent)
        agents.append(agent)
    await db_session.commit()
    return agents


async def test_dispatch_mention_webhooks_dispatches_concurrently(db_session, monkeypatch):
    agents = await _create_agents(
        db_session,
        [
            ("slow-a", "https://slow-a.example/hook"),
            ("slow-b", "https://slow-b.example/hook"),
            ("slow-c", "https://slow-c.example/hook"),
        ],
    )
    mentioned_agent_ids = [agent.id for agent in agents]

    monkeypatch.setattr(webhook_service, "_is_safe_url", lambda _url: True)

    active_requests = 0
    max_active_requests = 0

    async def fake_post(self, url, *, json=None, **kwargs):
        nonlocal active_requests, max_active_requests
        active_requests += 1
        max_active_requests = max(max_active_requests, active_requests)
        await asyncio.sleep(0.05)
        active_requests -= 1
        return httpx.Response(status_code=200)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    await webhook_service.dispatch_mention_webhooks(
        db_session, mentioned_agent_ids, {"event": "mention"}
    )

    assert max_active_requests > 1


async def test_dispatch_mention_webhooks_isolates_failures(db_session, monkeypatch, caplog):
    fail_url = "https://fail.example/hook"
    agents = await _create_agents(
        db_session,
        [
            ("ok-a", "https://ok-a.example/hook"),
            ("will-fail", fail_url),
            ("ok-b", "https://ok-b.example/hook"),
        ],
    )
    mentioned_agent_ids = [agent.id for agent in agents]
    expected_urls = {agent.webhook_url for agent in agents}

    monkeypatch.setattr(webhook_service, "_is_safe_url", lambda _url: True)
    caplog.set_level(logging.WARNING, logger=webhook_service.__name__)

    called_urls = []

    async def fake_post(self, url, *, json=None, **kwargs):
        called_urls.append(url)
        if url == fail_url:
            raise httpx.ReadTimeout("timed out")
        return httpx.Response(status_code=200)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    await webhook_service.dispatch_mention_webhooks(
        db_session, mentioned_agent_ids, {"event": "mention"}
    )

    assert set(called_urls) == expected_urls
    failure_logs = [
        record.message
        for record in caplog.records
        if "Webhook delivery failed for agent" in record.message
    ]
    assert len(failure_logs) == 1
    assert fail_url in failure_logs[0]


async def test_dispatch_mention_webhooks_blocks_unsafe_urls(db_session, monkeypatch, caplog):
    safe_url = "https://safe.example/hook"
    blocked_url = "https://internal.example/hook"
    agents = await _create_agents(
        db_session,
        [
            ("safe-agent", safe_url),
            ("blocked-agent", blocked_url),
        ],
    )
    mentioned_agent_ids = [agent.id for agent in agents]

    monkeypatch.setattr(webhook_service, "_is_safe_url", lambda url: url != blocked_url)
    caplog.set_level(logging.WARNING, logger=webhook_service.__name__)

    called_urls = []

    async def fake_post(self, url, *, json=None, **kwargs):
        called_urls.append(url)
        return httpx.Response(status_code=200)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    await webhook_service.dispatch_mention_webhooks(
        db_session, mentioned_agent_ids, {"event": "mention"}
    )

    assert called_urls == [safe_url]
    blocked_logs = [
        record.message for record in caplog.records if "Blocked SSRF attempt" in record.message
    ]
    assert len(blocked_logs) == 1
    assert blocked_url in blocked_logs[0]
