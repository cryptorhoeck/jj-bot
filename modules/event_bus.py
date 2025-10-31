"""
Event Bus for JJ-Bot
Provides pub/sub messaging between modules
"""

import logging
from typing import Dict, List, Callable, Any
from datetime import datetime
import threading


class EventBus:
    """
    Simple event bus for inter-module communication
    Implements publish-subscribe pattern
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
        self._event_history: List[Dict[str, Any]] = []
        self._max_history = 100
        self.logger = logging.getLogger("jjbot.EventBus")

    def subscribe(self, event_type: str, callback: Callable):
        """
        Subscribe to an event type

        Args:
            event_type: Name of the event to subscribe to
            callback: Function to call when event is published
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []

            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)
                self.logger.debug(f"Subscribed to '{event_type}': {callback.__name__}")

    def unsubscribe(self, event_type: str, callback: Callable):
        """
        Unsubscribe from an event type

        Args:
            event_type: Name of the event to unsubscribe from
            callback: Function to remove from subscribers
        """
        with self._lock:
            if event_type in self._subscribers:
                if callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)
                    self.logger.debug(f"Unsubscribed from '{event_type}': {callback.__name__}")

                # Clean up empty subscriber lists
                if not self._subscribers[event_type]:
                    del self._subscribers[event_type]

    def publish(self, event_type: str, data: Any):
        """
        Publish an event to all subscribers

        Args:
            event_type: Name of the event to publish
            data: Data to pass to subscribers
        """
        # Create event object
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }

        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Get subscribers (make a copy to avoid modification during iteration)
        with self._lock:
            subscribers = self._subscribers.get(event_type, []).copy()

        # Call each subscriber
        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"Error in subscriber {callback.__name__} for event '{event_type}': {e}")

        # Log if there were subscribers
        if subscribers:
            self.logger.debug(f"Published '{event_type}' to {len(subscribers)} subscriber(s)")

    def clear_subscribers(self, event_type: str = None):
        """
        Clear all subscribers for an event type, or all subscribers if no type specified

        Args:
            event_type: Optional event type to clear. If None, clears all.
        """
        with self._lock:
            if event_type:
                if event_type in self._subscribers:
                    del self._subscribers[event_type]
                    self.logger.info(f"Cleared all subscribers for '{event_type}'")
            else:
                self._subscribers.clear()
                self.logger.info("Cleared all subscribers")

    def get_subscribers(self, event_type: str = None) -> Dict[str, int]:
        """
        Get count of subscribers for each event type

        Args:
            event_type: Optional event type to check. If None, returns all.

        Returns:
            Dictionary of event types and their subscriber counts
        """
        with self._lock:
            if event_type:
                return {event_type: len(self._subscribers.get(event_type, []))}
            else:
                return {
                    event_type: len(callbacks)
                    for event_type, callbacks in self._subscribers.items()
                }

    def get_event_history(self, event_type: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent event history

        Args:
            event_type: Optional filter by event type
            limit: Maximum number of events to return

        Returns:
            List of recent events
        """
        if event_type:
            events = [e for e in self._event_history if e["type"] == event_type]
        else:
            events = self._event_history.copy()

        return events[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get event bus statistics

        Returns:
            Dictionary with statistics
        """
        with self._lock:
            return {
                "total_event_types": len(self._subscribers),
                "total_subscribers": sum(len(callbacks) for callbacks in self._subscribers.values()),
                "event_types": list(self._subscribers.keys()),
                "subscriber_counts": self.get_subscribers(),
                "events_in_history": len(self._event_history)
            }


# Global event bus instance
event_bus = EventBus()
