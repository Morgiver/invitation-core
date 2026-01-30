"""Unit tests for event bus adapters."""

import pytest

from invitation_core.adapters.event_buses.memory import InMemoryEventBus
from invitation_core.events import InvitationCreatedEvent, InvitationUsedEvent


class TestInMemoryEventBus:
    """Tests for in-memory event bus."""

    def test_publish_event(self):
        """Test publishing an event."""
        bus = InMemoryEventBus()
        event = InvitationCreatedEvent(
            invitation_id="123",
            code="TEST",
            created_by="user",
            created_at=None,
            expires_at=None,
            usage_limit=1,
            metadata={},
        )

        bus.publish(event)

        events = bus.get_published_events()
        assert len(events) == 1
        assert events[0] == event

    def test_subscribe_and_publish(self):
        """Test subscribing to events and receiving them."""
        bus = InMemoryEventBus()
        received_events = []

        def handler(event):
            received_events.append(event)

        bus.subscribe(InvitationCreatedEvent, handler)

        event = InvitationCreatedEvent(
            invitation_id="123",
            code="TEST",
            created_by="user",
            created_at=None,
            expires_at=None,
            usage_limit=1,
            metadata={},
        )

        bus.publish(event)

        assert len(received_events) == 1
        assert received_events[0] == event

    def test_multiple_subscribers(self):
        """Test multiple subscribers for same event type."""
        bus = InMemoryEventBus()
        received_1 = []
        received_2 = []

        def handler1(event):
            received_1.append(event)

        def handler2(event):
            received_2.append(event)

        bus.subscribe(InvitationCreatedEvent, handler1)
        bus.subscribe(InvitationCreatedEvent, handler2)

        event = InvitationCreatedEvent(
            invitation_id="123",
            code="TEST",
            created_by="user",
            created_at=None,
            expires_at=None,
            usage_limit=1,
            metadata={},
        )

        bus.publish(event)

        assert len(received_1) == 1
        assert len(received_2) == 1

    def test_different_event_types(self):
        """Test subscribing to different event types."""
        bus = InMemoryEventBus()
        created_events = []
        used_events = []

        def created_handler(event):
            created_events.append(event)

        def used_handler(event):
            used_events.append(event)

        bus.subscribe(InvitationCreatedEvent, created_handler)
        bus.subscribe(InvitationUsedEvent, used_handler)

        created_event = InvitationCreatedEvent(
            invitation_id="123",
            code="TEST",
            created_by="user",
            created_at=None,
            expires_at=None,
            usage_limit=1,
            metadata={},
        )

        used_event = InvitationUsedEvent(
            invitation_id="123",
            code="TEST",
            used_by="user2",
            used_at=None,
            usage_count=1,
            remaining_uses=0,
            is_exhausted=True,
        )

        bus.publish(created_event)
        bus.publish(used_event)

        assert len(created_events) == 1
        assert len(used_events) == 1
        assert created_events[0] == created_event
        assert used_events[0] == used_event

    def test_handler_exception_does_not_stop_other_handlers(self):
        """Test that exception in one handler doesn't stop others."""
        bus = InMemoryEventBus()
        received = []

        def failing_handler(event):
            raise ValueError("Handler failed")

        def working_handler(event):
            received.append(event)

        bus.subscribe(InvitationCreatedEvent, failing_handler)
        bus.subscribe(InvitationCreatedEvent, working_handler)

        event = InvitationCreatedEvent(
            invitation_id="123",
            code="TEST",
            created_by="user",
            created_at=None,
            expires_at=None,
            usage_limit=1,
            metadata={},
        )

        bus.publish(event)

        # Working handler should still receive event
        assert len(received) == 1

    def test_clear_events(self):
        """Test clearing published events."""
        bus = InMemoryEventBus()

        event = InvitationCreatedEvent(
            invitation_id="123",
            code="TEST",
            created_by="user",
            created_at=None,
            expires_at=None,
            usage_limit=1,
            metadata={},
        )

        bus.publish(event)
        assert len(bus.get_published_events()) == 1

        bus.clear()
        assert len(bus.get_published_events()) == 0

    def test_get_published_events_returns_copy(self):
        """Test that get_published_events returns a copy."""
        bus = InMemoryEventBus()

        event = InvitationCreatedEvent(
            invitation_id="123",
            code="TEST",
            created_by="user",
            created_at=None,
            expires_at=None,
            usage_limit=1,
            metadata={},
        )

        bus.publish(event)

        events1 = bus.get_published_events()
        events2 = bus.get_published_events()

        # Should be different lists
        assert events1 is not events2
        # But same content
        assert events1 == events2
