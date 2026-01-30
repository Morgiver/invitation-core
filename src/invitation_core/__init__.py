"""Invitation Core - Domain-focused invitation code management system.

A framework-agnostic package for managing invitation codes following
hexagonal architecture and domain-driven design principles.
"""

from invitation_core.domain import (
    Invitation,
    InvitationAlreadyExistsError,
    InvitationAlreadyUsedError,
    InvitationCode,
    InvitationDomainError,
    InvitationExpiredError,
    InvitationLimitReachedError,
    InvitationNotFoundError,
    InvitationService,
    InvitationStatus,
    InvalidInvitationCodeError,
    UsageLimit,
)
from invitation_core.dto import (
    CreateInvitationRequest,
    InvitationResponse,
    InvitationStatsResponse,
    InvitationUsageResponse,
    InvitationValidationResponse,
    RevokeInvitationRequest,
    UseInvitationRequest,
    ValidateInvitationRequest,
)
from invitation_core.events import (
    InvitationCreatedEvent,
    InvitationExpiredEvent,
    InvitationLimitReachedEvent,
    InvitationRevokedEvent,
    InvitationUsedEvent,
)
from invitation_core.interfaces import IEventBus, IInvitationRepository

__version__ = "0.1.0"

__all__ = [
    # Domain
    "Invitation",
    "InvitationStatus",
    "InvitationCode",
    "UsageLimit",
    "InvitationService",
    # Exceptions
    "InvitationDomainError",
    "InvitationNotFoundError",
    "InvitationAlreadyUsedError",
    "InvitationExpiredError",
    "InvitationLimitReachedError",
    "InvalidInvitationCodeError",
    "InvitationAlreadyExistsError",
    # DTOs
    "CreateInvitationRequest",
    "UseInvitationRequest",
    "RevokeInvitationRequest",
    "ValidateInvitationRequest",
    "InvitationResponse",
    "InvitationValidationResponse",
    "InvitationUsageResponse",
    "InvitationStatsResponse",
    # Events
    "InvitationCreatedEvent",
    "InvitationUsedEvent",
    "InvitationRevokedEvent",
    "InvitationExpiredEvent",
    "InvitationLimitReachedEvent",
    # Interfaces
    "IInvitationRepository",
    "IEventBus",
]
