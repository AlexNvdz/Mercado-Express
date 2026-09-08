import pytest

from services import auth
from services.exceptions import ApiAuthenticationError


def test_login_success_returns_token_pair():
    result = auth.login("cliente.demo@mercadoexpress.test", "demo1234")
    assert result["access_token"]
    assert result["refresh_token"]
    assert result["token_type"] == "bearer"


def test_login_failure_raises_authentication_error():
    with pytest.raises(ApiAuthenticationError):
        auth.login("cliente.demo@mercadoexpress.test", "wrong-password")


def test_register_returns_created_customer():
    customer = auth.register("nueva@example.com", "supersecreta1", "Nueva Persona", "+57 1 000")
    assert customer["email"] == "nueva@example.com"
    assert customer["full_name"] == "Nueva Persona"


def test_get_current_user_with_token():
    user = auth.get_current_user("any-token")
    assert user["email"] == "cliente.demo@mercadoexpress.test"


def test_get_current_user_without_token():
    assert auth.get_current_user("") is None


def test_session_token_roundtrip(rf):
    request = rf.get("/")
    request.session = {}
    assert auth.get_access_token(request) is None
    assert auth.is_authenticated(request) is False

    auth.save_tokens(request, access_token="acc-123", refresh_token="ref-456")
    assert auth.get_access_token(request) == "acc-123"
    assert auth.get_refresh_token(request) == "ref-456"
    assert auth.is_authenticated(request) is True

    auth.clear_tokens(request)
    assert auth.get_access_token(request) is None
    assert auth.get_refresh_token(request) is None
    assert auth.is_authenticated(request) is False
