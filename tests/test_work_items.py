import uuid


async def test_create_epic(client, approved_agent):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]

    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "My Epic"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "epic"
    assert data["title"] == "My Epic"
    assert data["parent_id"] is None


async def test_create_feature_under_epic(client, approved_agent):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]

    epic_resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "Parent Epic"},
        headers=headers,
    )
    epic_id = epic_resp.json()["id"]

    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "feature", "title": "Child Feature", "parent_id": epic_id},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["parent_id"] == epic_id
    assert resp.json()["type"] == "feature"


async def test_create_story_under_feature(client, approved_agent):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]

    epic = await client.post(f"/workspaces/{wid}/work-items", json={"type": "epic", "title": "Epic"}, headers=headers)
    feature = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "feature", "title": "Feature", "parent_id": epic.json()["id"]},
        headers=headers,
    )

    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "story", "title": "Story", "parent_id": feature.json()["id"]},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["type"] == "story"
    assert resp.json()["parent_id"] == feature.json()["id"]


async def test_create_task_under_story(client, approved_agent):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]

    epic = await client.post(f"/workspaces/{wid}/work-items", json={"type": "epic", "title": "Epic"}, headers=headers)
    feature = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "feature", "title": "Feature", "parent_id": epic.json()["id"]},
        headers=headers,
    )
    story = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "story", "title": "Story", "parent_id": feature.json()["id"]},
        headers=headers,
    )

    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "task", "title": "Task", "parent_id": story.json()["id"]},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["type"] == "task"
    assert resp.json()["parent_id"] == story.json()["id"]


async def test_invalid_hierarchy(client, approved_agent):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]

    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "feature", "title": "Orphan Feature"},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_wrong_parent_type(client, approved_agent):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]

    epic = await client.post(f"/workspaces/{wid}/work-items", json={"type": "epic", "title": "Epic"}, headers=headers)

    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "task", "title": "Bad Task", "parent_id": epic.json()["id"]},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_update_work_item(client, approved_agent):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]

    epic = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "Update Me"},
        headers=headers,
    )
    epic_id = epic.json()["id"]

    resp = await client.patch(
        f"/workspaces/{wid}/work-items/{epic_id}",
        json={"status": "in_progress"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


# --- Hierarchy Enforcement ---


async def test_epic_with_parent_rejected(client, approved_agent):
    """Epics must be root items — specifying a parent should fail."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    epic = await client.post(f"/workspaces/{wid}/work-items", json={"type": "epic", "title": "Root"}, headers=headers)

    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "Child Epic", "parent_id": epic.json()["id"]},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "must not have a parent" in resp.json()["detail"]


async def test_story_under_epic_rejected(client, approved_agent):
    """Story requires Feature parent, not Epic."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    epic = await client.post(f"/workspaces/{wid}/work-items", json={"type": "epic", "title": "Epic"}, headers=headers)

    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "story", "title": "Bad Story", "parent_id": epic.json()["id"]},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "feature" in resp.json()["detail"].lower()


async def test_task_under_feature_rejected(client, approved_agent):
    """Task requires Story parent, not Feature."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    epic = await client.post(f"/workspaces/{wid}/work-items", json={"type": "epic", "title": "Epic"}, headers=headers)
    feature = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "feature", "title": "Feature", "parent_id": epic.json()["id"]},
        headers=headers,
    )

    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "task", "title": "Bad Task", "parent_id": feature.json()["id"]},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "story" in resp.json()["detail"].lower()


async def test_task_under_epic_rejected(client, approved_agent):
    """Task requires Story parent, not Epic (skip two levels)."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    epic = await client.post(f"/workspaces/{wid}/work-items", json={"type": "epic", "title": "Epic"}, headers=headers)

    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "task", "title": "Way Bad Task", "parent_id": epic.json()["id"]},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_feature_under_story_rejected(client, approved_agent):
    """Feature requires Epic parent, not Story (reverse hierarchy)."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    epic = await client.post(f"/workspaces/{wid}/work-items", json={"type": "epic", "title": "Epic"}, headers=headers)
    feature = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "feature", "title": "Feature", "parent_id": epic.json()["id"]},
        headers=headers,
    )
    story = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "story", "title": "Story", "parent_id": feature.json()["id"]},
        headers=headers,
    )

    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "feature", "title": "Nested Feature", "parent_id": story.json()["id"]},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_story_without_parent_rejected(client, approved_agent):
    """Story requires a Feature parent — orphan should fail."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]

    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "story", "title": "Orphan Story"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "requires a parent" in resp.json()["detail"]


async def test_task_without_parent_rejected(client, approved_agent):
    """Task requires a Story parent — orphan should fail."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]

    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "task", "title": "Orphan Task"},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_nonexistent_parent_rejected(client, approved_agent):
    """Referencing a nonexistent parent should fail."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    fake_parent = str(uuid.uuid4())

    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "feature", "title": "Ghost Parent", "parent_id": fake_parent},
        headers=headers,
    )
    assert resp.status_code == 404
    assert "parent" in resp.json()["detail"].lower()


# --- Auth / Security ---


async def test_create_work_item_no_auth(client, approved_agent):
    """Creating a work item without auth should fail."""
    wid = approved_agent["workspace_id"]
    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "No Auth Epic"},
    )
    assert resp.status_code in (401, 403, 422)


async def test_create_work_item_invalid_key(client, approved_agent):
    wid = approved_agent["workspace_id"]
    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "Bad Key Epic"},
        headers={"X-API-Key": "not-a-real-key"},
    )
    assert resp.status_code == 401


async def test_create_work_item_non_member(client, registered_agent, workspace):
    """Agent not in workspace can't create work items."""
    wid = workspace["id"]
    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "Outsider Epic"},
        headers=registered_agent["headers"],
    )
    assert resp.status_code == 403


async def test_update_work_item_non_member(client, approved_agent):
    """Agent not in workspace can't update work items."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    epic = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "Locked Epic"},
        headers=headers,
    )
    epic_id = epic.json()["id"]

    # Create a fresh agent that is NOT a member
    outsider_name = f"outsider-{uuid.uuid4().hex[:8]}"
    reg = await client.post("/agents", json={"name": outsider_name, "display_name": f"Outsider {outsider_name}"})
    outsider_headers = {"X-API-Key": reg.json()["api_key"]}

    resp = await client.patch(
        f"/workspaces/{wid}/work-items/{epic_id}",
        json={"status": "done"},
        headers=outsider_headers,
    )
    assert resp.status_code == 403


# --- Not Found ---


async def test_get_work_item_not_found(client, approved_agent):
    wid = approved_agent["workspace_id"]
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/workspaces/{wid}/work-items/{fake_id}")
    assert resp.status_code == 404


async def test_update_work_item_not_found(client, approved_agent):
    wid = approved_agent["workspace_id"]
    fake_id = str(uuid.uuid4())
    resp = await client.patch(
        f"/workspaces/{wid}/work-items/{fake_id}",
        json={"status": "done"},
        headers=approved_agent["headers"],
    )
    assert resp.status_code == 404


# --- Input Validation ---


async def test_create_work_item_empty_title(client, approved_agent):
    wid = approved_agent["workspace_id"]
    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": ""},
        headers=approved_agent["headers"],
    )
    assert resp.status_code == 422


async def test_create_work_item_title_too_long(client, approved_agent):
    wid = approved_agent["workspace_id"]
    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "x" * 501},
        headers=approved_agent["headers"],
    )
    assert resp.status_code == 422


async def test_create_work_item_invalid_type(client, approved_agent):
    wid = approved_agent["workspace_id"]
    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "invalid-type", "title": "Bad Type"},
        headers=approved_agent["headers"],
    )
    assert resp.status_code == 422


async def test_create_work_item_description_too_long(client, approved_agent):
    wid = approved_agent["workspace_id"]
    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "Big Desc", "description": "x" * 5001},
        headers=approved_agent["headers"],
    )
    assert resp.status_code == 422


async def test_update_work_item_invalid_status(client, approved_agent):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    epic = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "Status Test"},
        headers=headers,
    )

    resp = await client.patch(
        f"/workspaces/{wid}/work-items/{epic.json()['id']}",
        json={"status": "invalid_status"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_update_work_item_all_statuses(client, approved_agent):
    """All valid statuses should be accepted."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    epic = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "Status Cycle"},
        headers=headers,
    )
    epic_id = epic.json()["id"]

    for status in ["in_progress", "review", "done", "cancelled", "backlog"]:
        resp = await client.patch(
            f"/workspaces/{wid}/work-items/{epic_id}",
            json={"status": status},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == status


async def test_assign_nonexistent_agent(client, approved_agent):
    """Assigning to a nonexistent agent should fail."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]

    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "Ghost Agent", "assigned_agent_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert resp.status_code == 404


async def test_create_work_item_assign_approved_member(client, approved_agent, admin_headers):
    """Assigning to an approved member in the same workspace should succeed."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]

    assignee_name = f"assignee-{uuid.uuid4().hex[:8]}"
    reg = await client.post("/agents", json={"name": assignee_name, "display_name": f"Assignee {assignee_name}"})
    assert reg.status_code == 201
    assignee = reg.json()
    assignee_headers = {"X-API-Key": assignee["api_key"]}

    join_resp = await client.post(f"/workspaces/{wid}/join", headers=assignee_headers)
    assert join_resp.status_code == 201
    approve_resp = await client.patch(
        f"/workspaces/{wid}/members/{assignee['id']}",
        json={"status": "approved", "approved_by": "admin"},
        headers=admin_headers,
    )
    assert approve_resp.status_code == 200

    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "Assigned Epic", "assigned_agent_id": assignee["id"]},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["assigned_agent_id"] == assignee["id"]


async def test_create_work_item_assign_non_member_rejected(client, approved_agent):
    """Assigning to an existing agent outside the workspace should fail."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]

    outsider_name = f"outsider-{uuid.uuid4().hex[:8]}"
    reg = await client.post("/agents", json={"name": outsider_name, "display_name": f"Outsider {outsider_name}"})
    assert reg.status_code == 201
    outsider = reg.json()

    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "Cross Workspace", "assigned_agent_id": outsider["id"]},
        headers=headers,
    )
    assert resp.status_code == 403
    assert "approved member" in resp.json()["detail"].lower()


async def test_create_work_item_assign_pending_member_rejected(client, approved_agent):
    """Assigning to a pending (not approved) member should fail."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]

    pending_name = f"pending-{uuid.uuid4().hex[:8]}"
    reg = await client.post("/agents", json={"name": pending_name, "display_name": f"Pending {pending_name}"})
    assert reg.status_code == 201
    pending = reg.json()
    pending_headers = {"X-API-Key": pending["api_key"]}

    join_resp = await client.post(f"/workspaces/{wid}/join", headers=pending_headers)
    assert join_resp.status_code == 201

    resp = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "Pending Assignee", "assigned_agent_id": pending["id"]},
        headers=headers,
    )
    assert resp.status_code == 403
    assert "approved member" in resp.json()["detail"].lower()


async def test_update_work_item_assign_nonexistent_agent(client, approved_agent):
    """Updating assignment to a nonexistent agent should fail."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    epic = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "Reassign Me"},
        headers=headers,
    )
    assert epic.status_code == 201

    resp = await client.patch(
        f"/workspaces/{wid}/work-items/{epic.json()['id']}",
        json={"assigned_agent_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert resp.status_code == 404


async def test_update_work_item_assign_approved_member(client, approved_agent, admin_headers):
    """Updating assignment to an approved member in the same workspace should succeed."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    epic = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "Update Assignment"},
        headers=headers,
    )
    assert epic.status_code == 201

    assignee_name = f"up-assignee-{uuid.uuid4().hex[:8]}"
    reg = await client.post("/agents", json={"name": assignee_name, "display_name": f"Assignee {assignee_name}"})
    assert reg.status_code == 201
    assignee = reg.json()
    assignee_headers = {"X-API-Key": assignee["api_key"]}
    join_resp = await client.post(f"/workspaces/{wid}/join", headers=assignee_headers)
    assert join_resp.status_code == 201
    approve_resp = await client.patch(
        f"/workspaces/{wid}/members/{assignee['id']}",
        json={"status": "approved", "approved_by": "admin"},
        headers=admin_headers,
    )
    assert approve_resp.status_code == 200

    resp = await client.patch(
        f"/workspaces/{wid}/work-items/{epic.json()['id']}",
        json={"assigned_agent_id": assignee["id"]},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["assigned_agent_id"] == assignee["id"]


async def test_update_work_item_assign_non_member_rejected(client, approved_agent):
    """Updating assignment to a non-member should fail."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    epic = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "Update Non Member"},
        headers=headers,
    )
    assert epic.status_code == 201

    outsider_name = f"up-outsider-{uuid.uuid4().hex[:8]}"
    reg = await client.post("/agents", json={"name": outsider_name, "display_name": f"Outsider {outsider_name}"})
    assert reg.status_code == 201
    outsider = reg.json()

    resp = await client.patch(
        f"/workspaces/{wid}/work-items/{epic.json()['id']}",
        json={"assigned_agent_id": outsider["id"]},
        headers=headers,
    )
    assert resp.status_code == 403
    assert "approved member" in resp.json()["detail"].lower()


async def test_update_work_item_assign_pending_member_rejected(client, approved_agent):
    """Updating assignment to a pending member should fail."""
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    epic = await client.post(
        f"/workspaces/{wid}/work-items",
        json={"type": "epic", "title": "Update Pending"},
        headers=headers,
    )
    assert epic.status_code == 201

    pending_name = f"up-pending-{uuid.uuid4().hex[:8]}"
    reg = await client.post("/agents", json={"name": pending_name, "display_name": f"Pending {pending_name}"})
    assert reg.status_code == 201
    pending = reg.json()
    pending_headers = {"X-API-Key": pending["api_key"]}
    join_resp = await client.post(f"/workspaces/{wid}/join", headers=pending_headers)
    assert join_resp.status_code == 201

    resp = await client.patch(
        f"/workspaces/{wid}/work-items/{epic.json()['id']}",
        json={"assigned_agent_id": pending["id"]},
        headers=headers,
    )
    assert resp.status_code == 403
    assert "approved member" in resp.json()["detail"].lower()


# --- Pagination / Filtering ---


async def test_list_work_items_filter_by_type(client, approved_agent):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    await client.post(f"/workspaces/{wid}/work-items", json={"type": "epic", "title": "E1"}, headers=headers)
    await client.post(f"/workspaces/{wid}/work-items", json={"type": "epic", "title": "E2"}, headers=headers)

    resp = await client.get(f"/workspaces/{wid}/work-items?type=epic")
    assert resp.status_code == 200
    for item in resp.json():
        assert item["type"] == "epic"


async def test_list_work_items_filter_by_status(client, approved_agent):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    epic = await client.post(
        f"/workspaces/{wid}/work-items", json={"type": "epic", "title": "Done Epic"}, headers=headers
    )
    await client.patch(
        f"/workspaces/{wid}/work-items/{epic.json()['id']}",
        json={"status": "done"},
        headers=headers,
    )

    resp = await client.get(f"/workspaces/{wid}/work-items?status=done")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    for item in resp.json():
        assert item["status"] == "done"


async def test_list_work_items_pagination(client, approved_agent):
    wid = approved_agent["workspace_id"]
    headers = approved_agent["headers"]
    for i in range(3):
        await client.post(f"/workspaces/{wid}/work-items", json={"type": "epic", "title": f"E-{i}"}, headers=headers)

    resp = await client.get(f"/workspaces/{wid}/work-items?limit=1")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp2 = await client.get(f"/workspaces/{wid}/work-items?limit=1&offset=1")
    assert resp2.status_code == 200
    assert len(resp2.json()) == 1
    assert resp.json()[0]["id"] != resp2.json()[0]["id"]


async def test_list_work_items_invalid_type_filter(client, approved_agent):
    wid = approved_agent["workspace_id"]
    resp = await client.get(f"/workspaces/{wid}/work-items?type=invalid")
    assert resp.status_code == 422
