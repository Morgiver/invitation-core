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
