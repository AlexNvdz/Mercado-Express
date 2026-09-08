import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_register_creates_customer(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "new-user@test.com", "password": "Passw0rd!", "full_name": "New User"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new-user@test.com"
    assert body["role"] == "customer"
    assert "hashed_password" not in body


async def test_register_duplicate_email_conflicts(client: AsyncClient) -> None:
    payload = {"email": "dupe@test.com", "password": "Passw0rd!", "full_name": "Dupe"}
    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


async def test_login_and_me(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login@test.com", "password": "Passw0rd!", "full_name": "Login User"},
    )
    login = await client.post(
        "/api/v1/auth/login", data={"username": "login@test.com", "password": "Passw0rd!"}
    )
    assert login.status_code == 200
    tokens = login.json()
    assert "access_token" in tokens and "refresh_token" in tokens

    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "login@test.com"


async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpw@test.com", "password": "Passw0rd!", "full_name": "User"},
    )
    resp = await client.post(
        "/api/v1/auth/login", data={"username": "wrongpw@test.com", "password": "bad-password"}
    )
    assert resp.status_code == 401


async def test_me_requires_authentication(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
