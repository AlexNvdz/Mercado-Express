"""Test fixtures.

Tests run against a real PostgreSQL database (a dedicated `*_test` database
on the same server configured via .env / docker-compose) so native types
(UUID, ENUM) and constraints behave exactly as in production. Schema is
created once per session via `Base.metadata.create_all` (fast, no need to
run through Alembic for tests); each test then runs inside a transaction
that's rolled back afterwards, so tests never see each other's data.

Authentication in tests goes through the real JWT flow (real access tokens,
real `get_current_user` dependency) rather than overriding the dependency,
so `customer_client` and `admin_client` are independent AsyncClient
instances and can safely be used together in the same test.
"""

import uuid
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.asyncio_compat import apply_windows_event_loop_policy
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.enums import UserRole
from app.models.user import User

apply_windows_event_loop_policy()

TEST_DB_URL = settings.sqlalchemy_database_uri.rsplit("/", 1)[0] + "/mercadoexpress_test"

test_engine = create_async_engine(TEST_DB_URL, pool_pre_ping=True)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_schema() -> AsyncGenerator[None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    connection = await test_engine.connect()
    trans = await connection.begin()
    session = AsyncSession(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )

    async def _override_get_db() -> AsyncGenerator[AsyncSession]:
        yield session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield session
    finally:
        app.dependency_overrides.pop(get_db, None)
        await session.close()
        await trans.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _create_user(
    db_session: AsyncSession, *, email: str, role: UserRole, password: str = "Passw0rd!"
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name="Test User",
        role=role,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def customer_user(db_session: AsyncSession) -> User:
    email = f"customer-{uuid.uuid4().hex[:8]}@test.com"
    return await _create_user(db_session, email=email, role=UserRole.CUSTOMER)


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    email = f"admin-{uuid.uuid4().hex[:8]}@test.com"
    return await _create_user(db_session, email=email, role=UserRole.ADMIN)


def _authed_client(user: User) -> AsyncClient:
    token = create_access_token(str(user.id), user.role.value)
    transport = ASGITransport(app=app)
    return AsyncClient(
        transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {token}"}
    )


@pytest_asyncio.fixture
async def customer_client(
    db_session: AsyncSession, customer_user: User
) -> AsyncGenerator[AsyncClient]:
    async with _authed_client(customer_user) as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_client(db_session: AsyncSession, admin_user: User) -> AsyncGenerator[AsyncClient]:
    async with _authed_client(admin_user) as ac:
        yield ac
