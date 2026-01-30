"""Repository interface for invitation persistence."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from invitation_core.domain.models import Invitation, InvitationStatus
from invitation_core.domain.value_objects import InvitationCode


class IInvitationRepository(ABC):
    """Abstract repository interface for invitation persistence.

    Implementations can use any storage backend (SQL, NoSQL, in-memory, etc.)
    """

    @abstractmethod
    def save(self, invitation: Invitation) -> Invitation:
        """Save an invitation (create or update).

        Args:
            invitation: The invitation to save

        Returns:
            The saved invitation

        Raises:
            InvitationAlreadyExistsError: If creating with existing code
        """
        pass

    @abstractmethod
    def find_by_id(self, invitation_id: str) -> Optional[Invitation]:
        """Find an invitation by its ID.

        Args:
            invitation_id: The invitation ID

        Returns:
            The invitation if found, None otherwise
        """
        pass

    @abstractmethod
    def find_by_code(self, code: InvitationCode) -> Optional[Invitation]:
        """Find an invitation by its code.

        Args:
            code: The invitation code

        Returns:
            The invitation if found, None otherwise
        """
        pass

    @abstractmethod
    def exists_by_code(self, code: InvitationCode) -> bool:
        """Check if an invitation exists with the given code.

        Args:
            code: The invitation code to check

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    def find_by_created_by(self, user_id: str) -> list[Invitation]:
        """Find all invitations created by a user.

        Args:
            user_id: The user ID

        Returns:
            List of invitations created by this user
        """
        pass

    @abstractmethod
    def find_by_status(self, status: InvitationStatus) -> list[Invitation]:
        """Find all invitations with a given status.

        Args:
            status: The invitation status

        Returns:
            List of invitations with this status
        """
        pass

    @abstractmethod
    def find_expired(self, check_time: Optional[datetime] = None) -> list[Invitation]:
        """Find all expired invitations.

        Args:
            check_time: Time to check against (defaults to now)

        Returns:
            List of expired invitations
        """
        pass

    @abstractmethod
    def delete(self, invitation_id: str) -> bool:
        """Delete an invitation.

        Args:
            invitation_id: The invitation ID to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def count_by_status(self, status: InvitationStatus) -> int:
        """Count invitations by status.

        Args:
            status: The invitation status

        Returns:
            Number of invitations with this status
        """
        pass
