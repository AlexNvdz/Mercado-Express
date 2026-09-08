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
