"""Domain models for invitation management."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from invitation_core.domain.exceptions import (
    InvitationAlreadyUsedError,
    InvitationExpiredError,
    InvitationLimitReachedError,
)
from invitation_core.domain.value_objects import InvitationCode, UsageLimit

logger = logging.getLogger(__name__)


class InvitationStatus(str, Enum):
    """Status of an invitation."""

    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class Invitation:
    """Invitation entity.

    Represents an invitation code that can be used for user registration.

    Business rules:
    - Each invitation has a unique code
    - Can have an expiration date
    - Can have a usage limit (single-use, multi-use, or unlimited)
    - Tracks who created it and when
    - Tracks who used it and when
    - Can be revoked at any time
    """

    id: str
    code: InvitationCode
    created_by: str
    created_at: datetime
    status: InvitationStatus = InvitationStatus.ACTIVE
    expires_at: Optional[datetime] = None
    usage_limit: UsageLimit = field(default_factory=lambda: UsageLimit(1))
    usage_count: int = 0
    used_by: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None
    revocation_reason: Optional[str] = None

    @staticmethod
    def create(
        code: InvitationCode,
        created_by: str,
        expires_at: Optional[datetime] = None,
        usage_limit: Optional[UsageLimit] = None,
        metadata: Optional[dict] = None,
    ) -> "Invitation":
        """Factory method to create a new invitation.

        Args:
            code: The invitation code
            created_by: User ID who created this invitation
            expires_at: Optional expiration datetime
            usage_limit: Optional usage limit (defaults to single-use)
            metadata: Optional metadata dictionary

        Returns:
            New Invitation instance
        """
        logger.debug(f"Creating new invitation with code: {code}")

        return Invitation(
            id=str(uuid4()),
            code=code,
            created_by=created_by,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            usage_limit=usage_limit or UsageLimit(1),
            metadata=metadata or {},
        )

    def is_valid(self, check_time: Optional[datetime] = None) -> bool:
        """Check if invitation is valid for use.

        Args:
            check_time: Time to check against (defaults to now)

        Returns:
            True if invitation can be used
        """
        if self.status != InvitationStatus.ACTIVE:
            return False

        if self.is_expired(check_time):
            return False

        if self.is_limit_reached():
            return False

        return True

    def is_expired(self, check_time: Optional[datetime] = None) -> bool:
        """Check if invitation is expired.

        Args:
            check_time: Time to check against (defaults to now)

        Returns:
            True if invitation is expired
        """
        if self.expires_at is None:
            return False

        current_time = check_time or datetime.utcnow()
        return current_time >= self.expires_at

    def is_limit_reached(self) -> bool:
        """Check if usage limit has been reached.

        Returns:
            True if limit is reached
        """
        return self.usage_limit.is_reached(self.usage_count)

    def use(self, used_by: str, use_time: Optional[datetime] = None) -> None:
        """Use this invitation for registration.

        Args:
            used_by: User ID who is using this invitation
            use_time: Time of usage (defaults to now)

        Raises:
            InvitationExpiredError: If invitation is expired
            InvitationLimitReachedError: If usage limit is reached
            InvitationAlreadyUsedError: If invitation is not active
        """
        use_time = use_time or datetime.utcnow()

        # Check status
        if self.status != InvitationStatus.ACTIVE:
            logger.warning(f"Attempted to use invitation {self.id} with status {self.status}")
            raise InvitationAlreadyUsedError(
                f"Invitation is {self.status.value} and cannot be used"
            )

        # Check expiration
        if self.is_expired(use_time):
            logger.warning(f"Attempted to use expired invitation {self.id}")
            self.status = InvitationStatus.EXPIRED
            raise InvitationExpiredError(f"Invitation expired at {self.expires_at}")

        # Check limit
        if self.is_limit_reached():
            logger.warning(f"Attempted to use invitation {self.id} that reached limit")
            raise InvitationLimitReachedError(
                f"Invitation usage limit of {self.usage_limit} has been reached"
            )

        # Record usage
        self.usage_count += 1
        self.used_by.append(used_by)

        # Update status if limit reached
        if self.is_limit_reached():
            self.status = InvitationStatus.USED
            logger.info(f"Invitation {self.id} marked as USED after reaching limit")
        else:
            logger.info(
                f"Invitation {self.id} used by {used_by} "
                f"({self.usage_count}/{self.usage_limit})"
            )

    def revoke(
        self, revoked_by: str, reason: Optional[str] = None, revoke_time: Optional[datetime] = None
    ) -> None:
        """Revoke this invitation.

        Args:
            revoked_by: User ID who is revoking this invitation
            reason: Optional reason for revocation
            revoke_time: Time of revocation (defaults to now)
        """
        if self.status == InvitationStatus.REVOKED:
            logger.warning(f"Invitation {self.id} is already revoked")
            return

        self.status = InvitationStatus.REVOKED
        self.revoked_at = revoke_time or datetime.utcnow()
        self.revoked_by = revoked_by
        self.revocation_reason = reason

        logger.info(f"Invitation {self.id} revoked by {revoked_by}: {reason or 'No reason given'}")

    def remaining_uses(self) -> Optional[int]:
        """Get remaining number of uses.

        Returns:
            Number of remaining uses, or None if unlimited
        """
        if self.usage_limit.is_unlimited():
            return None

        remaining = self.usage_limit.value - self.usage_count  # type: ignore
        return max(0, remaining)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"Invitation(id={self.id}, code={self.code}, "
            f"status={self.status.value}, usage={self.usage_count}/{self.usage_limit})"
        )
