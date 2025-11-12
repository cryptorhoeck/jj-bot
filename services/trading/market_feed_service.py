"""
Market Feed Service - Fetches real-time cryptocurrency market data
"""

import sys
import os
import time
import requests
import sqlite3
from datetime import datetime
from typing import Dict, List, Any

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from services.base.service import BaseService
from modules.event_bus import event_bus


class MarketFeedService(BaseService):
    """Service that fetches real-time market data and publishes price updates"""

    def __init__(self):
        super().__init__(name="market_feed", auto_start=False)  # Disabled - simulator uses real prices

        # Configuration with improved rate limiting
        self.config = {
            "update_interval": 120,  # seconds (2 minutes to avoid 429 errors)
            "api_url": "https://api.coingecko.com/api/v3/simple/price",
            "request_timeout": 15,  # increased timeout
            "retry_delay": 5,  # seconds to wait before retry
            "max_retries": 3
        }

        # Rate limiting tracking
        self.last_request_time = 0
        self.min_request_interval = 120  # Minimum 2 minutes between requests

        # Stats tracking
        self.stats = {
            "total_updates": 0,
            "successful_fetches": 0,
            "failed_fetches": 0,
            "rate_limit_hits": 0,
            "last_update": None,
            "last_error": None,
            "current_prices": {}
        }

    def _get_enabled_symbols(self) -> Dict[str, str]:
        """Get enabled symbols from database"""
        try:
            db_path = os.path.join(
                os.path.dirname(__file__), '..', '..', 'data', 'symbols.db'
            )

            if not os.path.exists(db_path):
                # Return default symbols if database doesn't exist
                return {
                    "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
                    "SOL": "solana", "XRP": "ripple", "ADA": "cardano"
                }

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT symbol, coingecko_id
                FROM symbols
                WHERE enabled = 1
                ORDER BY symbol ASC
            """)

            rows = cursor.fetchall()
            conn.close()

            return {row[0]: row[1] for row in rows}

        except Exception as e:
            print(f"⚠️ Error getting symbols from database: {e}")
            # Return default symbols on error
            return {
                "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
                "SOL": "solana", "XRP": "ripple", "ADA": "cardano"
            }

    def _run(self):
        """Fetch market data in a loop with rate limiting"""
        print(f"🌐 Market Feed Service starting (update every {self.config['update_interval']}s)...")
        print(f"⏱️  Rate limiting: Minimum {self.min_request_interval}s between requests")
        print(f"🔍 Market Feed _run() entered, status={self.status}")

        while self.status == "running":
            try:
                # Check rate limiting
                time_since_last_request = time.time() - self.last_request_time
                if time_since_last_request < self.min_request_interval:
                    wait_time = self.min_request_interval - time_since_last_request
                    print(f"⏸️  Rate limit: Waiting {wait_time:.0f}s before next request...")
                    time.sleep(wait_time)

                # Fetch market data
                print(f"🔍 Market Feed: Fetching data...")
                data = self._fetch_market_data()
                print(f"🔍 Market Feed: Received {len(data) if data else 0} symbols")

                if data:
                    # Update stats
                    self.stats["successful_fetches"] += 1
                    self.stats["last_update"] = datetime.now().isoformat()
                    self.stats["current_prices"] = data

                    # Publish price updates to event bus
                    for symbol, price_data in data.items():
                        event_bus.publish("PRICE_UPDATE", {
                            "symbol": symbol,
                            "price": price_data["price"],
                            "change_24h": price_data["change_24h"],
                            "volume_24h": price_data.get("volume_24h", 0),
                            "timestamp": datetime.now().isoformat()
                        })

                    self.stats["total_updates"] += 1

                    # Log every update
                    print(f"📊 Market Feed: {len(data)} coins updated | Total: {self.stats['total_updates']}")

                else:
                    self.stats["failed_fetches"] += 1

            except Exception as e:
                self.stats["failed_fetches"] += 1
                self.stats["last_error"] = str(e)
                print(f"❌ Market Feed error: {e}")

            # Wait before next update
            time.sleep(self.config["update_interval"])

    def _fetch_market_data(self) -> Dict[str, Dict]:
        """
        Fetch current market data from CoinGecko with retry logic

        Returns:
            Dictionary of symbol -> price data
        """
        # Get enabled symbols from database
        symbol_map = self._get_enabled_symbols()

        if not symbol_map:
            print("⚠️ No enabled symbols to fetch")
            return None

        # Split into batches of 10 to avoid hitting API limits
        symbols_list = list(symbol_map.items())
        batch_size = 10
        all_results = {}

        for i in range(0, len(symbols_list), batch_size):
            batch = symbols_list[i:i + batch_size]
            batch_coingecko_ids = [coin_id for _, coin_id in batch]

            for attempt in range(self.config["max_retries"]):
                try:
                    # Record request time for rate limiting
                    self.last_request_time = time.time()

                    # Build API request
                    ids = ",".join(batch_coingecko_ids)
                    params = {
                        "ids": ids,
                        "vs_currencies": "usd",
                        "include_24hr_change": "true",
                        "include_market_cap": "true",
                        "include_24hr_vol": "true"
                    }

                    # Make request
                    response = requests.get(
                        self.config["api_url"],
                        params=params,
                        timeout=self.config["request_timeout"]
                    )

                    if response.status_code == 200:
                        api_data = response.json()

                        # Transform to our format
                        for symbol, coin_id in batch:
                            if coin_id in api_data:
                                data = api_data[coin_id]
                                all_results[symbol] = {
                                    "price": data.get("usd", 0),
                                    "change_24h": data.get("usd_24h_change", 0),
                                    "market_cap": data.get("usd_market_cap", 0),
                                    "volume_24h": data.get("usd_24h_vol", 0)
                                }

                        break  # Success, exit retry loop

                    elif response.status_code == 429:
                        # Rate limited
                        self.stats["rate_limit_hits"] += 1
                        retry_after = int(response.headers.get('Retry-After', 60))
                        print(f"⚠️ Rate limited (429). Waiting {retry_after}s before retry...")
                        time.sleep(retry_after)

                    else:
                        print(f"⚠️ Market Feed API returned status {response.status_code}")
                        if attempt < self.config["max_retries"] - 1:
                            time.sleep(self.config["retry_delay"])

                except requests.exceptions.Timeout:
                    print(f"⚠️ Request timeout (attempt {attempt + 1}/{self.config['max_retries']})")
                    if attempt < self.config["max_retries"] - 1:
                        time.sleep(self.config["retry_delay"])

                except requests.exceptions.RequestException as e:
                    print(f"⚠️ Market Feed network error: {e}")
                    if attempt < self.config["max_retries"] - 1:
                        time.sleep(self.config["retry_delay"])

                except Exception as e:
                    print(f"⚠️ Market Feed unexpected error: {e}")
                    if attempt < self.config["max_retries"] - 1:
                        time.sleep(self.config["retry_delay"])

            # Small delay between batches
            if i + batch_size < len(symbols_list):
                time.sleep(2)

        return all_results if all_results else None

    def _cleanup(self):
        """Cleanup when stopping"""
        print("🛑 Market Feed Service stopped")

    def get_current_prices(self) -> Dict[str, Dict]:
        """
        Get current cached prices

        Returns:
            Dictionary of symbol -> price data
        """
        return self.stats.get("current_prices", {})

    def get_price(self, symbol: str) -> Dict:
        """
        Get price for a specific symbol

        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')

        Returns:
            Price data dictionary or None if not found
        """
        return self.stats.get("current_prices", {}).get(symbol)
