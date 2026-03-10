import uuid


async def test_create_thread(client, approved_agent):
    wid = approved_agent["workspace_id"]
    resp = await client.post(
        f"/workspaces/{wid}/threads",
        json={"title": "test thread"},
        headers=approved_agent["headers"],
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "test thread"
    assert data["workspace_id"] == wid


async def test_create_thread_non_member(client, registered_agent, workspace):
    resp = await client.post(
        f"/workspaces/{workspace['id']}/threads",
        json={"title": "should fail"},
        headers=registered_agent["headers"],
    )
    assert resp.status_code == 403


async def test_list_threads(client, approved_agent):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    await client.post(f"/workspaces/{wid}/threads", json={"title": "thread 1"}, headers=headers)
    await client.post(f"/workspaces/{wid}/threads", json={"title": "thread 2"}, headers=headers)

    resp = await client.get(f"/workspaces/{wid}/threads", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_get_thread(client, approved_agent):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    create_resp = await client.post(
        f"/workspaces/{wid}/threads",
        json={"title": "get me"},
        headers=headers,
    )
    thread_id = create_resp.json()["id"]

    resp = await client.get(f"/workspaces/{wid}/threads/{thread_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == thread_id
    assert resp.json()["title"] == "get me"


# --- Auth / Security ---


async def test_create_thread_no_auth(client, workspace):
    """Creating a thread without API key should fail."""
    resp = await client.post(
        f"/workspaces/{workspace['id']}/threads",
        json={"title": "no auth"},
    )
    assert resp.status_code in (401, 403, 422)


async def test_create_thread_invalid_key(client, workspace):
    """Creating a thread with an invalid API key should fail."""
    resp = await client.post(
        f"/workspaces/{workspace['id']}/threads",
        json={"title": "bad key"},
        headers={"X-API-Key": "invalid-key-12345"},
    )
    assert resp.status_code == 401


async def test_create_thread_pending_member(client, registered_agent, workspace, admin_headers):
    """An agent with pending (not approved) membership can't create threads."""
    wid = workspace["id"]
    await client.post(f"/workspaces/{wid}/join", headers=registered_agent["headers"])
    # Don't approve — leave pending
    resp = await client.post(
        f"/workspaces/{wid}/threads",
        json={"title": "pending member"},
        headers=registered_agent["headers"],
    )
    assert resp.status_code == 403


# --- Not Found ---


async def test_get_thread_not_found(client, approved_agent):
    wid = approved_agent["workspace_id"]
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/workspaces/{wid}/threads/{fake_id}", headers=approved_agent["headers"])
    assert resp.status_code == 404


async def test_create_thread_nonexistent_workspace(client, registered_agent):
    fake_ws = str(uuid.uuid4())
    resp = await client.post(
        f"/workspaces/{fake_ws}/threads",
        json={"title": "ghost workspace"},
        headers=registered_agent["headers"],
    )
    assert resp.status_code in (403, 404)


# --- Input Validation ---


async def test_create_thread_empty_title(client, approved_agent):
    wid = approved_agent["workspace_id"]
    resp = await client.post(
        f"/workspaces/{wid}/threads",
        json={"title": ""},
        headers=approved_agent["headers"],
    )
    assert resp.status_code == 422


async def test_create_thread_title_too_long(client, approved_agent):
    wid = approved_agent["workspace_id"]
    resp = await client.post(
        f"/workspaces/{wid}/threads",
        json={"title": "x" * 501},
        headers=approved_agent["headers"],
    )
    assert resp.status_code == 422


async def test_create_thread_with_nonexistent_work_item(client, approved_agent):
    """Linking a thread to a nonexistent work item should fail."""
    wid = approved_agent["workspace_id"]
    fake_wi = str(uuid.uuid4())
    resp = await client.post(
        f"/workspaces/{wid}/threads",
        json={"title": "linked thread", "work_item_id": fake_wi},
        headers=approved_agent["headers"],
    )
    assert resp.status_code == 404


# --- Pagination ---


async def test_list_threads_pagination(client, approved_agent):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    for i in range(3):
        await client.post(f"/workspaces/{wid}/threads", json={"title": f"page-{i}"}, headers=headers)

    resp = await client.get(f"/workspaces/{wid}/threads?limit=2&offset=0", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp2 = await client.get(f"/workspaces/{wid}/threads?limit=2&offset=2", headers=headers)
    assert resp2.status_code == 200
    assert len(resp2.json()) == 1


async def test_list_threads_limit_zero(client, approved_agent):
    wid = approved_agent["workspace_id"]
    resp = await client.get(f"/workspaces/{wid}/threads?limit=0")
    assert resp.status_code == 422
