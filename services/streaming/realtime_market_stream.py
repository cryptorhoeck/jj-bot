"""
Real-time Market Data Streaming Service

Connects to exchange WebSocket APIs (Kraken, Binance) for live price updates
Publishes price updates to the event bus for distribution to clients
"""

import asyncio
import json
import time
from typing import Dict, Set, Optional, Callable
from datetime import datetime
import websockets

try:
    from modules.event_bus import event_bus
except ImportError:
    # Fallback if event_bus not available
    print("⚠️ Event bus not available, using dummy implementation")
    class DummyEventBus:
        def publish(self, event, data):
            pass
    event_bus = DummyEventBus()


class RealtimeMarketStream:
    """Manages real-time WebSocket connections to cryptocurrency exchanges"""

    def __init__(self):
        self.active = False
        self.websocket = None
        self.subscribed_symbols: Set[str] = set()
        self.price_cache: Dict[str, Dict] = {}

        # Reconnection settings
        self.reconnect_delay = 5  # seconds
        self.max_reconnect_attempts = 10

        # Stats
        self.stats = {
            "messages_received": 0,
            "price_updates": 0,
            "errors": 0,
            "last_update": None,
            "connection_status": "disconnected"
        }

    async def connect_kraken(self, symbols: list[str]):
        """
        Connect to Kraken WebSocket API for real-time ticker data

        Args:
            symbols: List of symbols to subscribe to (e.g., ['BTC', 'ETH', 'SOL'])
        """
        self.active = True
        kraken_pairs = [self._to_kraken_pair(s) for s in symbols]

        uri = "wss://ws.kraken.com"
        attempts = 0

        while self.active and attempts < self.max_reconnect_attempts:
            try:
                print(f"📡 Connecting to Kraken WebSocket... (attempt {attempts + 1})")

                async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as websocket:
                    self.websocket = websocket
                    self.stats["connection_status"] = "connected"
                    print("✅ Connected to Kraken WebSocket")

                    # Subscribe to ticker data
                    subscribe_message = {
                        "event": "subscribe",
                        "pair": kraken_pairs,
                        "subscription": {
                            "name": "ticker"
                        }
                    }

                    await websocket.send(json.dumps(subscribe_message))
                    print(f"📊 Subscribed to tickers: {', '.join(symbols)}")

                    self.subscribed_symbols.update(symbols)

                    # Listen for messages
                    async for message in websocket:
                        if not self.active:
                            break

                        await self._handle_kraken_message(message)

            except websockets.exceptions.ConnectionClosed:
                print("⚠️ Kraken WebSocket connection closed")
                self.stats["connection_status"] = "disconnected"
            except Exception as e:
                print(f"❌ Kraken WebSocket error: {e}")
                self.stats["errors"] += 1
                self.stats["connection_status"] = "error"

            # Reconnect if still active
            if self.active:
                attempts += 1
                print(f"🔄 Reconnecting in {self.reconnect_delay} seconds...")
                await asyncio.sleep(self.reconnect_delay)
            else:
                break

        self.stats["connection_status"] = "disconnected"
        print("🔌 Kraken WebSocket disconnected")

    async def _handle_kraken_message(self, message: str):
        """Process incoming Kraken WebSocket messages"""
        try:
            data = json.loads(message)
            self.stats["messages_received"] += 1

            # Handle heartbeat
            if isinstance(data, dict):
                if data.get("event") == "heartbeat":
                    return
                elif data.get("event") == "systemStatus":
                    print(f"📊 Kraken status: {data.get('status')}")
                    return
                elif data.get("event") == "subscriptionStatus":
                    print(f"✅ Subscription {data.get('status')}: {data.get('pair')}")
                    return

            # Handle ticker updates
            if isinstance(data, list) and len(data) >= 4:
                channel_id = data[0]
                ticker_data = data[1]
                channel_name = data[2]
                pair = data[3]

                if channel_name == "ticker" and isinstance(ticker_data, dict):
                    await self._process_ticker_update(pair, ticker_data)

        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"⚠️ Error processing Kraken message: {e}")

    async def _process_ticker_update(self, pair: str, ticker: dict):
        """Process and publish ticker update"""
        try:
            # Extract ticker data
            # Kraken ticker format: {"a": [ask_price, ...], "b": [bid_price, ...], "c": [last_price, ...], "v": [volume_today, ...], ...}

            last_price = float(ticker.get("c", [0])[0]) if ticker.get("c") else 0
            volume = float(ticker.get("v", [0])[1]) if ticker.get("v") else 0  # 24h volume
            high = float(ticker.get("h", [0])[1]) if ticker.get("h") else 0  # 24h high
            low = float(ticker.get("l", [0])[1]) if ticker.get("l") else 0  # 24h low

            # Convert pair back to symbol
            symbol = self._from_kraken_pair(pair)

            # Calculate 24h change if we have previous price
            change_24h = 0
            if symbol in self.price_cache:
                prev_price = self.price_cache[symbol].get("price", last_price)
                if prev_price > 0:
                    change_24h = ((last_price - prev_price) / prev_price) * 100

            # Update cache
            self.price_cache[symbol] = {
                "price": last_price,
                "volume_24h": volume,
                "high_24h": high,
                "low_24h": low,
                "change_24h": change_24h,
                "timestamp": datetime.now().isoformat()
            }

            # Publish to event bus
            event_bus.publish("PRICE_UPDATE", {
                "symbol": symbol,
                "price": last_price,
                "volume_24h": volume,
                "high_24h": high,
                "low_24h": low,
                "change_24h": change_24h,
                "timestamp": datetime.now().isoformat()
            })

            self.stats["price_updates"] += 1
            self.stats["last_update"] = datetime.now().isoformat()

        except Exception as e:
            print(f"⚠️ Error processing ticker update: {e}")

    async def connect_binance(self, symbols: list[str]):
        """
        Connect to Binance WebSocket API for real-time ticker data

        Args:
            symbols: List of symbols to subscribe to (e.g., ['BTC', 'ETH'])
        """
        self.active = True

        # Binance uses lowercase symbols with 'usdt' suffix
        streams = [f"{s.lower()}usdt@ticker" for s in symbols]
        stream_names = "/".join(streams)

        uri = f"wss://stream.binance.com:9443/stream?streams={stream_names}"
        attempts = 0

        while self.active and attempts < self.max_reconnect_attempts:
            try:
                print(f"📡 Connecting to Binance WebSocket... (attempt {attempts + 1})")

                async with websockets.connect(uri, ping_interval=20) as websocket:
                    self.websocket = websocket
                    self.stats["connection_status"] = "connected"
                    print("✅ Connected to Binance WebSocket")
                    print(f"📊 Subscribed to: {', '.join(symbols)}")

                    self.subscribed_symbols.update(symbols)

                    # Listen for messages
                    async for message in websocket:
                        if not self.active:
                            break

                        await self._handle_binance_message(message)

            except websockets.exceptions.ConnectionClosed:
                print("⚠️ Binance WebSocket connection closed")
                self.stats["connection_status"] = "disconnected"
            except Exception as e:
                print(f"❌ Binance WebSocket error: {e}")
                self.stats["errors"] += 1
                self.stats["connection_status"] = "error"

            # Reconnect if still active
            if self.active:
                attempts += 1
                print(f"🔄 Reconnecting in {self.reconnect_delay} seconds...")
                await asyncio.sleep(self.reconnect_delay)
            else:
                break

        self.stats["connection_status"] = "disconnected"
        print("🔌 Binance WebSocket disconnected")

    async def _handle_binance_message(self, message: str):
        """Process incoming Binance WebSocket messages"""
        try:
            data = json.loads(message)
            self.stats["messages_received"] += 1

            if "data" in data:
                ticker = data["data"]

                # Extract symbol (remove USDT suffix)
                symbol = ticker.get("s", "").replace("USDT", "")

                last_price = float(ticker.get("c", 0))
                volume = float(ticker.get("v", 0))
                high = float(ticker.get("h", 0))
                low = float(ticker.get("l", 0))
                price_change_percent = float(ticker.get("P", 0))

                # Update cache
                self.price_cache[symbol] = {
                    "price": last_price,
                    "volume_24h": volume,
                    "high_24h": high,
                    "low_24h": low,
                    "change_24h": price_change_percent,
                    "timestamp": datetime.now().isoformat()
                }

                # Publish to event bus
                event_bus.publish("PRICE_UPDATE", {
                    "symbol": symbol,
                    "price": last_price,
                    "volume_24h": volume,
                    "high_24h": high,
                    "low_24h": low,
                    "change_24h": price_change_percent,
                    "timestamp": datetime.now().isoformat()
                })

                self.stats["price_updates"] += 1
                self.stats["last_update"] = datetime.now().isoformat()

        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"⚠️ Error processing Binance message: {e}")

    def _to_kraken_pair(self, symbol: str) -> str:
        """Convert symbol to Kraken pair format"""
        mapping = {
            "BTC": "XBT/USD",
            "ETH": "ETH/USD",
            "SOL": "SOL/USD",
            "XRP": "XRP/USD",
            "ADA": "ADA/USD",
            "DOGE": "XDG/USD",
            "AVAX": "AVAX/USD",
            "DOT": "DOT/USD",
            "POL": "POL/USD"
        }
        return mapping.get(symbol.upper(), f"{symbol.upper()}/USD")

    def _from_kraken_pair(self, pair: str) -> str:
        """Convert Kraken pair back to symbol"""
        mapping = {
            "XBT/USD": "BTC",
            "ETH/USD": "ETH",
            "SOL/USD": "SOL",
            "XRP/USD": "XRP",
            "ADA/USD": "ADA",
            "XDG/USD": "DOGE",
            "AVAX/USD": "AVAX",
            "DOT/USD": "DOT",
            "POL/USD": "POL"
        }
        return mapping.get(pair, pair.split("/")[0])

    async def stop(self):
        """Stop the WebSocket connection"""
        print("🛑 Stopping market stream...")
        self.active = False

        if self.websocket:
            await self.websocket.close()

        self.subscribed_symbols.clear()
        self.stats["connection_status"] = "disconnected"

    def get_latest_price(self, symbol: str) -> Optional[Dict]:
        """Get the latest cached price for a symbol"""
        return self.price_cache.get(symbol)

    def get_stats(self) -> Dict:
        """Get service statistics"""
        return {
            **self.stats,
            "subscribed_symbols": list(self.subscribed_symbols),
            "cached_symbols": list(self.price_cache.keys())
        }


# Singleton instance
realtime_stream = RealtimeMarketStream()
