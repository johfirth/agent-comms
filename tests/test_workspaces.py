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


# --- Auth / Security ---


async def test_create_workspace_with_agent_key_not_admin(client, registered_agent):
    """Agent API key should not grant admin access to create workspaces."""
    resp = await client.post(
        "/workspaces",
        json={"name": "agent-ws", "description": "nope"},
        headers=registered_agent["headers"],
    )
    assert resp.status_code == 403
    assert "admin" in resp.json()["detail"].lower()


async def test_create_workspace_with_invalid_key(client):
    resp = await client.post(
        "/workspaces",
        json={"name": "bad-key-ws", "description": "nope"},
        headers={"X-API-Key": "totally-invalid-key"},
    )
    assert resp.status_code == 403


# --- Not Found / Duplicates ---


async def test_get_workspace_not_found(client):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/workspaces/{fake_id}")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_create_workspace_duplicate_name(client, admin_headers):
    name = f"dup-ws-{uuid.uuid4().hex[:8]}"
    resp1 = await client.post("/workspaces", json={"name": name}, headers=admin_headers)
    assert resp1.status_code == 201
    resp2 = await client.post("/workspaces", json={"name": name}, headers=admin_headers)
    assert resp2.status_code == 409


# --- Input Validation ---


async def test_create_workspace_empty_name(client, admin_headers):
    resp = await client.post("/workspaces", json={"name": ""}, headers=admin_headers)
    assert resp.status_code == 422


async def test_create_workspace_missing_name(client, admin_headers):
    resp = await client.post("/workspaces", json={"description": "no name"}, headers=admin_headers)
    assert resp.status_code == 422


async def test_create_workspace_name_too_long(client, admin_headers):
    long_name = "x" * 256
    resp = await client.post("/workspaces", json={"name": long_name}, headers=admin_headers)
    assert resp.status_code == 422


# --- Pagination ---


async def test_list_workspaces_pagination(client, admin_headers):
    """Create 3 workspaces and paginate with limit=1."""
    for i in range(3):
        await client.post(
            "/workspaces",
            json={"name": f"page-ws-{uuid.uuid4().hex[:8]}"},
            headers=admin_headers,
        )
    resp = await client.get("/workspaces?limit=1&offset=0", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp2 = await client.get("/workspaces?limit=1&offset=1", headers=admin_headers)
    assert resp2.status_code == 200
    assert len(resp2.json()) == 1
    assert resp.json()[0]["id"] != resp2.json()[0]["id"]


async def test_list_workspaces_limit_zero(client, admin_headers):
    """limit=0 should be rejected (ge=1)."""
    resp = await client.get("/workspaces?limit=0", headers=admin_headers)
    assert resp.status_code == 422


async def test_list_workspaces_negative_offset(client, admin_headers):
    """offset=-1 should be rejected (ge=0)."""
    resp = await client.get("/workspaces?offset=-1", headers=admin_headers)
    assert resp.status_code == 422


async def test_list_workspaces_large_offset(client, admin_headers):
    """Very large offset returns empty list."""
    resp = await client.get("/workspaces?offset=99999", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == []
