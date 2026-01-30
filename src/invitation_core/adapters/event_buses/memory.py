"""In-memory event bus implementation for testing/development."""

import logging
from collections import defaultdict
from typing import Any, Callable

from invitation_core.interfaces.event_bus import IEventBus

logger = logging.getLogger(__name__)


class InMemoryEventBus(IEventBus):
    """In-memory event bus implementation.

    Useful for testing and development. Events are handled synchronously.
    Not thread-safe.
    """

    def __init__(self) -> None:
        """Initialize empty event bus."""
        self._handlers: dict[type, list[Callable[[Any], None]]] = defaultdict(list)
        self._published_events: list[Any] = []

    def publish(self, event: Any) -> None:
        """Publish a domain event synchronously.

        Args:
            event: The event to publish
        """
        event_type = type(event)
        self._published_events.append(event)

        logger.debug(f"Publishing event: {event_type.__name__}")

        # Call all registered handlers for this event type
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(
                    f"Error handling event {event_type.__name__} with handler {handler.__name__}: {e}",
                    exc_info=True,
                )

    def subscribe(self, event_type: type, handler: Callable[[Any], None]) -> None:
        """Subscribe to a specific event type.

        Args:
            event_type: The event class to subscribe to
            handler: Callback function to handle the event
        """
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed {handler.__name__} to {event_type.__name__}")

    def get_published_events(self) -> list[Any]:
        """Get all published events (useful for testing).

        Returns:
            List of all published events
        """
        return self._published_events.copy()

    def clear(self) -> None:
        """Clear all published events (useful for testing)."""
        self._published_events.clear()
        logger.debug("Cleared all published events")
