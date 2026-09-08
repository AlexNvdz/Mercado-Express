from services import customers, mock_data


def test_get_profile():
    profile = customers.get_profile("any-token")
    assert profile["email"] == mock_data.MOCK_USER["email"]


def test_update_profile_merges_fields():
    result = customers.update_profile("any-token", full_name="Nuevo Nombre")
    assert result["full_name"] == "Nuevo Nombre"
    assert result["email"] == mock_data.MOCK_USER["email"]


def test_list_addresses():
    addresses = customers.list_addresses("any-token")
    assert len(addresses) >= 1
    assert {"line1", "city", "country"} <= addresses[0].keys()


def test_add_address_returns_created_address():
    payload = {"line1": "Cra 1 # 2-3", "city": "Medellín", "state": "Antioquia", "postal_code": "050001", "country": "CO", "is_default": False}
    created = customers.add_address("any-token", payload)
    assert created["line1"] == "Cra 1 # 2-3"
    assert "id" in created


def test_delete_address_does_not_raise():
    customers.delete_address("any-token", "00000000-0000-0000-0000-000000000601")


def test_added_address_is_retrievable_afterwards():
    payload = {"line1": "Cra 1 # 2-3", "city": "Medellín", "state": "Antioquia", "postal_code": "050001", "country": "CO", "is_default": False}
    created = customers.add_address("any-token", payload)
    addresses = customers.list_addresses("any-token")
    assert any(a["id"] == created["id"] for a in addresses)


def test_deleted_address_is_gone_afterwards():
    payload = {"line1": "temp", "city": "x", "state": "x", "postal_code": "x", "country": "CO", "is_default": False}
    created = customers.add_address("any-token", payload)
    customers.delete_address("any-token", created["id"])
    addresses = customers.list_addresses("any-token")
    assert not any(a["id"] == created["id"] for a in addresses)


def test_set_default_address_unsets_previous_default():
    default_id = mock_data.MOCK_ADDRESSES[0]["id"]
    new_address = customers.add_address(
        "any-token",
        {"line1": "new", "city": "x", "state": "x", "postal_code": "x", "country": "CO", "is_default": False},
    )

    customers.update_address("any-token", new_address["id"], {"is_default": True})

    addresses = {a["id"]: a for a in customers.list_addresses("any-token")}
    assert addresses[new_address["id"]]["is_default"] is True
    assert addresses[default_id]["is_default"] is False
