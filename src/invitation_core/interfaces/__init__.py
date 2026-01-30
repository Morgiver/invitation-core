"""Interfaces for invitation core."""

from invitation_core.interfaces.event_bus import IEventBus
from invitation_core.interfaces.repository import IInvitationRepository

__all__ = ["IInvitationRepository", "IEventBus"]
