from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings, get_settings
from app.main import app


def _test_settings() -> Settings:
    return Settings(
        db_host="localhost",
        db_port=5432,
        db_name="test",
        db_user="test",
        db_password="test",
        model_store_path="/tmp/model_store",
        log_level="DEBUG",
    )


class MockConnection:
    """Mock asyncpg connection with configurable return values."""

    def __init__(self):
        self.fetchval = AsyncMock(return_value=1)
        self.fetchrow = AsyncMock(return_value=None)
        self.fetch = AsyncMock(return_value=[])


class MockPoolAcquire:
    """Mock the async context manager returned by pool.acquire()."""

    def __init__(self, conn: MockConnection):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


class MockPool:
    """Mock asyncpg pool."""

    def __init__(self):
        self.conn = MockConnection()
        self.close = AsyncMock()

    def acquire(self):
        return MockPoolAcquire(self.conn)


@pytest.fixture
def mock_pool():
    return MockPool()


@pytest.fixture
def test_app(mock_pool):
    app.dependency_overrides[get_settings] = _test_settings
    app.state.db_pool = mock_pool
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
