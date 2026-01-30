"""Contract tests for repository implementations.

All repository implementations must pass these tests to ensure they
properly implement the IInvitationRepository interface.
"""

from datetime import datetime, timedelta

import pytest

from invitation_core.domain.exceptions import InvitationAlreadyExistsError
from invitation_core.domain.models import Invitation, InvitationStatus
from invitation_core.domain.value_objects import InvitationCode, UsageLimit


class RepositoryContractTests:
    """Base contract tests that all repository implementations must pass."""

    @pytest.fixture
    def repository(self):
        """Subclasses must provide a repository implementation."""
        raise NotImplementedError("Subclasses must implement repository fixture")

    def test_save_and_find_by_id(self, repository):
        """Test saving and finding an invitation by ID."""
        invitation = Invitation.create(
            code=InvitationCode("TEST123"),
            created_by="user123",
            usage_limit=UsageLimit(5),
        )

        # Save
        saved = repository.save(invitation)
        assert saved.id == invitation.id

        # Find by ID
        found = repository.find_by_id(invitation.id)
        assert found is not None
        assert found.id == invitation.id
        assert found.code == invitation.code
        assert found.created_by == invitation.created_by

    def test_find_by_id_not_found_returns_none(self, repository):
        """Test finding non-existent invitation returns None."""
        result = repository.find_by_id("nonexistent")
        assert result is None

    def test_save_and_find_by_code(self, repository):
        """Test saving and finding an invitation by code."""
        invitation = Invitation.create(
            code=InvitationCode("FINDME"),
            created_by="user123",
        )

        repository.save(invitation)

        found = repository.find_by_code(InvitationCode("FINDME"))
        assert found is not None
        assert found.code == InvitationCode("FINDME")

    def test_find_by_code_case_insensitive(self, repository):
        """Test finding by code is case-insensitive."""
        invitation = Invitation.create(
            code=InvitationCode("UPPERCASE"),
            created_by="user123",
        )

        repository.save(invitation)

        # Should find with lowercase
        found = repository.find_by_code(InvitationCode("uppercase"))
        assert found is not None
        assert found.code == InvitationCode("UPPERCASE")

    def test_find_by_code_not_found_returns_none(self, repository):
        """Test finding non-existent code returns None."""
        result = repository.find_by_code(InvitationCode("NOTFOUND"))
        assert result is None

    def test_exists_by_code(self, repository):
        """Test checking if code exists."""
        invitation = Invitation.create(
            code=InvitationCode("EXISTS"),
            created_by="user123",
        )

        repository.save(invitation)

        assert repository.exists_by_code(InvitationCode("EXISTS")) is True
        assert repository.exists_by_code(InvitationCode("NOTEXISTS")) is False

    def test_exists_by_code_case_insensitive(self, repository):
        """Test exists check is case-insensitive."""
        invitation = Invitation.create(
            code=InvitationCode("TESTCODE"),
            created_by="user123",
        )

        repository.save(invitation)

        assert repository.exists_by_code(InvitationCode("testcode")) is True

    def test_save_duplicate_code_raises_error(self, repository):
        """Test saving duplicate code raises error."""
        inv1 = Invitation.create(
            code=InvitationCode("DUPLICATE"),
            created_by="user1",
        )
        repository.save(inv1)

        inv2 = Invitation.create(
            code=InvitationCode("DUPLICATE"),
            created_by="user2",
        )

        with pytest.raises(InvitationAlreadyExistsError):
            repository.save(inv2)

    def test_update_existing_invitation(self, repository):
        """Test updating an existing invitation."""
        invitation = Invitation.create(
            code=InvitationCode("UPDATE"),
            created_by="user123",
            usage_limit=UsageLimit(5),
        )

        repository.save(invitation)

        # Use the invitation
        invitation.use(used_by="user456")

        # Update
        repository.save(invitation)

        # Verify update
        found = repository.find_by_id(invitation.id)
        assert found.usage_count == 1
        assert found.used_by == ["user456"]

    def test_find_by_created_by(self, repository):
        """Test finding invitations by creator."""
        # Create invitations by different users
        inv1 = Invitation.create(code=InvitationCode("USER1A"), created_by="user1")
        inv2 = Invitation.create(code=InvitationCode("USER1B"), created_by="user1")
        inv3 = Invitation.create(code=InvitationCode("USER2A"), created_by="user2")

        repository.save(inv1)
        repository.save(inv2)
        repository.save(inv3)

        # Find user1's invitations
        results = repository.find_by_created_by("user1")
        assert len(results) == 2
        assert all(inv.created_by == "user1" for inv in results)

    def test_find_by_created_by_returns_empty_list(self, repository):
        """Test finding by non-existent creator returns empty list."""
        results = repository.find_by_created_by("nobody")
        assert results == []

    def test_find_by_status(self, repository):
        """Test finding invitations by status."""
        # Create active invitation
        active = Invitation.create(code=InvitationCode("ACTIVE123"), created_by="user1")
        repository.save(active)

        # Create and exhaust invitation
        used = Invitation.create(
            code=InvitationCode("USED123"), created_by="user1", usage_limit=UsageLimit(1)
        )
        used.use(used_by="user2")
        repository.save(used)

        # Create and revoke invitation
        revoked = Invitation.create(code=InvitationCode("REVOKED"), created_by="user1")
        revoked.revoke(revoked_by="admin", reason="Test")
        repository.save(revoked)

        # Test finding by status
        active_results = repository.find_by_status(InvitationStatus.ACTIVE)
        assert len(active_results) == 1
        assert active_results[0].status == InvitationStatus.ACTIVE

        used_results = repository.find_by_status(InvitationStatus.USED)
        assert len(used_results) == 1
        assert used_results[0].status == InvitationStatus.USED

        revoked_results = repository.find_by_status(InvitationStatus.REVOKED)
        assert len(revoked_results) == 1
        assert revoked_results[0].status == InvitationStatus.REVOKED

    def test_find_expired(self, repository):
        """Test finding expired invitations."""
        # Create expired invitation
        past = datetime.utcnow() - timedelta(days=1)
        expired = Invitation.create(
            code=InvitationCode("EXPIRED"),
            created_by="user1",
            expires_at=past,
        )
        repository.save(expired)

        # Create active invitation
        future = datetime.utcnow() + timedelta(days=1)
        active = Invitation.create(
            code=InvitationCode("ACTIVE123"),
            created_by="user1",
            expires_at=future,
        )
        repository.save(active)

        # Find expired
        results = repository.find_expired()
        assert len(results) == 1
        assert results[0].code == InvitationCode("EXPIRED")

    def test_delete(self, repository):
        """Test deleting an invitation."""
        invitation = Invitation.create(
            code=InvitationCode("DELETE"),
            created_by="user1",
        )
        repository.save(invitation)

        # Delete
        result = repository.delete(invitation.id)
        assert result is True

        # Verify deleted
        found = repository.find_by_id(invitation.id)
        assert found is None

    def test_delete_nonexistent_returns_false(self, repository):
        """Test deleting non-existent invitation returns False."""
        result = repository.delete("nonexistent")
        assert result is False

    def test_count_by_status(self, repository):
        """Test counting invitations by status."""
        # Create multiple invitations with different statuses
        for i in range(3):
            inv = Invitation.create(
                code=InvitationCode(f"ACTIVE{i}00"),
                created_by="user1",
            )
            repository.save(inv)

        for i in range(2):
            inv = Invitation.create(
                code=InvitationCode(f"USED{i}000"),
                created_by="user1",
                usage_limit=UsageLimit(1),
            )
            inv.use(used_by="user2")
            repository.save(inv)

        # Count
        active_count = repository.count_by_status(InvitationStatus.ACTIVE)
        used_count = repository.count_by_status(InvitationStatus.USED)
        revoked_count = repository.count_by_status(InvitationStatus.REVOKED)

        assert active_count == 3
        assert used_count == 2
        assert revoked_count == 0

    def test_save_preserves_all_fields(self, repository):
        """Test that saving preserves all fields correctly."""
        metadata = {"campaign": "winter2024", "discount": 20}
        expires_at = datetime.utcnow() + timedelta(days=30)

        invitation = Invitation.create(
            code=InvitationCode("FULL123"),
            created_by="admin",
            expires_at=expires_at,
            usage_limit=UsageLimit(10),
            metadata=metadata,
        )

        repository.save(invitation)

        found = repository.find_by_id(invitation.id)
        assert found.code == InvitationCode("FULL123")
        assert found.created_by == "admin"
        # MongoDB stores datetimes with millisecond precision, allow slight difference
        assert abs((found.expires_at - expires_at).total_seconds()) < 0.001
        assert found.usage_limit.value == 10
        assert found.metadata == metadata
        assert found.usage_count == 0
        assert found.used_by == []
        assert found.status == InvitationStatus.ACTIVE


class TestInMemoryRepository(RepositoryContractTests):
    """Contract tests for in-memory repository."""

    @pytest.fixture
    def repository(self):
        from invitation_core.adapters.repositories.memory import InMemoryInvitationRepository

        return InMemoryInvitationRepository()


class TestSQLAlchemyRepository(RepositoryContractTests):
    """Contract tests for SQLAlchemy repository."""

    @pytest.fixture
    def repository(self, db_session):
        from invitation_core.adapters.repositories.sqlalchemy import SQLAlchemyInvitationRepository

        return SQLAlchemyInvitationRepository(db_session)


class TestMongoDBRepository(RepositoryContractTests):
    """Contract tests for MongoDB repository."""

    @pytest.fixture
    def repository(self, mongo_db):
        from invitation_core.adapters.repositories.mongodb import MongoDBInvitationRepository

        return MongoDBInvitationRepository(mongo_db)
