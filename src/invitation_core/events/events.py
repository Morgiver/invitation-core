"""Domain events for invitation management."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class InvitationCreatedEvent:
    """Event published when an invitation is created."""

    invitation_id: str
    code: str
    created_by: str
    created_at: datetime
    expires_at: Optional[datetime]
    usage_limit: Optional[int]
    metadata: dict

    @property
    def event_name(self) -> str:
        """Event name for routing."""
        return "invitation.created"


@dataclass(frozen=True)
class InvitationUsedEvent:
    """Event published when an invitation is used."""

    invitation_id: str
    code: str
    used_by: str
    used_at: datetime
    usage_count: int
    remaining_uses: Optional[int]
    is_exhausted: bool

    @property
    def event_name(self) -> str:
        """Event name for routing."""
        return "invitation.used"


@dataclass(frozen=True)
class InvitationRevokedEvent:
    """Event published when an invitation is revoked."""

    invitation_id: str
    code: str
    revoked_by: str
    revoked_at: datetime
    reason: Optional[str]

    @property
    def event_name(self) -> str:
        """Event name for routing."""
        return "invitation.revoked"


@dataclass(frozen=True)
class InvitationExpiredEvent:
    """Event published when an invitation expires."""

    invitation_id: str
    code: str
    expired_at: datetime

    @property
    def event_name(self) -> str:
        """Event name for routing."""
        return "invitation.expired"


@dataclass(frozen=True)
class InvitationLimitReachedEvent:
    """Event published when an invitation reaches its usage limit."""

    invitation_id: str
    code: str
    usage_limit: int
    final_used_by: str
    reached_at: datetime

    @property
    def event_name(self) -> str:
        """Event name for routing."""
        return "invitation.limit_reached"
