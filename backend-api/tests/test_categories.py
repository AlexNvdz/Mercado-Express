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

    child = await admin_client.post("/api/v1/categories", json={"name": "Child Cat", "parent_id": parent_id})
    assert child.status_code == 201
    assert child.json()["parent_id"] == parent_id


async def test_delete_category(admin_client: AsyncClient) -> None:
    created = await admin_client.post("/api/v1/categories", json={"name": "Temp Cat"})
    category_id = created.json()["id"]

    deleted = await admin_client.delete(f"/api/v1/categories/{category_id}")
    assert deleted.status_code == 204

    fetched = await admin_client.get(f"/api/v1/categories/{category_id}")
    assert fetched.status_code == 404


async def test_delete_category_with_products_conflicts(admin_client: AsyncClient) -> None:
    created = await admin_client.post("/api/v1/categories", json={"name": "Stocked Cat"})
    category_id = created.json()["id"]
    product = await admin_client.post(
        "/api/v1/products",
        json={"sku": "SKU-CAT-DEL", "name": "Kept", "category_id": category_id, "price": "1.00"},
    )
    assert product.status_code == 201

    deleted = await admin_client.delete(f"/api/v1/categories/{category_id}")
    assert deleted.status_code == 409

    fetched = await admin_client.get(f"/api/v1/categories/{category_id}")
    assert fetched.status_code == 200


async def test_delete_parent_category_keeps_subcategories(admin_client: AsyncClient) -> None:
    parent = await admin_client.post("/api/v1/categories", json={"name": "Old Parent"})
    parent_id = parent.json()["id"]
    child = await admin_client.post(
        "/api/v1/categories", json={"name": "Orphan Child", "parent_id": parent_id}
    )
    child_id = child.json()["id"]

    deleted = await admin_client.delete(f"/api/v1/categories/{parent_id}")
    assert deleted.status_code == 204

    fetched = await admin_client.get(f"/api/v1/categories/{child_id}")
    assert fetched.status_code == 200
    assert fetched.json()["parent_id"] is None


async def test_customer_cannot_create_category(customer_client: AsyncClient) -> None:
    resp = await customer_client.post("/api/v1/categories", json={"name": "Blocked"})
    assert resp.status_code == 403


async def _category_with_products(
    admin_client: AsyncClient, name: str, active: int, inactive: int = 0
) -> str:
    category_id = (await admin_client.post("/api/v1/categories", json={"name": name})).json()["id"]
    for n in range(active + inactive):
        product = await admin_client.post(
            "/api/v1/products",
            json={"sku": f"{name}-{n}", "name": f"{name} {n}", "category_id": category_id, "price": "1.00"},
        )
        if n >= active:
            await admin_client.patch(f"/api/v1/products/{product.json()['id']}", json={"is_active": False})
    return category_id


async def test_active_product_count_in_list_detail_and_writes(
    admin_client: AsyncClient, client: AsyncClient
) -> None:
    category_id = await _category_with_products(admin_client, "Counted", active=2, inactive=3)

    listed = (await client.get("/api/v1/categories")).json()["items"]
    assert [(c["name"], c["active_product_count"]) for c in listed] == [("Counted", 2)]
    assert (await client.get(f"/api/v1/categories/{category_id}")).json()["active_product_count"] == 2
    renamed = await admin_client.patch(f"/api/v1/categories/{category_id}", json={"name": "Counted 2"})
    assert renamed.json()["active_product_count"] == 2
    created = await admin_client.post("/api/v1/categories", json={"name": "Brand new"})
    assert created.json()["active_product_count"] == 0


async def test_with_products_filter_and_sort_by_products_with_pagination(
    admin_client: AsyncClient, client: AsyncClient
) -> None:
    await _category_with_products(admin_client, "B-one", active=1)
    await _category_with_products(admin_client, "C-three", active=3)
    await _category_with_products(admin_client, "A-one", active=1)
    await _category_with_products(admin_client, "D-none", active=0, inactive=2)
    await _category_with_products(admin_client, "E-empty", active=0)

    async def names(**params: str) -> tuple[list[str], int]:
        body = (await client.get("/api/v1/categories", params=params)).json()
        return [c["name"] for c in body["items"]], body["total"]

    assert await names() == (["A-one", "B-one", "C-three", "D-none", "E-empty"], 5)
    assert await names(with_products="true") == (["A-one", "B-one", "C-three"], 3)
    # Ties (A-one, B-one: 1 each) fall back to the name.
    assert await names(with_products="true", sort="products") == (["C-three", "A-one", "B-one"], 3)
    assert await names(sort="products", page_size="2", page="2") == (["B-one", "D-none"], 5)
    assert await names(with_products="true", sort="products", page_size="2", page="2") == (["B-one"], 3)
    assert (await client.get("/api/v1/categories", params={"sort": "price"})).status_code == 422
