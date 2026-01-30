"""Event bus interface for publishing domain events."""

from abc import ABC, abstractmethod
from typing import Any, Callable


class IEventBus(ABC):
    """Abstract event bus interface for publishing domain events.

    Allows the domain to publish events without depending on a specific
    event bus implementation (Redis, RabbitMQ, in-memory, etc.)
    """

    @abstractmethod
    def publish(self, event: Any) -> None:
        """Publish a domain event.

        Args:
            event: The event to publish
        """
        pass

    @abstractmethod
    def subscribe(self, event_type: type, handler: Callable[[Any], None]) -> None:
        """Subscribe to a specific event type.

        Args:
            event_type: The event class to subscribe to
            handler: Callback function to handle the event
        """
        pass
