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
