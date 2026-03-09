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
