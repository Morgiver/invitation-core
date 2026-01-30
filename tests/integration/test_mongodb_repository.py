"""Integration tests for MongoDB repository."""

import os

import pytest

# Only run these tests if MongoDB connection is configured
pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_MONGO_CONNECTION_STRING"),
    reason="MongoDB connection not configured. Set TEST_MONGO_CONNECTION_STRING environment variable.",
)


@pytest.fixture(scope="module")
def mongo_client():
    """Create MongoDB client for tests."""
    from pymongo import MongoClient

    connection_string = os.getenv("TEST_MONGO_CONNECTION_STRING")
    client = MongoClient(connection_string)

    yield client

    # Cleanup
    client.close()


@pytest.fixture
def mongo_database(mongo_client):
    """Create MongoDB database for each test."""
    db_name = os.getenv("TEST_MONGO_DB_NAME", "test_invitation_core")
    database = mongo_client[db_name]

    yield database

    # Clean up collections
    database.invitations.drop()


@pytest.fixture
def repository(mongo_database):
    """Create MongoDB repository."""
    from invitation_core.adapters.repositories.mongodb import MongoDBInvitationRepository

    return MongoDBInvitationRepository(mongo_database)


# Import and run contract tests
from tests.contracts.test_repository_contract import RepositoryContractTests


class TestMongoDBRepositoryIntegration(RepositoryContractTests):
    """Run contract tests against MongoDB repository with real database."""

    pass
