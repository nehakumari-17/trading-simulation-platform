"""
conftest.py

Shared fixtures used across all test files.

Uses an in-memory SQLite database so tests never touch the real trading_sim.db.
Each test gets a fresh database — no leftover data between tests.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from backend.database import Base, get_db
from backend.main import app


# in-memory SQLite — fast and isolated, wiped after every test session
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    """Replaces the real DB session with a test session."""
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Creates all tables once before any test runs."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    """
    Provides an async HTTP test client for the FastAPI app.
    Overrides the DB dependency so tests use the in-memory database.
    Overrides the simulation engine so it doesn't try to load CSV files.
    """
    app.dependency_overrides[get_db] = override_get_db

    # patch the simulation engine so it doesn't start during tests
    from backend.simulation.engine import SimulationEngine
    from unittest.mock import AsyncMock, MagicMock

    mock_engine = MagicMock()
    mock_engine.get_current_price = MagicMock(return_value=1293.0)
    mock_engine.start = AsyncMock()
    mock_engine.stop  = AsyncMock()
    mock_engine.set_ws_manager = MagicMock()

    import backend.simulation.engine as engine_module
    original_engine = engine_module.sim_engine
    engine_module.sim_engine = mock_engine

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    engine_module.sim_engine = original_engine
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client):
    """
    Registers a test user and returns JWT auth headers.
    Use this in any test that needs a logged-in user.
    """
    await client.post("/api/auth/register", json={
        "username": "testuser",
        "email":    "test@example.com",
        "password": "password123",
    })

    login = await client.post("/api/auth/login", json={
        "email":    "test@example.com",
        "password": "password123",
    })

    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def second_auth_headers(client):
    """A second user — used for security tests (can't see other users' data)."""
    await client.post("/api/auth/register", json={
        "username": "otheruser",
        "email":    "other@example.com",
        "password": "password123",
    })
    login = await client.post("/api/auth/login", json={
        "email":    "other@example.com",
        "password": "password123",
    })
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
