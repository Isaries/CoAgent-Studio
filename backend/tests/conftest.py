from typing import Any, AsyncGenerator, Dict, List, Optional
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.core.config import settings
from app.core.db import get_session
from app.core.llm_service import LLMResponse, LLMService
from app.core.socket_manager import manager
from app.main import app
from app.models.user import User, UserRole

# Use existing DB URL (assume local dev DB is fine for now with rollback)
TEST_DATABASE_URL = settings.async_database_url


@pytest.fixture(autouse=True)
async def mock_room_monitor():
    """
    Prevent the background RoomMonitor from running during tests.
    """
    with patch("app.core.room_monitor.RoomMonitor.start", new_callable=AsyncMock) as mock_start:
        with patch("app.core.room_monitor.RoomMonitor.stop", new_callable=AsyncMock) as mock_stop:
            yield mock_start


@pytest.fixture(autouse=True)
async def reset_socket_manager():
    """
    Reset the singleton Socket Manager state before and after each test.
    Prevents connection leakage between tests.
    """
    manager.active_connections = {}
    manager.background_tasks = set()
    yield
    manager.active_connections = {}
    manager.background_tasks = set()


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
async def setup_db_schema():
    """
    Session-scoped fixture to initializes the DB schema ONCE.
    This avoids the overhead of creating tables for every test.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    async with engine.begin() as conn:
        from sqlmodel import SQLModel

        await conn.run_sync(SQLModel.metadata.create_all)
    await engine.dispose()


@pytest.fixture()
async def db_engine(setup_db_schema):
    """
    Function-scoped engine to ensure it is attached to the current test's event loop.
    Depends on setup_db_schema to ensure tables exist.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    yield engine
    await engine.dispose()


@pytest.fixture()
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture that returns a SQLAlchemy session with a PRE-STARTED transaction.
    At the end of the test, the transaction is ROLLED BACK, so no data is persisted.
    """
    connection = await db_engine.connect()
    transaction = await connection.begin()

    session_factory = sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async_session = session_factory()

    yield async_session

    await async_session.close()
    await transaction.rollback()
    await connection.close()


@pytest.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Fixture that yields an HTTP client.
    It also overrides the 'get_session' dependency to use the test's rolling-back session.
    """

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
async def mock_superuser(db_session: AsyncSession) -> User:
    user = User(
        email="admin@example.com",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture()
async def mock_teacher(db_session: AsyncSession) -> User:
    user = User(
        email="teacher@example.com",
        role=UserRole.TEACHER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture()
async def superuser_client(client: AsyncClient, mock_superuser: User) -> AsyncClient:
    """
    Client authenticated as Super Admin via Dependency Override.
    """

    async def override_get_current_user():
        return mock_superuser

    app.dependency_overrides[deps.get_current_user] = override_get_current_user
    return client


@pytest.fixture()
async def teacher_client(client: AsyncClient, mock_teacher: User) -> AsyncClient:
    """
    Client authenticated as Teacher via Dependency Override.
    """

    async def override_get_current_user():
        return mock_teacher

    app.dependency_overrides[deps.get_current_user] = override_get_current_user
    return client


@pytest.fixture()
async def mock_student(db_session: AsyncSession) -> User:
    user = User(
        email="student@example.com",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture()
async def student_client(client: AsyncClient, mock_student: User) -> AsyncClient:
    """
    Client authenticated as Student via Dependency Override.
    """

    async def override_get_current_user():
        return mock_student

    app.dependency_overrides[deps.get_current_user] = override_get_current_user
    return client


# Smart Mock LLM Implementation
class MockLLMRegistry:
    """
    Singleton registry to hold expected responses for the Mock LLM.
    Tests can add responses to this registry, and the MockLLMService will consume them.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MockLLMRegistry, cls).__new__(cls)
            cls._instance.responses = []
            cls._instance.default_response = LLMResponse(content="Mock Default Response")
        return cls._instance

    def add_response(self, response: LLMResponse):
        """Queue a specific response to be returned next."""
        self.responses.append(response)

    def set_default(self, response: LLMResponse):
        """Set a fallback response if the queue is empty."""
        self.default_response = response

    def clear(self):
        """Clear all queued responses."""
        self.responses = []

    def get_next(self) -> LLMResponse:
        """Pop the next response from the queue, or return default."""
        if self.responses:
            return self.responses.pop(0)
        return self.default_response


class MockLLMService(LLMService):
    def __init__(self):
        self.registry = MockLLMRegistry()

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        # We could add logic here to match prompts to specific responses if needed,
        # but a simple queue is usually sufficient for linear test flows.
        return self.registry.get_next()


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    """
    Fixture that patches the LLMFactory to return our Smart Mock.
    Returns the registry instance so tests can configure expectations.
    """
    # Create the service (and implicit registry)
    mock_service = MockLLMService()
    registry = mock_service.registry

    # Ensure fresh state for each test
    registry.clear()

    # Patch the factory
    monkeypatch.setattr(
        "app.core.llm_service.LLMFactory.get_service", lambda provider: mock_service
    )

    return registry
