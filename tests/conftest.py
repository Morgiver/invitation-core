"""Shared fixtures for invitation tests."""

from datetime import datetime, timedelta

import pytest

from invitation_core.adapters.event_buses.memory import InMemoryEventBus
from invitation_core.adapters.repositories.memory import (
    InMemoryInvitationRepository,
)
from invitation_core.domain.models import Invitation
from invitation_core.domain.services import InvitationService
from invitation_core.domain.value_objects import InvitationCode, UsageLimit


@pytest.fixture
def repository() -> InMemoryInvitationRepository:
    """Create a fresh in-memory repository."""
    return InMemoryInvitationRepository()


@pytest.fixture
def event_bus() -> InMemoryEventBus:
    """Create a fresh in-memory event bus."""
    return InMemoryEventBus()


@pytest.fixture
def service(repository: InMemoryInvitationRepository, event_bus: InMemoryEventBus) -> InvitationService:
    """Create a fully configured invitation service."""
    return InvitationService(repository=repository, event_bus=event_bus)


@pytest.fixture
def valid_invitation() -> Invitation:
    """Create a valid active invitation."""
    return Invitation.create(
        code=InvitationCode("TESTCODE123"),
        created_by="user123",
        expires_at=datetime.utcnow() + timedelta(days=7),
        usage_limit=UsageLimit(5),
        metadata={"source": "test"},
    )


@pytest.fixture
def expired_invitation() -> Invitation:
    """Create an expired invitation."""
    return Invitation.create(
        code=InvitationCode("EXPIRED123"),
        created_by="user123",
        expires_at=datetime.utcnow() - timedelta(days=1),
        usage_limit=UsageLimit(5),
    )


@pytest.fixture
def single_use_invitation() -> Invitation:
    """Create a single-use invitation."""
    return Invitation.create(
        code=InvitationCode("SINGLE123"),
        created_by="user123",
        usage_limit=UsageLimit(1),
    )


@pytest.fixture
def unlimited_invitation() -> Invitation:
    """Create an unlimited invitation."""
    return Invitation.create(
        code=InvitationCode("UNLIMITED123"),
        created_by="user123",
        usage_limit=UsageLimit(None),
    )


@pytest.fixture
def invitation_factory():
    """Factory for creating test invitations with custom parameters."""

    def _create(
        code: str = "TESTCODE",
        created_by: str = "user123",
        expires_at: datetime = None,
        usage_limit: int = 1,
        **kwargs,
    ) -> Invitation:
        return Invitation.create(
            code=InvitationCode(code),
            created_by=created_by,
            expires_at=expires_at,
            usage_limit=UsageLimit(usage_limit),
            metadata=kwargs.get("metadata", {}),
        )

    return _create


# ============================================================================
# Database Fixtures (SQLAlchemy)
# ============================================================================

@pytest.fixture(scope='function')
def db_engine():
    """Create SQLAlchemy engine for testing."""
    import os
    conn_string = os.environ.get('TEST_DB_CONNECTION_STRING')
    db_type = os.environ.get('TEST_DB_TYPE', 'memory')

    if not conn_string or db_type != 'postgresql':
        pytest.skip("PostgreSQL database not configured. Set TEST_DB_TYPE=postgresql and TEST_DB_CONNECTION_STRING")

    from sqlalchemy import create_engine
    from invitation_core.adapters.repositories.sqlalchemy import Base

    engine = create_engine(conn_string, echo=False)

    # Create tables
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup tables after test
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope='function')
def db_session(db_engine):
    """Create SQLAlchemy session for testing."""
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()

    yield session

    session.rollback()
    session.close()


# ============================================================================
# Database Fixtures (MongoDB)
# ============================================================================

@pytest.fixture(scope='function')
def mongo_client():
    """Create MongoDB client for testing."""
    import os
    conn_string = os.environ.get('TEST_MONGO_CONNECTION_STRING')
    db_type = os.environ.get('TEST_DB_TYPE', 'memory')

    if not conn_string or db_type != 'mongodb':
        pytest.skip("MongoDB database not configured. Set TEST_DB_TYPE=mongodb and TEST_MONGO_CONNECTION_STRING")

    from pymongo import MongoClient

    client = MongoClient(conn_string)

    yield client

    client.close()


@pytest.fixture(scope='function')
def mongo_db(mongo_client):
    """Create MongoDB database for testing."""
    import os
    db_name = os.environ.get('TEST_MONGO_DB_NAME', 'test_invitation_core')
    db = mongo_client[db_name]

    yield db

    # Cleanup all collections after test
    for collection_name in db.list_collection_names():
        db[collection_name].delete_many({})


# ============================================================================
# Pytest Hooks
# ============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "adapter(name): mark test to run only for specific adapter"
    )


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--adapter",
        action="store",
        default=None,
        help="Run tests only for specific adapter (sqlalchemy, mongodb, memory)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip tests based on adapter filter."""
    adapter_filter = config.getoption("--adapter", default=None)

    if not adapter_filter:
        return

    for item in items:
        # Check if test class name indicates specific adapter
        if hasattr(item, 'cls') and item.cls:
            class_name = item.cls.__name__

            # Map class names to adapters
            if 'SQLAlchemy' in class_name and adapter_filter != 'sqlalchemy':
                item.add_marker(pytest.mark.skip(reason=f"Skipping SQLAlchemy tests (adapter={adapter_filter})"))
            elif 'MongoDB' in class_name and adapter_filter != 'mongodb':
                item.add_marker(pytest.mark.skip(reason=f"Skipping MongoDB tests (adapter={adapter_filter})"))
            elif 'InMemory' in class_name and adapter_filter not in ['memory', 'inmemory']:
                item.add_marker(pytest.mark.skip(reason=f"Skipping InMemory tests (adapter={adapter_filter})"))
