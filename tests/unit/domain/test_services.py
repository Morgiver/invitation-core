"""Unit tests for domain services."""

from datetime import datetime, timedelta

import pytest

from invitation_core.domain.exceptions import (
    InvitationAlreadyExistsError,
    InvitationAlreadyUsedError,
    InvitationExpiredError,
    InvitationNotFoundError,
)
from invitation_core.domain.models import InvitationStatus
from invitation_core.domain.services import InvitationService
from invitation_core.dto.requests import (
    CreateInvitationRequest,
    RevokeInvitationRequest,
    UseInvitationRequest,
    ValidateInvitationRequest,
)
from invitation_core.events import (
    InvitationCreatedEvent,
    InvitationLimitReachedEvent,
    InvitationRevokedEvent,
    InvitationUsedEvent,
)


class TestInvitationService:
    """Tests for InvitationService."""

    def test_create_invitation_success(self, service, event_bus):
        """Test successful invitation creation."""
        request = CreateInvitationRequest(
            code="WELCOME123",
            created_by="admin",
            usage_limit=5,
            metadata={"source": "campaign"},
        )

        result = service.create_invitation(request)

        assert result.code == "WELCOME123"
        assert result.created_by == "admin"
        assert result.status == "active"
        assert result.usage_limit == 5
        assert result.usage_count == 0
        assert result.metadata == {"source": "campaign"}

        # Verify event was published
        events = event_bus.get_published_events()
        assert len(events) == 1
        assert isinstance(events[0], InvitationCreatedEvent)
        assert events[0].code == "WELCOME123"

    def test_create_invitation_with_expiration(self, service):
        """Test creating invitation with expiration date."""
        expires_at = datetime.utcnow() + timedelta(days=7)
        request = CreateInvitationRequest(
            code="EXPIRES123", created_by="admin", expires_at=expires_at
        )

        result = service.create_invitation(request)

        assert result.expires_at == expires_at

    def test_create_invitation_duplicate_code_raises_error(self, service):
        """Test that creating invitation with existing code raises error."""
        request1 = CreateInvitationRequest(code="DUPLICATE", created_by="admin")
        service.create_invitation(request1)

        request2 = CreateInvitationRequest(code="DUPLICATE", created_by="admin2")
        with pytest.raises(InvitationAlreadyExistsError, match="DUPLICATE"):
            service.create_invitation(request2)

    def test_create_invitation_case_insensitive_duplicate(self, service):
        """Test that code comparison is case-insensitive."""
        request1 = CreateInvitationRequest(code="TESTCODE", created_by="admin")
        service.create_invitation(request1)

        request2 = CreateInvitationRequest(code="testcode", created_by="admin2")
        with pytest.raises(InvitationAlreadyExistsError):
            service.create_invitation(request2)

    def test_use_invitation_success(self, service, event_bus):
        """Test successful invitation usage."""
        # Create invitation
        create_req = CreateInvitationRequest(code="USE123", created_by="admin", usage_limit=5)
        service.create_invitation(create_req)
        event_bus.clear()

        # Use invitation
        use_req = UseInvitationRequest(code="USE123", used_by="user1@example.com")
        result = service.use_invitation(use_req)

        assert result.code == "USE123"
        assert result.used_by == "user1@example.com"
        assert result.usage_count == 1
        assert result.remaining_uses == 4
        assert result.is_exhausted is False

        # Verify event was published
        events = event_bus.get_published_events()
        assert len(events) == 1
        assert isinstance(events[0], InvitationUsedEvent)
        assert events[0].used_by == "user1@example.com"

    def test_use_invitation_multiple_times(self, service):
        """Test using multi-use invitation multiple times."""
        # Create multi-use invitation
        create_req = CreateInvitationRequest(code="MULTI123", created_by="admin", usage_limit=3)
        service.create_invitation(create_req)

        # Use it 3 times
        for i in range(1, 4):
            use_req = UseInvitationRequest(code="MULTI123", used_by=f"user{i}@example.com")
            result = service.use_invitation(use_req)
            assert result.usage_count == i
            assert result.remaining_uses == 3 - i

        # Last usage should mark as exhausted
        assert result.is_exhausted is True

    def test_use_invitation_not_found_raises_error(self, service):
        """Test using non-existent invitation raises error."""
        use_req = UseInvitationRequest(code="NOTFOUND", used_by="user@example.com")

        with pytest.raises(InvitationNotFoundError, match="NOTFOUND"):
            service.use_invitation(use_req)

    def test_use_expired_invitation_raises_error(self, service):
        """Test using expired invitation raises error."""
        # Create short-lived invitation
        expires_at = datetime.utcnow() + timedelta(seconds=1)
        create_req = CreateInvitationRequest(
            code="SHORTLIVED", created_by="admin", expires_at=expires_at
        )
        service.create_invitation(create_req)

        # Wait for expiration
        import time
        time.sleep(2)

        # Try to use it
        use_req = UseInvitationRequest(code="SHORTLIVED", used_by="user@example.com")
        with pytest.raises(InvitationExpiredError):
            service.use_invitation(use_req)

    def test_use_exhausted_invitation_raises_error(self, service):
        """Test using exhausted invitation raises error."""
        # Create single-use invitation
        create_req = CreateInvitationRequest(code="SINGLE", created_by="admin", usage_limit=1)
        service.create_invitation(create_req)

        # Use it once
        use_req1 = UseInvitationRequest(code="SINGLE", used_by="user1@example.com")
        service.use_invitation(use_req1)

        # Try to use again
        use_req2 = UseInvitationRequest(code="SINGLE", used_by="user2@example.com")
        with pytest.raises(InvitationAlreadyUsedError):
            service.use_invitation(use_req2)

    def test_use_invitation_publishes_limit_reached_event(self, service, event_bus):
        """Test that limit reached event is published."""
        # Create single-use invitation
        create_req = CreateInvitationRequest(code="SINGLE", created_by="admin", usage_limit=1)
        service.create_invitation(create_req)
        event_bus.clear()

        # Use it
        use_req = UseInvitationRequest(code="SINGLE", used_by="user@example.com")
        service.use_invitation(use_req)

        # Verify both events were published
        events = event_bus.get_published_events()
        assert len(events) == 2
        assert isinstance(events[0], InvitationUsedEvent)
        assert isinstance(events[1], InvitationLimitReachedEvent)
        assert events[1].usage_limit == 1

    def test_validate_invitation_valid(self, service):
        """Test validating a valid invitation."""
        # Create invitation
        create_req = CreateInvitationRequest(code="VALID123", created_by="admin", usage_limit=5)
        service.create_invitation(create_req)

        # Validate it
        validate_req = ValidateInvitationRequest(code="VALID123")
        result = service.validate_invitation(validate_req)

        assert result.is_valid is True
        assert result.code == "VALID123"
        assert result.status == "active"
        assert result.remaining_uses == 5
        assert result.reason is None

    def test_validate_invitation_not_found(self, service):
        """Test validating non-existent invitation."""
        validate_req = ValidateInvitationRequest(code="NOTFOUND")
        result = service.validate_invitation(validate_req)

        assert result.is_valid is False
        assert result.code == "NOTFOUND"
        assert result.status is None
        assert result.reason == "Invitation not found"

    def test_validate_invitation_expired(self, service):
        """Test validating expired invitation."""
        # Create short-lived invitation
        expires_at = datetime.utcnow() + timedelta(seconds=1)
        create_req = CreateInvitationRequest(
            code="EXPIRED123", created_by="admin", expires_at=expires_at
        )
        service.create_invitation(create_req)

        # Wait for expiration
        import time
        time.sleep(2)

        # Validate it
        validate_req = ValidateInvitationRequest(code="EXPIRED123")
        result = service.validate_invitation(validate_req)

        assert result.is_valid is False
        assert result.status == "active"
        assert result.reason == "Invitation has expired"

    def test_validate_invitation_revoked(self, service):
        """Test validating revoked invitation."""
        # Create and revoke invitation
        create_req = CreateInvitationRequest(code="REVOKED123", created_by="admin")
        invitation = service.create_invitation(create_req)

        revoke_req = RevokeInvitationRequest(
            invitation_id=invitation.id, revoked_by="admin", reason="Test"
        )
        service.revoke_invitation(revoke_req)

        # Validate it
        validate_req = ValidateInvitationRequest(code="REVOKED123")
        result = service.validate_invitation(validate_req)

        assert result.is_valid is False
        assert result.status == "revoked"
        assert result.reason == "Invitation is revoked"

    def test_revoke_invitation_success(self, service, event_bus):
        """Test successful invitation revocation."""
        # Create invitation
        create_req = CreateInvitationRequest(code="REVOKE123", created_by="admin")
        invitation = service.create_invitation(create_req)
        event_bus.clear()

        # Revoke it
        revoke_req = RevokeInvitationRequest(
            invitation_id=invitation.id, revoked_by="admin", reason="Test revocation"
        )
        result = service.revoke_invitation(revoke_req)

        assert result.status == "revoked"
        assert result.revoked_by == "admin"
        assert result.revocation_reason == "Test revocation"

        # Verify event was published
        events = event_bus.get_published_events()
        assert len(events) == 1
        assert isinstance(events[0], InvitationRevokedEvent)
        assert events[0].reason == "Test revocation"

    def test_revoke_invitation_not_found_raises_error(self, service):
        """Test revoking non-existent invitation raises error."""
        revoke_req = RevokeInvitationRequest(
            invitation_id="nonexistent", revoked_by="admin", reason="Test"
        )

        with pytest.raises(InvitationNotFoundError):
            service.revoke_invitation(revoke_req)

    def test_get_invitation_by_id_success(self, service):
        """Test getting invitation by ID."""
        # Create invitation
        create_req = CreateInvitationRequest(code="GET123", created_by="admin")
        created = service.create_invitation(create_req)

        # Get it by ID
        result = service.get_invitation_by_id(created.id)

        assert result.id == created.id
        assert result.code == "GET123"

    def test_get_invitation_by_id_not_found_raises_error(self, service):
        """Test getting non-existent invitation raises error."""
        with pytest.raises(InvitationNotFoundError):
            service.get_invitation_by_id("nonexistent")

    def test_get_invitation_by_code_success(self, service):
        """Test getting invitation by code."""
        # Create invitation
        create_req = CreateInvitationRequest(code="GETCODE123", created_by="admin")
        service.create_invitation(create_req)

        # Get it by code
        result = service.get_invitation_by_code("GETCODE123")

        assert result.code == "GETCODE123"

    def test_get_invitation_by_code_case_insensitive(self, service):
        """Test getting invitation by code is case-insensitive."""
        create_req = CreateInvitationRequest(code="LOWERCASE", created_by="admin")
        service.create_invitation(create_req)

        result = service.get_invitation_by_code("lowercase")
        assert result.code == "LOWERCASE"

    def test_get_invitation_by_code_not_found_raises_error(self, service):
        """Test getting non-existent invitation by code raises error."""
        with pytest.raises(InvitationNotFoundError):
            service.get_invitation_by_code("NOTFOUND")

    def test_get_invitations_by_creator(self, service):
        """Test getting all invitations by creator."""
        # Create multiple invitations
        for i in range(3):
            create_req = CreateInvitationRequest(code=f"ADMIN{i}XXX", created_by="admin")
            service.create_invitation(create_req)

        # Create invitation by different user
        create_req = CreateInvitationRequest(code="USER1XX", created_by="user1")
        service.create_invitation(create_req)

        # Get admin's invitations
        results = service.get_invitations_by_creator("admin")

        assert len(results) == 3
        assert all(inv.created_by == "admin" for inv in results)
        assert {inv.code for inv in results} == {"ADMIN0XXX", "ADMIN1XXX", "ADMIN2XXX"}

    def test_get_invitations_by_creator_empty(self, service):
        """Test getting invitations for user with none."""
        results = service.get_invitations_by_creator("nobody")
        assert results == []

    def test_get_invitation_stats(self, service):
        """Test getting invitation statistics."""
        # Create invitations with different statuses
        # Active
        create_req1 = CreateInvitationRequest(code="ACTIVE1X", created_by="admin")
        service.create_invitation(create_req1)

        # Used (exhausted)
        create_req2 = CreateInvitationRequest(code="USED1XXX", created_by="admin", usage_limit=1)
        inv2 = service.create_invitation(create_req2)
        use_req = UseInvitationRequest(code="USED1XXX", used_by="user@example.com")
        service.use_invitation(use_req)

        # Revoked
        create_req3 = CreateInvitationRequest(code="REVOKED1", created_by="admin")
        inv3 = service.create_invitation(create_req3)
        revoke_req = RevokeInvitationRequest(
            invitation_id=inv3.id, revoked_by="admin", reason="Test"
        )
        service.revoke_invitation(revoke_req)

        # Get stats
        stats = service.get_invitation_stats()

        assert stats.total == 3
        assert stats.active == 1
        assert stats.used == 1
        assert stats.revoked == 1
        assert stats.expired == 0

    def test_service_without_event_bus(self, repository):
        """Test that service works without event bus."""
        service = InvitationService(repository, event_bus=None)

        # Should work normally
        create_req = CreateInvitationRequest(code="NOEVENTS", created_by="admin")
        result = service.create_invitation(create_req)

        assert result.code == "NOEVENTS"
