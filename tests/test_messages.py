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


# --- Auth / Security ---


async def test_post_message_no_auth(client, approved_agent):
    """Posting a message without API key should fail."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    thread_resp = await client.post(
        f"/workspaces/{wid}/threads", json={"title": "auth test"}, headers=headers
    )
    tid = thread_resp.json()["id"]

    resp = await client.post(f"/threads/{tid}/messages", json={"content": "no auth"})
    assert resp.status_code in (401, 403, 422)


async def test_post_message_invalid_key(client, approved_agent):
    """Posting a message with an invalid API key should fail."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    thread_resp = await client.post(
        f"/workspaces/{wid}/threads", json={"title": "auth test2"}, headers=headers
    )
    tid = thread_resp.json()["id"]

    resp = await client.post(
        f"/threads/{tid}/messages",
        json={"content": "bad key"},
        headers={"X-API-Key": "completely-wrong-key"},
    )
    assert resp.status_code == 401


async def test_post_message_non_member(client, approved_agent):
    """Agent who is not a member of the workspace can't post messages."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    thread_resp = await client.post(
        f"/workspaces/{wid}/threads", json={"title": "member test"}, headers=headers
    )
    tid = thread_resp.json()["id"]

    # Create a fresh agent that is NOT a member of the workspace
    import uuid as _uuid
    outsider_name = f"outsider-{_uuid.uuid4().hex[:8]}"
    reg = await client.post("/agents", json={"name": outsider_name, "display_name": f"Outsider {outsider_name}"})
    outsider_headers = {"X-API-Key": reg.json()["api_key"]}

    resp = await client.post(
        f"/threads/{tid}/messages",
        json={"content": "I'm not a member"},
        headers=outsider_headers,
    )
    assert resp.status_code == 403


# --- Not Found ---


async def test_post_message_nonexistent_thread(client, registered_agent):
    fake_tid = str(uuid.uuid4())
    resp = await client.post(
        f"/threads/{fake_tid}/messages",
        json={"content": "ghost thread"},
        headers=registered_agent["headers"],
    )
    assert resp.status_code == 404


async def test_list_messages_nonexistent_thread(client):
    fake_tid = str(uuid.uuid4())
    resp = await client.get(f"/threads/{fake_tid}/messages")
    assert resp.status_code == 404


# --- Input Validation ---


async def test_post_message_empty_content(client, approved_agent):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    thread_resp = await client.post(
        f"/workspaces/{wid}/threads", json={"title": "empty msg test"}, headers=headers
    )
    tid = thread_resp.json()["id"]

    resp = await client.post(
        f"/threads/{tid}/messages",
        json={"content": ""},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_post_message_content_too_long(client, approved_agent):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    thread_resp = await client.post(
        f"/workspaces/{wid}/threads", json={"title": "long msg test"}, headers=headers
    )
    tid = thread_resp.json()["id"]

    resp = await client.post(
        f"/threads/{tid}/messages",
        json={"content": "x" * 50001},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_post_message_unicode_content(client, approved_agent):
    """Unicode messages should work fine."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    thread_resp = await client.post(
        f"/workspaces/{wid}/threads", json={"title": "unicode msg"}, headers=headers
    )
    tid = thread_resp.json()["id"]

    content = "Hello 世界! 🎉 Ñoño — こんにちは"
    resp = await client.post(
        f"/threads/{tid}/messages",
        json={"content": content},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["content"] == content


# --- Pagination ---


async def test_list_messages_pagination(client, approved_agent):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    thread_resp = await client.post(
        f"/workspaces/{wid}/threads", json={"title": "paginate msgs"}, headers=headers
    )
    tid = thread_resp.json()["id"]

    for i in range(5):
        await client.post(f"/threads/{tid}/messages", json={"content": f"msg-{i}"}, headers=headers)

    resp = await client.get(f"/threads/{tid}/messages?limit=2&offset=0")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp2 = await client.get(f"/threads/{tid}/messages?limit=2&offset=3")
    assert resp2.status_code == 200
    assert len(resp2.json()) == 2


async def test_list_messages_limit_exceeds_max(client, approved_agent):
    """limit=201 should be rejected (le=200)."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    thread_resp = await client.post(
        f"/workspaces/{wid}/threads", json={"title": "limit test"}, headers=headers
    )
    tid = thread_resp.json()["id"]

    resp = await client.get(f"/threads/{tid}/messages?limit=201")
    assert resp.status_code == 422
