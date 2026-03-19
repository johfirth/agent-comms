async def test_health_check(client):
    """Health endpoint returns ok."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
