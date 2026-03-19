import uuid


async def test_set_webhook_success(client, registered_agent):
    """Authenticated agent can set their own webhook."""
    agent_id = registered_agent["id"]
    headers = registered_agent["headers"]
    resp = await client.put(
        f"/agents/{agent_id}/webhook",
        json={"webhook_url": "https://example.com/hook"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["webhook_url"] == "https://example.com/hook"


async def test_set_webhook_invalid_url(client, registered_agent):
    """Invalid URL format should be rejected."""
    agent_id = registered_agent["id"]
    headers = registered_agent["headers"]
    resp = await client.put(
        f"/agents/{agent_id}/webhook",
        json={"webhook_url": "ftp://invalid"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_set_webhook_other_agent_forbidden(client, registered_agent):
    """Agent cannot set another agent's webhook."""
    name2 = f"other-{uuid.uuid4().hex[:8]}"
    resp2 = await client.post(
        "/agents", json={"name": name2, "display_name": "Other"}
    )
    other_id = resp2.json()["id"]

    resp = await client.put(
        f"/agents/{other_id}/webhook",
        json={"webhook_url": "https://example.com/hook"},
        headers=registered_agent["headers"],
    )
    assert resp.status_code == 403
