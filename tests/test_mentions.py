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
