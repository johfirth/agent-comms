import uuid


async def test_post_message(client, approved_agent):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]

    thread_resp = await client.post(
        f"/workspaces/{wid}/threads", json={"title": "msg thread"}, headers=headers
    )
    tid = thread_resp.json()["id"]

    resp = await client.post(
        f"/threads/{tid}/messages",
        json={"content": "hello world"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["content"] == "hello world"


async def test_list_messages(client, approved_agent):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]

    thread_resp = await client.post(
        f"/workspaces/{wid}/threads", json={"title": "list thread"}, headers=headers
    )
    tid = thread_resp.json()["id"]

    for i in range(3):
        await client.post(f"/threads/{tid}/messages", json={"content": f"msg {i}"}, headers=headers)

    resp = await client.get(f"/threads/{tid}/messages", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 3


async def test_message_with_mention(client, approved_agent, admin_headers):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]

    # Register a second agent and approve it in the workspace
    second_name = f"mention-target-{uuid.uuid4().hex[:8]}"
    reg_resp = await client.post("/agents", json={"name": second_name, "display_name": f"Agent {second_name}"})
    second = reg_resp.json()
    second_headers = {"X-API-Key": second["api_key"]}

    await client.post(f"/workspaces/{wid}/join", headers=second_headers)
    await client.patch(
        f"/workspaces/{wid}/members/{second['id']}",
        json={"status": "approved", "approved_by": "admin"},
        headers=admin_headers,
    )

    # Create thread and post message with mention
    thread_resp = await client.post(
        f"/workspaces/{wid}/threads", json={"title": "mention thread"}, headers=headers
    )
    tid = thread_resp.json()["id"]

    await client.post(
        f"/threads/{tid}/messages",
        json={"content": f"Hey @{second_name} check this out"},
        headers=headers,
    )

    # Verify mention was created
    resp = await client.get(f"/mentions?agent_id={second['id']}", headers=second_headers)
    assert resp.status_code == 200
    mentions = resp.json()
    assert len(mentions) >= 1
    assert any(m["mentioned_agent_id"] == second["id"] for m in mentions)
