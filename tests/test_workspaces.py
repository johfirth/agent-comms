import uuid


async def test_create_workspace(client, admin_headers):
    resp = await client.post(
        "/workspaces",
        json={"name": f"ws-{uuid.uuid4().hex[:8]}", "description": "A workspace"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert "name" in data


async def test_create_workspace_unauthorized(client):
    resp = await client.post(
        "/workspaces",
        json={"name": "unauthorized-ws", "description": "nope"},
    )
    assert resp.status_code in (401, 403)


async def test_list_workspaces(client, admin_headers):
    name1 = f"ws-list-{uuid.uuid4().hex[:8]}"
    name2 = f"ws-list-{uuid.uuid4().hex[:8]}"
    await client.post("/workspaces", json={"name": name1, "description": "first"}, headers=admin_headers)
    await client.post("/workspaces", json={"name": name2, "description": "second"}, headers=admin_headers)

    resp = await client.get("/workspaces", headers=admin_headers)
    assert resp.status_code == 200
    names = [ws["name"] for ws in resp.json()]
    assert name1 in names
    assert name2 in names


async def test_get_workspace(client, admin_headers):
    name = f"ws-get-{uuid.uuid4().hex[:8]}"
    create_resp = await client.post(
        "/workspaces",
        json={"name": name, "description": "get me"},
        headers=admin_headers,
    )
    ws_id = create_resp.json()["id"]

    resp = await client.get(f"/workspaces/{ws_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == ws_id
    assert resp.json()["name"] == name
