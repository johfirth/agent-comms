import pytest


# --- GET /api/dashboard/overview ---


async def test_dashboard_overview_empty(client):
    """Overview returns zeros when no data exists."""
    resp = await client.get("/api/dashboard/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_workspaces"] == 0
    assert data["total_agents"] == 0
    assert data["total_threads"] == 0
    assert data["total_messages"] == 0
    assert data["total_work_items"] == 0
    assert data["workspaces"] == []


async def test_dashboard_overview_with_data(client, approved_agent):
    """Overview returns correct counts after creating data."""
    resp = await client.get("/api/dashboard/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_workspaces"] >= 1
    assert data["total_agents"] >= 1
    assert len(data["workspaces"]) >= 1


# --- GET /api/dashboard/recent-messages ---


async def test_dashboard_recent_messages_empty(client):
    """No messages returns empty list."""
    resp = await client.get("/api/dashboard/recent-messages")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_dashboard_recent_messages_with_data(client, approved_agent):
    """Messages appear in dashboard after posting."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    thread_resp = await client.post(
        f"/workspaces/{wid}/threads",
        json={"title": "Dashboard test"},
        headers=headers,
    )
    tid = thread_resp.json()["id"]
    await client.post(
        f"/threads/{tid}/messages",
        json={"content": "Hello dashboard"},
        headers=headers,
    )

    resp = await client.get("/api/dashboard/recent-messages")
    assert resp.status_code == 200
    msgs = resp.json()
    assert len(msgs) >= 1
    assert msgs[0]["content"] == "Hello dashboard"


async def test_dashboard_recent_messages_workspace_filter(client, approved_agent):
    """Filter by workspace_id returns 200."""
    wid = approved_agent["workspace_id"]
    resp = await client.get(f"/api/dashboard/recent-messages?workspace_id={wid}")
    assert resp.status_code == 200


# --- GET /api/dashboard/threads ---


async def test_dashboard_threads(client, approved_agent):
    """Threads endpoint returns threads with message_count."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    await client.post(
        f"/workspaces/{wid}/threads",
        json={"title": "Thread for dashboard"},
        headers=headers,
    )
    resp = await client.get(f"/api/dashboard/threads?workspace_id={wid}")
    assert resp.status_code == 200
    threads = resp.json()
    assert len(threads) >= 1
    assert "message_count" in threads[0]


# --- GET /api/dashboard/work-items ---


async def test_dashboard_work_items(client, approved_agent):
    """Work items endpoint returns items for a workspace."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "Dashboard epic"},
        headers=headers,
    )
    resp = await client.get(f"/api/dashboard/work-items?workspace_id={wid}")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1


# --- GET /api/dashboard/mentions ---


async def test_dashboard_mentions_empty(client):
    """No mentions returns empty list."""
    resp = await client.get("/api/dashboard/mentions")
    assert resp.status_code == 200
    assert resp.json() == []


# --- GET /dashboard (HTML page) ---


async def test_dashboard_page(client):
    """Dashboard HTML page loads."""
    resp = await client.get("/dashboard")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
