"""
Event Bus for Module Communication
Modules publish and subscribe to events
"""

import json
from datetime import datetime
from typing import Dict, List, Callable, Any
from collections import defaultdict

class EventBus:
    """Simple event bus for module communication"""
    
    def __init__(self):
        self.subscribers = defaultdict(list)
        self.event_history = []
        self.max_history = 1000
    
    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to an event type"""
        self.subscribers[event_type].append(callback)
        print(f"Subscribed to {event_type}")
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """Unsubscribe from an event type"""
        if callback in self.subscribers[event_type]:
            self.subscribers[event_type].remove(callback)
    
    def publish(self, event_type: str, data: Any):
        """Publish an event"""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
        
        # Notify subscribers
        for callback in self.subscribers[event_type]:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in event handler: {e}")
    
    def get_history(self, event_type: str = None, limit: int = 100):
        """Get event history"""
        history = self.event_history
        if event_type:
            history = [e for e in history if e["type"] == event_type]
        return history[-limit:]

# Global event bus instance
event_bus = EventBus()
