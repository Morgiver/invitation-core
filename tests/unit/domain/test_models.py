"""Unit tests for domain models."""

from datetime import datetime, timedelta

import pytest

from invitation_core.domain.exceptions import (
    InvitationAlreadyUsedError,
    InvitationExpiredError,
    InvitationLimitReachedError,
)
from invitation_core.domain.models import Invitation, InvitationStatus
from invitation_core.domain.value_objects import InvitationCode, UsageLimit


class TestInvitation:
    """Tests for Invitation entity."""

    def test_create_invitation(self) -> None:
        """Test creating a new invitation."""
        code = InvitationCode("WELCOME2024")
        invitation = Invitation.create(
            code=code,
            created_by="user123",
            expires_at=datetime.utcnow() + timedelta(days=7),
            usage_limit=UsageLimit(5),
            metadata={"source": "email_campaign"},
        )

        assert invitation.id is not None
        assert invitation.code == code
        assert invitation.created_by == "user123"
        assert invitation.status == InvitationStatus.ACTIVE
        assert invitation.usage_count == 0
        assert invitation.metadata["source"] == "email_campaign"

    def test_create_single_use_invitation_by_default(self) -> None:
        """Test that invitations are single-use by default."""
        invitation = Invitation.create(
            code=InvitationCode("WELCOME"),
            created_by="user123",
        )

        assert invitation.usage_limit.value == 1

    def test_invitation_is_valid_when_active(self) -> None:
        """Test that active invitation is valid."""
        invitation = Invitation.create(
            code=InvitationCode("WELCOME"),
            created_by="user123",
        )

        assert invitation.is_valid() is True

    def test_invitation_is_invalid_when_revoked(self) -> None:
        """Test that revoked invitation is not valid."""
        invitation = Invitation.create(
            code=InvitationCode("WELCOME"),
            created_by="user123",
        )
        invitation.revoke(revoked_by="admin", reason="Testing")

        assert invitation.is_valid() is False

    def test_invitation_is_invalid_when_expired(self) -> None:
        """Test that expired invitation is not valid."""
        past_time = datetime.utcnow() - timedelta(days=1)
        invitation = Invitation.create(
            code=InvitationCode("WELCOME"),
            created_by="user123",
            expires_at=past_time,
        )

        assert invitation.is_valid() is False
        assert invitation.is_expired() is True

    def test_invitation_is_invalid_when_limit_reached(self) -> None:
        """Test that invitation with reached limit is not valid."""
        invitation = Invitation.create(
            code=InvitationCode("WELCOME"),
            created_by="user123",
            usage_limit=UsageLimit(1),
        )
        invitation.use(used_by="user456")

        assert invitation.is_valid() is False
        assert invitation.is_limit_reached() is True

    def test_use_invitation_single_use(self) -> None:
        """Test using a single-use invitation."""
        invitation = Invitation.create(
            code=InvitationCode("WELCOME"),
            created_by="user123",
            usage_limit=UsageLimit(1),
        )

        invitation.use(used_by="user456")

        assert invitation.usage_count == 1
        assert invitation.used_by == ["user456"]
        assert invitation.status == InvitationStatus.USED

    def test_use_invitation_multi_use(self) -> None:
        """Test using a multi-use invitation."""
        invitation = Invitation.create(
            code=InvitationCode("WELCOME"),
            created_by="user123",
            usage_limit=UsageLimit(3),
        )

        invitation.use(used_by="user456")
        assert invitation.usage_count == 1
        assert invitation.status == InvitationStatus.ACTIVE

        invitation.use(used_by="user789")
        assert invitation.usage_count == 2
        assert invitation.status == InvitationStatus.ACTIVE

        invitation.use(used_by="user999")
        assert invitation.usage_count == 3
        assert invitation.status == InvitationStatus.USED

    def test_use_invitation_unlimited(self) -> None:
        """Test using an unlimited invitation."""
        invitation = Invitation.create(
            code=InvitationCode("WELCOME"),
            created_by="user123",
            usage_limit=UsageLimit(None),
        )

        for i in range(100):
            invitation.use(used_by=f"user{i}")

        assert invitation.usage_count == 100
        assert invitation.status == InvitationStatus.ACTIVE

    def test_use_expired_invitation_raises_error(self) -> None:
        """Test that using an expired invitation raises an error."""
        past_time = datetime.utcnow() - timedelta(days=1)
        invitation = Invitation.create(
            code=InvitationCode("WELCOME"),
            created_by="user123",
            expires_at=past_time,
        )

        with pytest.raises(InvitationExpiredError):
            invitation.use(used_by="user456")

        # Status should be updated to expired
        assert invitation.status == InvitationStatus.EXPIRED

    def test_use_invitation_after_limit_raises_error(self) -> None:
        """Test that using invitation after limit raises an error."""
        invitation = Invitation.create(
            code=InvitationCode("WELCOME"),
            created_by="user123",
            usage_limit=UsageLimit(1),
        )
        invitation.use(used_by="user456")

        # After single-use, status becomes USED, so it raises InvitationAlreadyUsedError
        with pytest.raises(InvitationAlreadyUsedError):
            invitation.use(used_by="user789")

    def test_use_revoked_invitation_raises_error(self) -> None:
        """Test that using a revoked invitation raises an error."""
        invitation = Invitation.create(
            code=InvitationCode("WELCOME"),
            created_by="user123",
        )
        invitation.revoke(revoked_by="admin", reason="Testing")

        with pytest.raises(InvitationAlreadyUsedError, match="revoked"):
            invitation.use(used_by="user456")

    def test_revoke_invitation(self) -> None:
        """Test revoking an invitation."""
        invitation = Invitation.create(
            code=InvitationCode("WELCOME"),
            created_by="user123",
        )

        revoke_time = datetime.utcnow()
        invitation.revoke(revoked_by="admin", reason="Testing", revoke_time=revoke_time)

        assert invitation.status == InvitationStatus.REVOKED
        assert invitation.revoked_by == "admin"
        assert invitation.revocation_reason == "Testing"
        assert invitation.revoked_at == revoke_time

    def test_revoke_already_revoked_invitation_is_idempotent(self) -> None:
        """Test that revoking an already revoked invitation doesn't error."""
        invitation = Invitation.create(
            code=InvitationCode("WELCOME"),
            created_by="user123",
        )

        invitation.revoke(revoked_by="admin1", reason="First")
        invitation.revoke(revoked_by="admin2", reason="Second")

        # Should keep first revocation
        assert invitation.revoked_by == "admin1"
        assert invitation.revocation_reason == "First"

    def test_remaining_uses_with_limit(self) -> None:
        """Test remaining_uses calculation with a limit."""
        invitation = Invitation.create(
            code=InvitationCode("WELCOME"),
            created_by="user123",
            usage_limit=UsageLimit(5),
        )

        assert invitation.remaining_uses() == 5

        invitation.use(used_by="user1")
        assert invitation.remaining_uses() == 4

        invitation.use(used_by="user2")
        invitation.use(used_by="user3")
        assert invitation.remaining_uses() == 2

    def test_remaining_uses_unlimited(self) -> None:
        """Test remaining_uses with unlimited invitation."""
        invitation = Invitation.create(
            code=InvitationCode("WELCOME"),
            created_by="user123",
            usage_limit=UsageLimit(None),
        )

        assert invitation.remaining_uses() is None

        for i in range(100):
            invitation.use(used_by=f"user{i}")

        assert invitation.remaining_uses() is None

    def test_remaining_uses_never_negative(self) -> None:
        """Test that remaining_uses never goes negative."""
        invitation = Invitation.create(
            code=InvitationCode("WELCOME"),
            created_by="user123",
            usage_limit=UsageLimit(1),
        )
        invitation.use(used_by="user1")

        assert invitation.remaining_uses() == 0
