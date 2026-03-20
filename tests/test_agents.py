import uuid


async def test_register_agent(client):
    name = f"agent-{uuid.uuid4().hex[:8]}"
    resp = await client.post("/agents", json={"name": name, "display_name": f"Agent {name}"})
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert "api_key" in data
    assert data["name"] == name


async def test_register_duplicate(client):
    name = f"dup-agent-{uuid.uuid4().hex[:8]}"
    payload = {"name": name, "display_name": f"Agent {name}"}
    resp1 = await client.post("/agents", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/agents", json=payload)
    assert resp2.status_code == 409


async def test_get_agent(client, registered_agent):
    agent_id = registered_agent["id"]
    resp = await client.get(f"/agents/{agent_id}", headers=registered_agent["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == agent_id
    assert data["name"] == registered_agent["name"]
    assert "api_key" not in data


# --- Auth / Security ---


async def test_get_agent_not_found(client):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/agents/{fake_id}")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_register_agent_missing_name(client):
    resp = await client.post("/agents", json={"display_name": "No Name"})
    assert resp.status_code == 422


async def test_register_agent_missing_display_name(client):
    resp = await client.post("/agents", json={"name": "valid-name"})
    assert resp.status_code == 422


async def test_register_agent_empty_name(client):
    resp = await client.post("/agents", json={"name": "", "display_name": "Empty"})
    assert resp.status_code == 422


async def test_register_agent_empty_display_name(client):
    resp = await client.post("/agents", json={"name": "valid-name", "display_name": ""})
    assert resp.status_code == 422


async def test_register_agent_name_too_long(client):
    long_name = "a" * 101
    resp = await client.post("/agents", json={"name": long_name, "display_name": "Long"})
    assert resp.status_code == 422


async def test_register_agent_invalid_name_uppercase(client):
    resp = await client.post("/agents", json={"name": "UPPERCASE", "display_name": "Bad"})
    assert resp.status_code == 422


async def test_register_agent_invalid_name_spaces(client):
    resp = await client.post("/agents", json={"name": "has spaces", "display_name": "Bad"})
    assert resp.status_code == 422


async def test_register_agent_invalid_name_special_chars(client):
    resp = await client.post("/agents", json={"name": "agent@#$!", "display_name": "Bad"})
    assert resp.status_code == 422


async def test_register_agent_unicode_display_name(client):
    name = f"unicode-{uuid.uuid4().hex[:8]}"
    resp = await client.post("/agents", json={"name": name, "display_name": "Agent 日本語 🤖"})
    assert resp.status_code == 201
    assert resp.json()["display_name"] == "Agent 日本語 🤖"


async def test_regenerate_key_requires_admin(client, registered_agent):
    agent_id = registered_agent["id"]
    resp = await client.post(f"/agents/{agent_id}/regenerate-key", headers=registered_agent["headers"])
    assert resp.status_code == 403


async def test_regenerate_key_no_auth(client, registered_agent):
    agent_id = registered_agent["id"]
    resp = await client.post(f"/agents/{agent_id}/regenerate-key")
    assert resp.status_code == 403


async def test_regenerate_key_not_found(client, admin_headers):
    fake_id = str(uuid.uuid4())
    resp = await client.post(f"/agents/{fake_id}/regenerate-key", headers=admin_headers)
    assert resp.status_code == 404


async def test_regenerate_key_success(client, registered_agent, admin_headers):
    agent_id = registered_agent["id"]
    old_key = registered_agent["api_key"]
    resp = await client.post(f"/agents/{agent_id}/regenerate-key", headers=admin_headers)
    assert resp.status_code == 200
    new_key = resp.json()["api_key"]
    assert new_key != old_key
    # Old key should no longer work
    old_resp = await client.post(
        f"/workspaces",
        json={"name": "test-ws", "description": "test"},
        headers={"X-API-Key": old_key},
    )
    assert old_resp.status_code == 403


async def test_set_webhook_requires_auth(client, registered_agent):
    agent_id = registered_agent["id"]
    resp = await client.put(f"/agents/{agent_id}/webhook", json={"webhook_url": "http://example.com"})
    assert resp.status_code == 403
