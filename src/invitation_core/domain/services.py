"""Domain services for invitation business logic."""

import logging
from datetime import datetime
from typing import Optional

from invitation_core.domain.exceptions import (
    InvitationAlreadyExistsError,
    InvitationNotFoundError,
)
from invitation_core.domain.models import Invitation, InvitationStatus
from invitation_core.domain.value_objects import InvitationCode, UsageLimit
from invitation_core.dto.requests import (
    CreateInvitationRequest,
    RevokeInvitationRequest,
    UseInvitationRequest,
    ValidateInvitationRequest,
)
from invitation_core.dto.responses import (
    InvitationResponse,
    InvitationStatsResponse,
    InvitationUsageResponse,
    InvitationValidationResponse,
)
from invitation_core.events.events import (
    InvitationCreatedEvent,
    InvitationLimitReachedEvent,
    InvitationRevokedEvent,
    InvitationUsedEvent,
)
from invitation_core.interfaces.event_bus import IEventBus
from invitation_core.interfaces.repository import IInvitationRepository

logger = logging.getLogger(__name__)


class InvitationService:
    """Domain service for invitation management.

    Orchestrates business logic for creating, using, validating, and revoking invitations.
    """

    def __init__(
        self, repository: IInvitationRepository, event_bus: Optional[IEventBus] = None
    ) -> None:
        """Initialize the service.

        Args:
            repository: Repository for invitation persistence
            event_bus: Optional event bus for publishing domain events
        """
        self.repository = repository
        self.event_bus = event_bus

    def create_invitation(self, request: CreateInvitationRequest) -> InvitationResponse:
        """Create a new invitation.

        Args:
            request: Creation request with invitation details

        Returns:
            Created invitation response

        Raises:
            InvitationAlreadyExistsError: If code already exists
        """
        logger.info(f"Creating invitation with code: {request.code}")

        # Create value objects
        code = InvitationCode(request.code)

        # Check if code already exists
        if self.repository.exists_by_code(code):
            logger.warning(f"Attempted to create invitation with existing code: {code}")
            raise InvitationAlreadyExistsError(f"Invitation code '{code}' already exists")

        # Create usage limit
        usage_limit = UsageLimit(request.usage_limit)

        # Create invitation
        invitation = Invitation.create(
            code=code,
            created_by=request.created_by,
            expires_at=request.expires_at,
            usage_limit=usage_limit,
            metadata=request.metadata,
        )

        # Save to repository
        saved_invitation = self.repository.save(invitation)

        # Publish event
        if self.event_bus:
            event = InvitationCreatedEvent(
                invitation_id=saved_invitation.id,
                code=str(saved_invitation.code),
                created_by=saved_invitation.created_by,
                created_at=saved_invitation.created_at,
                expires_at=saved_invitation.expires_at,
                usage_limit=saved_invitation.usage_limit.value,
                metadata=saved_invitation.metadata,
            )
            self.event_bus.publish(event)
            logger.debug(f"Published InvitationCreatedEvent for {saved_invitation.id}")

        logger.info(f"Successfully created invitation {saved_invitation.id}")
        return InvitationResponse.from_domain(saved_invitation)

    def use_invitation(self, request: UseInvitationRequest) -> InvitationUsageResponse:
        """Use an invitation for registration.

        Args:
            request: Usage request with code and user

        Returns:
            Usage response with updated information

        Raises:
            InvitationNotFoundError: If invitation not found
            InvitationExpiredError: If invitation is expired
            InvitationLimitReachedError: If usage limit reached
            InvitationAlreadyUsedError: If invitation is not active
        """
        logger.info(f"Using invitation with code: {request.code} by user: {request.used_by}")

        # Find invitation
        code = InvitationCode(request.code)
        invitation = self.repository.find_by_code(code)

        if not invitation:
            logger.warning(f"Invitation not found with code: {code}")
            raise InvitationNotFoundError(f"Invitation with code '{code}' not found")

        # Record previous status
        was_limit_reached_before = invitation.is_limit_reached()

        # Use invitation (raises exceptions if invalid)
        use_time = datetime.utcnow()
        invitation.use(used_by=request.used_by, use_time=use_time)

        # Save updated invitation
        updated_invitation = self.repository.save(invitation)

        # Publish events
        if self.event_bus:
            # Always publish used event
            used_event = InvitationUsedEvent(
                invitation_id=updated_invitation.id,
                code=str(updated_invitation.code),
                used_by=request.used_by,
                used_at=use_time,
                usage_count=updated_invitation.usage_count,
                remaining_uses=updated_invitation.remaining_uses(),
                is_exhausted=updated_invitation.status == InvitationStatus.USED,
            )
            self.event_bus.publish(used_event)
            logger.debug(f"Published InvitationUsedEvent for {updated_invitation.id}")

            # Publish limit reached event if applicable
            if not was_limit_reached_before and updated_invitation.is_limit_reached():
                limit_event = InvitationLimitReachedEvent(
                    invitation_id=updated_invitation.id,
                    code=str(updated_invitation.code),
                    usage_limit=updated_invitation.usage_limit.value or 0,
                    final_used_by=request.used_by,
                    reached_at=use_time,
                )
                self.event_bus.publish(limit_event)
                logger.debug(f"Published InvitationLimitReachedEvent for {updated_invitation.id}")

        logger.info(
            f"Successfully used invitation {updated_invitation.id} "
            f"({updated_invitation.usage_count}/{updated_invitation.usage_limit})"
        )

        return InvitationUsageResponse(
            invitation_id=updated_invitation.id,
            code=str(updated_invitation.code),
            used_by=request.used_by,
            usage_count=updated_invitation.usage_count,
            remaining_uses=updated_invitation.remaining_uses(),
            is_exhausted=updated_invitation.status == InvitationStatus.USED,
        )

    def validate_invitation(
        self, request: ValidateInvitationRequest
    ) -> InvitationValidationResponse:
        """Validate an invitation code without using it.

        Args:
            request: Validation request with code

        Returns:
            Validation response with details
        """
        logger.debug(f"Validating invitation with code: {request.code}")

        code = InvitationCode(request.code)
        invitation = self.repository.find_by_code(code)

        if not invitation:
            return InvitationValidationResponse(
                is_valid=False, code=str(code), reason="Invitation not found"
            )

        # Check if valid
        is_valid = invitation.is_valid()

        # Determine reason if invalid
        reason = None
        if not is_valid:
            if invitation.status != InvitationStatus.ACTIVE:
                reason = f"Invitation is {invitation.status.value}"
            elif invitation.is_expired():
                reason = "Invitation has expired"
            elif invitation.is_limit_reached():
                reason = "Invitation usage limit reached"

        return InvitationValidationResponse(
            is_valid=is_valid,
            code=str(code),
            status=invitation.status.value,
            reason=reason,
            remaining_uses=invitation.remaining_uses(),
            expires_at=invitation.expires_at,
        )

    def revoke_invitation(self, request: RevokeInvitationRequest) -> InvitationResponse:
        """Revoke an invitation.

        Args:
            request: Revocation request

        Returns:
            Updated invitation response

        Raises:
            InvitationNotFoundError: If invitation not found
        """
        logger.info(
            f"Revoking invitation {request.invitation_id} by {request.revoked_by}: {request.reason}"
        )

        # Find invitation
        invitation = self.repository.find_by_id(request.invitation_id)

        if not invitation:
            logger.warning(f"Invitation not found: {request.invitation_id}")
            raise InvitationNotFoundError(
                f"Invitation with ID '{request.invitation_id}' not found"
            )

        # Revoke invitation
        revoke_time = datetime.utcnow()
        invitation.revoke(
            revoked_by=request.revoked_by, reason=request.reason, revoke_time=revoke_time
        )

        # Save updated invitation
        updated_invitation = self.repository.save(invitation)

        # Publish event
        if self.event_bus:
            event = InvitationRevokedEvent(
                invitation_id=updated_invitation.id,
                code=str(updated_invitation.code),
                revoked_by=request.revoked_by,
                revoked_at=revoke_time,
                reason=request.reason,
            )
            self.event_bus.publish(event)
            logger.debug(f"Published InvitationRevokedEvent for {updated_invitation.id}")

        logger.info(f"Successfully revoked invitation {updated_invitation.id}")
        return InvitationResponse.from_domain(updated_invitation)

    def get_invitation_by_id(self, invitation_id: str) -> InvitationResponse:
        """Get invitation by ID.

        Args:
            invitation_id: The invitation ID

        Returns:
            Invitation response

        Raises:
            InvitationNotFoundError: If not found
        """
        invitation = self.repository.find_by_id(invitation_id)

        if not invitation:
            raise InvitationNotFoundError(f"Invitation with ID '{invitation_id}' not found")

        return InvitationResponse.from_domain(invitation)

    def get_invitation_by_code(self, code: str) -> InvitationResponse:
        """Get invitation by code.

        Args:
            code: The invitation code

        Returns:
            Invitation response

        Raises:
            InvitationNotFoundError: If not found
        """
        invitation_code = InvitationCode(code)
        invitation = self.repository.find_by_code(invitation_code)

        if not invitation:
            raise InvitationNotFoundError(f"Invitation with code '{code}' not found")

        return InvitationResponse.from_domain(invitation)

    def get_invitations_by_creator(self, user_id: str) -> list[InvitationResponse]:
        """Get all invitations created by a user.

        Args:
            user_id: The user ID

        Returns:
            List of invitation responses
        """
        invitations = self.repository.find_by_created_by(user_id)
        return [InvitationResponse.from_domain(inv) for inv in invitations]

    def get_invitation_stats(self) -> InvitationStatsResponse:
        """Get invitation statistics.

        Returns:
            Statistics response
        """
        active = self.repository.count_by_status(InvitationStatus.ACTIVE)
        used = self.repository.count_by_status(InvitationStatus.USED)
        expired = self.repository.count_by_status(InvitationStatus.EXPIRED)
        revoked = self.repository.count_by_status(InvitationStatus.REVOKED)

        return InvitationStatsResponse(
            total=active + used + expired + revoked,
            active=active,
            used=used,
            expired=expired,
            revoked=revoked,
        )
