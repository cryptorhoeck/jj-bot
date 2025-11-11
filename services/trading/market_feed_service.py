"""
Market Feed Service - Fetches real-time cryptocurrency market data
"""

import sys
import os
import time
import requests
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

        # Configuration
        self.config = {
            "update_interval": 60,  # seconds (increased to avoid 429 errors)
            "api_url": "https://api.coingecko.com/api/v3/simple/price",
            "coins": [
                "bitcoin", "ethereum", "binancecoin", "solana", "ripple",
                "cardano", "dogecoin", "avalanche-2", "tron", "chainlink",
                "polkadot", "polygon", "wrapped-bitcoin", "shiba-inu",
                "litecoin", "bitcoin-cash", "uniswap", "stellar", "cosmos",
                "ethereum-classic"
            ]
        }

        # Symbol mapping
        self.symbol_map = {
            "bitcoin": "BTC", "ethereum": "ETH", "binancecoin": "BNB",
            "solana": "SOL", "ripple": "XRP", "cardano": "ADA",
            "dogecoin": "DOGE", "avalanche-2": "AVAX", "tron": "TRX",
            "chainlink": "LINK", "polkadot": "DOT", "polygon": "MATIC",
            "wrapped-bitcoin": "WBTC", "shiba-inu": "SHIB", "litecoin": "LTC",
            "bitcoin-cash": "BCH", "uniswap": "UNI", "stellar": "XLM",
            "cosmos": "ATOM", "ethereum-classic": "ETC"
        }

        # Stats tracking
        self.stats = {
            "total_updates": 0,
            "successful_fetches": 0,
            "failed_fetches": 0,
            "last_update": None,
            "last_error": None,
            "current_prices": {}
        }

    def _run(self):
        """Fetch market data in a loop"""
        print(f"🌐 Market Feed Service starting (update every {self.config['update_interval']}s)...")
        print(f"🔍 Market Feed _run() entered, status={self.status}")

        while self.status == "running":
            try:
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
        Fetch current market data from CoinGecko

        Returns:
            Dictionary of symbol -> price data
        """
        try:
            # Build API request
            ids = ",".join(self.config["coins"])
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
                timeout=10
            )

            if response.status_code == 200:
                api_data = response.json()

                # Transform to our format
                result = {}
                for coin_id, data in api_data.items():
                    symbol = self.symbol_map.get(coin_id, coin_id.upper())
                    result[symbol] = {
                        "price": data.get("usd", 0),
                        "change_24h": data.get("usd_24h_change", 0),
                        "market_cap": data.get("usd_market_cap", 0),
                        "volume_24h": data.get("usd_24h_vol", 0)
                    }

                return result
            else:
                print(f"⚠️ Market Feed API returned status {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Market Feed network error: {e}")
            return None
        except Exception as e:
            print(f"⚠️ Market Feed unexpected error: {e}")
            return None

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
