"""Integration tests for SQLAlchemy repository with PostgreSQL."""

import os

import pytest

# Only run these tests if database connection is configured
pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DB_CONNECTION_STRING"),
    reason="Database connection not configured. Set TEST_DB_CONNECTION_STRING environment variable.",
)


@pytest.fixture(scope="module")
def db_engine():
    """Create database engine for tests."""
    from sqlalchemy import create_engine

    from invitation_core.adapters.repositories.sqlalchemy import create_tables

    connection_string = os.getenv("TEST_DB_CONNECTION_STRING")
    engine = create_engine(connection_string, echo=False)

    # Create tables
    create_tables(engine)

    yield engine

    # Cleanup
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Create a database session for each test."""
    from sqlalchemy.orm import Session

    from invitation_core.adapters.repositories.sqlalchemy import Base

    session = Session(db_engine)

    yield session

    # Rollback any changes
    session.rollback()

    # Clean up all data
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


@pytest.fixture
def repository(db_session):
    """Create SQLAlchemy repository."""
    from invitation_core.adapters.repositories.sqlalchemy import SQLAlchemyInvitationRepository

    return SQLAlchemyInvitationRepository(db_session)


# Import and run contract tests
from tests.contracts.test_repository_contract import RepositoryContractTests


class TestSQLAlchemyRepositoryIntegration(RepositoryContractTests):
    """Run contract tests against SQLAlchemy repository with real database."""

    pass
