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
