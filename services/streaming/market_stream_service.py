"""
Market Stream Service

Managed service that runs real-time market data streams
Can be started/stopped via the service manager
"""

import asyncio
import sys
import os
from typing import Optional

# Add paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.streaming.realtime_market_stream import realtime_stream


class MarketStreamService:
    """Service wrapper for real-time market data streaming"""

    def __init__(self):
        self.stream = realtime_stream
        self.running = False
        self.task: Optional[asyncio.Task] = None

        # Default symbols to stream
        self.symbols = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA']

        # Exchange to use
        self.exchange = 'kraken'  # or 'binance'

    async def start(self):
        """Start the market stream service"""
        if self.running:
            print("[WARNING] Market stream already running")
            return

        print(f"[START] Starting market stream service ({self.exchange})...")
        self.running = True

        # Start the appropriate WebSocket connection
        if self.exchange == 'kraken':
            self.task = asyncio.create_task(self.stream.connect_kraken(self.symbols))
        elif self.exchange == 'binance':
            self.task = asyncio.create_task(self.stream.connect_binance(self.symbols))
        else:
            print(f"[ERROR] Unknown exchange: {self.exchange}")
            self.running = False
            return

        print(f"[OK] Market stream service started for {', '.join(self.symbols)}")

    async def stop(self):
        """Stop the market stream service"""
        if not self.running:
            return

        print("[STOP] Stopping market stream service...")
        self.running = False

        await self.stream.stop()

        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        print("[OK] Market stream service stopped")

    def set_symbols(self, symbols: list[str]):
        """Update the list of symbols to stream"""
        self.symbols = symbols
        print(f"[UPDATE] Updated symbols: {', '.join(symbols)}")

    def set_exchange(self, exchange: str):
        """Set the exchange to use (kraken or binance)"""
        if exchange.lower() in ['kraken', 'binance']:
            self.exchange = exchange.lower()
            print(f"[EXCHANGE] Exchange set to: {self.exchange}")
        else:
            print(f"[ERROR] Unknown exchange: {exchange}")

    def get_stats(self):
        """Get service statistics"""
        return {
            "running": self.running,
            "exchange": self.exchange,
            "symbols": self.symbols,
            "stream_stats": self.stream.get_stats()
        }

    def get_latest_prices(self):
        """Get latest prices for all subscribed symbols"""
        return {
            symbol: self.stream.get_latest_price(symbol)
            for symbol in self.symbols
        }


# Global service instance
market_stream_service = MarketStreamService()


# Entry point for running as standalone service
async def main():
    """Run the service standalone"""
    service = market_stream_service

    try:
        await service.start()

        # Keep running until interrupted
        while service.running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Received interrupt signal")
    finally:
        await service.stop()


if __name__ == "__main__":
    print("=" * 60)
    print("JJ-Bot Market Stream Service")
    print("=" * 60)

    asyncio.run(main())
