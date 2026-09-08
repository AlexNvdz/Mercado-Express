from httpx import AsyncClient


async def test_duplicate_category_name_conflicts(admin_client: AsyncClient) -> None:
    payload = {"name": "Outdoor"}
    first = await admin_client.post("/api/v1/categories", json=payload)
    assert first.status_code == 201
    second = await admin_client.post("/api/v1/categories", json=payload)
    assert second.status_code == 409


async def test_subcategory_references_parent(admin_client: AsyncClient) -> None:
    parent = await admin_client.post("/api/v1/categories", json={"name": "Parent Cat"})
    parent_id = parent.json()["id"]

    child = await admin_client.post(
        "/api/v1/categories", json={"name": "Child Cat", "parent_id": parent_id}
    )
    assert child.status_code == 201
    assert child.json()["parent_id"] == parent_id


async def test_delete_category(admin_client: AsyncClient) -> None:
    created = await admin_client.post("/api/v1/categories", json={"name": "Temp Cat"})
    category_id = created.json()["id"]

    deleted = await admin_client.delete(f"/api/v1/categories/{category_id}")
    assert deleted.status_code == 204

    fetched = await admin_client.get(f"/api/v1/categories/{category_id}")
    assert fetched.status_code == 404


async def test_customer_cannot_create_category(customer_client: AsyncClient) -> None:
    resp = await customer_client.post("/api/v1/categories", json={"name": "Blocked"})
    assert resp.status_code == 403
