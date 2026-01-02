"""
WebSocket Manager - Real-time event broadcasting to dashboard
"""

import asyncio
import json
from datetime import datetime
from typing import Set, Dict, Any
from fastapi import WebSocket
import sys
import os

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.event_bus import event_bus


class WebSocketManager:
    """Manages WebSocket connections and broadcasts events to clients"""

    def __init__(self, ping_interval: int = 30, ping_timeout: int = 10):
        # Active WebSocket connections
        self.active_connections: Set[WebSocket] = set()

        # Heartbeat configuration
        self.ping_interval = ping_interval  # seconds
        self.ping_timeout = ping_timeout    # seconds
        self.heartbeat_tasks: Dict[WebSocket, asyncio.Task] = {}

        # Event subscription setup
        self._setup_event_subscriptions()

        # Stats
        self.stats = {
            "total_connections": 0,
            "current_connections": 0,
            "messages_sent": 0,
            "events_received": 0,
            "heartbeats_sent": 0,
            "heartbeats_failed": 0
        }

    def _setup_event_subscriptions(self):
        """Subscribe to all relevant events from event bus"""
        # Market data events
        event_bus.subscribe("PRICE_UPDATE", self._on_price_update)

        # Trading signal events
        event_bus.subscribe("TRADING_SIGNAL", self._on_trading_signal)

        # Trade execution events
        event_bus.subscribe("TRADE_EXECUTED", self._on_trade_executed)
        event_bus.subscribe("TRADE_APPROVED", self._on_trade_approved)
        event_bus.subscribe("TRADE_REJECTED", self._on_trade_rejected)

        print("[OK] WebSocket Manager subscribed to event bus")

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.stats["total_connections"] += 1
        self.stats["current_connections"] = len(self.active_connections)

        # Send welcome message
        await self._send_to_client(websocket, {
            "type": "connection",
            "status": "connected",
            "message": "Connected to JJ-Bot real-time feed",
            "timestamp": datetime.now().isoformat()
        })

        # Start heartbeat for this connection
        heartbeat_task = asyncio.create_task(self._heartbeat_loop(websocket))
        self.heartbeat_tasks[websocket] = heartbeat_task

        print(f"[WS] WebSocket client connected (total: {len(self.active_connections)})")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        self.active_connections.discard(websocket)
        self.stats["current_connections"] = len(self.active_connections)

        # Cancel heartbeat task if exists
        if websocket in self.heartbeat_tasks:
            task = self.heartbeat_tasks.pop(websocket)
            if not task.done():
                task.cancel()

        print(f"[WS] WebSocket client disconnected (total: {len(self.active_connections)})")

    async def _heartbeat_loop(self, websocket: WebSocket):
        """
        Send periodic ping messages to keep connection alive
        and detect dead connections
        """
        try:
            while websocket in self.active_connections:
                await asyncio.sleep(self.ping_interval)

                # Send ping
                try:
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": datetime.now().isoformat()
                    })
                    self.stats["heartbeats_sent"] += 1
                except Exception as e:
                    print(f"[WARNING] Heartbeat failed for client: {e}")
                    self.stats["heartbeats_failed"] += 1
                    self.disconnect(websocket)
                    break

        except asyncio.CancelledError:
            # Task was cancelled (connection closed)
            pass
        except Exception as e:
            print(f"[WARNING] Error in heartbeat loop: {e}")
            self.disconnect(websocket)

    async def _send_to_client(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to a single client"""
        try:
            await websocket.send_json(message)
            self.stats["messages_sent"] += 1
        except Exception as e:
            print(f"[WARNING] Error sending to client: {e}")
            self.disconnect(websocket)

    def _safe_broadcast(self, message: Dict[str, Any]):
        """Safely schedule a broadcast from sync context"""
        if not self.active_connections:
            return

        try:
            # Try to get the running event loop
            loop = asyncio.get_running_loop()
            # Schedule the broadcast as a task
            loop.create_task(self.broadcast(message))
        except RuntimeError:
            # No running event loop - silently skip
            # This happens when events fire before the server starts
            pass
        except Exception as e:
            # Unexpected error - log but don't crash
            print(f"[WARNING] Error scheduling broadcast: {e}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return

        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
                self.stats["messages_sent"] += 1
            except Exception as e:
                print(f"[WARNING] Error broadcasting: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    def _on_price_update(self, event: Dict):
        """Handle price update events"""
        self.stats["events_received"] += 1
        data = event.get("data", {})

        message = {
            "type": "price_update",
            "data": {
                "symbol": data.get("symbol"),
                "price": data.get("price"),
                "change_24h": data.get("change_24h"),
                "volume_24h": data.get("volume_24h"),
                "timestamp": data.get("timestamp", datetime.now().isoformat())
            }
        }

        # Schedule broadcast safely
        self._safe_broadcast(message)

    def _on_trading_signal(self, event: Dict):
        """Handle trading signal events"""
        self.stats["events_received"] += 1
        data = event.get("data", {})

        message = {
            "type": "trading_signal",
            "data": {
                "symbol": data.get("symbol"),
                "action": data.get("action"),
                "price": data.get("price"),
                "strength": data.get("strength"),
                "reason": data.get("reason", []),
                "timestamp": data.get("timestamp", datetime.now().isoformat())
            }
        }

        self._safe_broadcast(message)

    def _on_trade_executed(self, event: Dict):
        """Handle trade execution events"""
        self.stats["events_received"] += 1
        data = event.get("data", {})

        message = {
            "type": "trade_executed",
            "data": {
                "symbol": data.get("symbol"),
                "action": data.get("action"),
                "price": data.get("price"),
                "quantity": data.get("quantity"),
                "pnl": data.get("pnl"),
                "timestamp": data.get("timestamp", datetime.now().isoformat())
            }
        }

        self._safe_broadcast(message)

    def _on_trade_approved(self, event: Dict):
        """Handle trade approval events"""
        self.stats["events_received"] += 1
        data = event.get("data", {})

        message = {
            "type": "trade_approved",
            "data": {
                "symbol": data.get("symbol"),
                "action": data.get("action"),
                "timestamp": datetime.now().isoformat()
            }
        }

        self._safe_broadcast(message)

    def _on_trade_rejected(self, event: Dict):
        """Handle trade rejection events"""
        self.stats["events_received"] += 1
        data = event.get("data", {})

        message = {
            "type": "trade_rejected",
            "data": {
                "symbol": data.get("symbol"),
                "action": data.get("action"),
                "reason": data.get("reason"),
                "timestamp": datetime.now().isoformat()
            }
        }

        self._safe_broadcast(message)

    async def send_system_message(self, message: str, level: str = "info"):
        """Send a system message to all clients"""
        await self.broadcast({
            "type": "system",
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })

    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics"""
        return self.stats.copy()


# Global WebSocket manager instance
ws_manager = WebSocketManager()
