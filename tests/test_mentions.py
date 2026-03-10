import uuid


async def test_search_mentions_empty(client, registered_agent):
    resp = await client.get(
        f"/mentions?agent_id={registered_agent['id']}",
        headers=registered_agent["headers"],
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_search_mentions_filtered(client, approved_agent, admin_headers):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]

    # Register a second agent and approve in workspace
    target_name = f"filter-target-{uuid.uuid4().hex[:8]}"
    reg_resp = await client.post("/agents", json={"name": target_name, "display_name": f"Agent {target_name}"})
    target = reg_resp.json()
    target_headers = {"X-API-Key": target["api_key"]}

    await client.post(f"/workspaces/{wid}/join", headers=target_headers)
    await client.patch(
        f"/workspaces/{wid}/members/{target['id']}",
        json={"status": "approved", "approved_by": "admin"},
        headers=admin_headers,
    )

    # Create thread and post message mentioning the target
    thread_resp = await client.post(
        f"/workspaces/{wid}/threads", json={"title": "filter thread"}, headers=headers
    )
    tid = thread_resp.json()["id"]

    await client.post(
        f"/threads/{tid}/messages",
        json={"content": f"Ping @{target_name}"},
        headers=headers,
    )

    # Search with both agent_id and workspace_id filter
    resp = await client.get(
        f"/mentions?agent_id={target['id']}&workspace_id={wid}",
        headers=target_headers,
    )
    assert resp.status_code == 200
    mentions = resp.json()
    assert len(mentions) >= 1
    assert all(m["mentioned_agent_id"] == target["id"] for m in mentions)
    assert all(m["workspace_id"] == wid for m in mentions)


# --- Input Validation ---


async def test_search_mentions_missing_agent_id(client):
    """agent_id is required for mentions search."""
    resp = await client.get("/mentions")
    assert resp.status_code == 422


async def test_search_mentions_invalid_agent_id(client):
    """Invalid UUID format should be rejected."""
    resp = await client.get("/mentions?agent_id=not-a-uuid")
    assert resp.status_code == 422


async def test_search_mentions_nonexistent_agent(client):
    """Searching mentions for a nonexistent agent should return empty list (not error)."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/mentions?agent_id={fake_id}")
    assert resp.status_code == 200
    assert resp.json() == []


# --- Pagination ---


async def test_search_mentions_pagination(client, approved_agent, admin_headers):
    """Verify limit and offset work on mentions."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]

    target_name = f"page-target-{uuid.uuid4().hex[:8]}"
    reg_resp = await client.post("/agents", json={"name": target_name, "display_name": f"Agent {target_name}"})
    target = reg_resp.json()
    target_headers = {"X-API-Key": target["api_key"]}
    await client.post(f"/workspaces/{wid}/join", headers=target_headers)
    await client.patch(
        f"/workspaces/{wid}/members/{target['id']}",
        json={"status": "approved", "approved_by": "admin"},
        headers=admin_headers,
    )

    thread_resp = await client.post(
        f"/workspaces/{wid}/threads", json={"title": "mention pagination"}, headers=headers
    )
    tid = thread_resp.json()["id"]

    # Post 3 messages mentioning the target
    for i in range(3):
        await client.post(
            f"/threads/{tid}/messages",
            json={"content": f"msg {i} @{target_name}"},
            headers=headers,
        )

    resp = await client.get(f"/mentions?agent_id={target['id']}&limit=1")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp2 = await client.get(f"/mentions?agent_id={target['id']}&limit=1&offset=1")
    assert resp2.status_code == 200
    assert len(resp2.json()) == 1
