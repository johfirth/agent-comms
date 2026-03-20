import uuid


async def test_join_workspace(client, registered_agent, workspace):
    """Agent can request to join a workspace."""
    resp = await client.post(
        f"/workspaces/{workspace['id']}/join",
        headers=registered_agent["headers"],
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["agent_id"] == registered_agent["id"]
    assert data["workspace_id"] == workspace["id"]
    assert data["status"] == "pending"


async def test_join_workspace_duplicate(client, registered_agent, workspace):
    """Joining the same workspace twice should fail."""
    resp1 = await client.post(
        f"/workspaces/{workspace['id']}/join",
        headers=registered_agent["headers"],
    )
    assert resp1.status_code == 201

    resp2 = await client.post(
        f"/workspaces/{workspace['id']}/join",
        headers=registered_agent["headers"],
    )
    assert resp2.status_code == 409


async def test_join_workspace_no_auth(client, workspace):
    """Joining without auth should fail."""
    resp = await client.post(f"/workspaces/{workspace['id']}/join")
    assert resp.status_code == 403


async def test_join_nonexistent_workspace(client, registered_agent):
    """Joining a nonexistent workspace should fail."""
    fake_ws = str(uuid.uuid4())
    resp = await client.post(
        f"/workspaces/{fake_ws}/join",
        headers=registered_agent["headers"],
    )
    assert resp.status_code == 404


async def test_approve_membership(client, registered_agent, workspace, admin_headers):
    """Admin can approve a membership."""
    await client.post(
        f"/workspaces/{workspace['id']}/join",
        headers=registered_agent["headers"],
    )

    resp = await client.patch(
        f"/workspaces/{workspace['id']}/members/{registered_agent['id']}",
        json={"status": "approved", "approved_by": "test-admin"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert resp.json()["approved_by"] == "test-admin"
    assert resp.json()["resolved_at"] is not None


async def test_reject_membership(client, registered_agent, workspace, admin_headers):
    """Admin can reject a membership."""
    await client.post(
        f"/workspaces/{workspace['id']}/join",
        headers=registered_agent["headers"],
    )

    resp = await client.patch(
        f"/workspaces/{workspace['id']}/members/{registered_agent['id']}",
        json={"status": "rejected", "approved_by": "test-admin"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


async def test_update_membership_requires_admin(client, registered_agent, workspace):
    """Non-admin agent cannot approve/reject memberships."""
    await client.post(
        f"/workspaces/{workspace['id']}/join",
        headers=registered_agent["headers"],
    )

    resp = await client.patch(
        f"/workspaces/{workspace['id']}/members/{registered_agent['id']}",
        json={"status": "approved", "approved_by": "self"},
        headers=registered_agent["headers"],
    )
    assert resp.status_code == 403


async def test_update_membership_not_found(client, workspace, admin_headers):
    """Updating membership for agent that never joined should 404."""
    fake_agent = str(uuid.uuid4())
    resp = await client.patch(
        f"/workspaces/{workspace['id']}/members/{fake_agent}",
        json={"status": "approved", "approved_by": "admin"},
        headers=admin_headers,
    )
    assert resp.status_code == 404


async def test_update_membership_invalid_status(client, registered_agent, workspace, admin_headers):
    """Invalid membership status should be rejected by schema."""
    await client.post(
        f"/workspaces/{workspace['id']}/join",
        headers=registered_agent["headers"],
    )

    resp = await client.patch(
        f"/workspaces/{workspace['id']}/members/{registered_agent['id']}",
        json={"status": "invalid", "approved_by": "admin"},
        headers=admin_headers,
    )
    assert resp.status_code == 422


async def test_list_members(client, registered_agent, workspace, admin_headers):
    """List members of a workspace."""
    await client.post(
        f"/workspaces/{workspace['id']}/join",
        headers=registered_agent["headers"],
    )

    resp = await client.get(f"/workspaces/{workspace['id']}/members")
    assert resp.status_code == 200
    members = resp.json()
    assert len(members) >= 1
    assert any(m["agent_id"] == registered_agent["id"] for m in members)


async def test_list_members_filter_by_status(client, registered_agent, workspace, admin_headers):
    """Filter members by status."""
    await client.post(
        f"/workspaces/{workspace['id']}/join",
        headers=registered_agent["headers"],
    )

    resp = await client.get(f"/workspaces/{workspace['id']}/members?status=pending")
    assert resp.status_code == 200
    for m in resp.json():
        assert m["status"] == "pending"

    resp2 = await client.get(f"/workspaces/{workspace['id']}/members?status=approved")
    assert resp2.status_code == 200
    for m in resp2.json():
        assert m["status"] == "approved"


async def test_list_members_invalid_status_filter(client, workspace):
    """Invalid status filter should be rejected."""
    resp = await client.get(f"/workspaces/{workspace['id']}/members?status=bogus")
    assert resp.status_code == 422


async def test_list_members_nonexistent_workspace(client):
    """Listing members of nonexistent workspace should 404."""
    fake_ws = str(uuid.uuid4())
    resp = await client.get(f"/workspaces/{fake_ws}/members")
    assert resp.status_code == 404
