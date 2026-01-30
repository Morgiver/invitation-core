"""In-memory repository implementation for invitations (testing/development)."""

import logging
from datetime import datetime
from typing import Optional

from invitation_core.domain.exceptions import InvitationAlreadyExistsError
from invitation_core.domain.models import Invitation, InvitationStatus
from invitation_core.domain.value_objects import InvitationCode
from invitation_core.interfaces.repository import IInvitationRepository

logger = logging.getLogger(__name__)


class InMemoryInvitationRepository(IInvitationRepository):
    """In-memory implementation of invitation repository.

    Useful for testing and development. Not thread-safe.
    """

    def __init__(self) -> None:
        """Initialize empty in-memory storage."""
        self._invitations: dict[str, Invitation] = {}

    def save(self, invitation: Invitation) -> Invitation:
        """Save an invitation (create or update)."""
        # Check if code exists (different ID)
        if invitation.id not in self._invitations:
            for existing in self._invitations.values():
                if existing.code == invitation.code:
                    raise InvitationAlreadyExistsError(
                        f"Invitation code '{invitation.code}' already exists"
                    )

        self._invitations[invitation.id] = invitation
        logger.debug(f"Saved invitation {invitation.id} to memory")
        return invitation

    def find_by_id(self, invitation_id: str) -> Optional[Invitation]:
        """Find an invitation by its ID."""
        return self._invitations.get(invitation_id)

    def find_by_code(self, code: InvitationCode) -> Optional[Invitation]:
        """Find an invitation by its code (case-insensitive)."""
        for invitation in self._invitations.values():
            if invitation.code == code:
                return invitation
        return None

    def exists_by_code(self, code: InvitationCode) -> bool:
        """Check if an invitation exists with the given code."""
        return self.find_by_code(code) is not None

    def find_by_created_by(self, user_id: str) -> list[Invitation]:
        """Find all invitations created by a user."""
        invitations = [inv for inv in self._invitations.values() if inv.created_by == user_id]
        return sorted(invitations, key=lambda x: x.created_at, reverse=True)

    def find_by_status(self, status: InvitationStatus) -> list[Invitation]:
        """Find all invitations with a given status."""
        invitations = [inv for inv in self._invitations.values() if inv.status == status]
        return sorted(invitations, key=lambda x: x.created_at, reverse=True)

    def find_expired(self, check_time: Optional[datetime] = None) -> list[Invitation]:
        """Find all expired invitations."""
        check_time = check_time or datetime.utcnow()
        invitations = [
            inv
            for inv in self._invitations.values()
            if inv.expires_at is not None and inv.expires_at <= check_time
        ]
        return sorted(invitations, key=lambda x: x.expires_at or datetime.min, reverse=True)

    def delete(self, invitation_id: str) -> bool:
        """Delete an invitation."""
        if invitation_id in self._invitations:
            del self._invitations[invitation_id]
            logger.info(f"Deleted invitation {invitation_id} from memory")
            return True
        return False

    def count_by_status(self, status: InvitationStatus) -> int:
        """Count invitations by status."""
        return sum(1 for inv in self._invitations.values() if inv.status == status)

    def clear(self) -> None:
        """Clear all invitations (useful for testing)."""
        self._invitations.clear()
        logger.debug("Cleared all invitations from memory")
