"""
Enhanced Data Feed - Top 20 Cryptos (Excluding Stablecoins)
Production-ready with error handling and caching
"""

import time
import json
import threading
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.base import BaseModule
from modules.event_bus import event_bus

class EnhancedDataFeed(BaseModule):
    """Enhanced data feed tracking top cryptos excluding stablecoins"""
    
    # Top cryptos excluding stablecoins (USDT, USDC, DAI, BUSD, etc.)
    TOP_CRYPTOS = [
        "bitcoin", "ethereum", "binancecoin", "solana", "ripple", 
        "cardano", "dogecoin", "avalanche-2", "tron", "chainlink", 
        "polkadot", "polygon", "wrapped-bitcoin", "shiba-inu", 
        "litecoin", "bitcoin-cash", "uniswap", "stellar", "cosmos", 
        "ethereum-classic", "monero", "okb", "internet-computer", 
        "filecoin", "lido-dao", "aptos", "arbitrum", "optimism"
    ]
    
    # Symbol mapping for display
    SYMBOL_MAP = {
        "bitcoin": "BTC", "ethereum": "ETH", "binancecoin": "BNB",
        "solana": "SOL", "ripple": "XRP", "cardano": "ADA",
        "dogecoin": "DOGE", "avalanche-2": "AVAX", "tron": "TRX", 
        "chainlink": "LINK", "polkadot": "DOT", "polygon": "MATIC", 
        "wrapped-bitcoin": "WBTC", "shiba-inu": "SHIB", "litecoin": "LTC", 
        "bitcoin-cash": "BCH", "uniswap": "UNI", "stellar": "XLM",
        "cosmos": "ATOM", "ethereum-classic": "ETC", "monero": "XMR",
        "okb": "OKB", "internet-computer": "ICP", "filecoin": "FIL",
        "lido-dao": "LDO", "aptos": "APT", "arbitrum": "ARB", "optimism": "OP"
    }
    
    def __init__(self):
        super().__init__("EnhancedDataFeed")
        self.running = False
        self.thread = None
        self.price_cache = {}
        self.market_data = {}
        self.last_update = None
        self.update_interval = 30  # seconds
        self.error_count = 0
        self.max_errors = 5
        # Take only first 20 for API limits
        self.active_coins = self.TOP_CRYPTOS[:20]
        
    def start(self) -> bool:
        """Start the enhanced data feed"""
        try:
            self.running = True
            self.status = "RUNNING"
            self.start_time = datetime.now().isoformat()
            
            # Initial fetch
            print(f"📊 Fetching top {len(self.active_coins)} cryptocurrencies (excluding stablecoins)...")
            self.fetch_all_data()
            
            # Start update thread
            self.thread = threading.Thread(target=self._run_feed)
            self.thread.daemon = True
            self.thread.start()
            
            self.logger.info(f"Enhanced feed started - tracking {len(self.active_coins)} cryptos")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to start: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the feed"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.status = "STOPPED"
        self.logger.info("Enhanced feed stopped")
        return True
    
    def health_check(self) -> Dict[str, Any]:
        """Check module health"""
        health = {
            "healthy": self.status == "RUNNING" and self.error_count < self.max_errors,
            "status": self.status,
            "error_count": self.error_count,
            "cache_size": len(self.price_cache),
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "coins_tracked": len(self.price_cache)
        }
        
        # Check if data is stale (>60 seconds old)
        if self.last_update:
            age = (datetime.now() - self.last_update).seconds
            health["data_age_seconds"] = age
            health["healthy"] = health["healthy"] and age < 120
        
        return health
    
    def fetch_all_data(self) -> bool:
        """Fetch data for all selected cryptos"""
        try:
            # Build API request
            ids = ",".join(self.active_coins)
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": ids,
                "vs_currencies": "usd",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
                "include_24hr_change": "true",
                "include_last_updated_at": "true"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self.process_batch_data(data)
            self.last_update = datetime.now()
            self.error_count = 0
            
            return True
            
        except requests.exceptions.RequestException as e:
            self.error_count += 1
            self.logger.error(f"API request failed: {e}")
            
            if self.price_cache:
                self.logger.info("Using cached data due to API error")
                return True
                
            if self.error_count >= self.max_errors:
                self.status = "DEGRADED"
                
            return False
            
        except Exception as e:
            self.log_error(f"Fetch error: {e}")
            return False
    
    def process_batch_data(self, data: Dict):
        """Process batch data from API"""
        timestamp = datetime.now().isoformat()
        
        for coin_id, coin_data in data.items():
            symbol = self.SYMBOL_MAP.get(coin_id, coin_id.upper())
            
            formatted = {
                "id": coin_id,
                "symbol": symbol,
                "price": coin_data.get("usd", 0),
                "market_cap": coin_data.get("usd_market_cap", 0),
                "volume_24h": coin_data.get("usd_24h_vol", 0),
                "change_24h": coin_data.get("usd_24h_change", 0),
                "timestamp": timestamp,
                "source": "coingecko"
            }
            
            # Cache it
            self.price_cache[symbol] = formatted
            self.market_data[coin_id] = formatted
            
            # Publish event
            event_bus.publish("PRICE_UPDATE", formatted)
            
            # Alert on significant moves (>5%)
            if abs(formatted["change_24h"]) > 5:
                event_bus.publish("PRICE_ALERT", {
                    "symbol": symbol,
                    "price": formatted["price"],
                    "change": formatted["change_24h"],
                    "message": f"{symbol} moved {formatted['change_24h']:.2f}% in 24h"
                })
    
    def _run_feed(self):
        """Background feed loop"""
        while self.running:
            try:
                time.sleep(self.update_interval)
                
                if self.fetch_all_data():
                    print(f"📊 Updated {len(self.price_cache)} crypto prices at {datetime.now().strftime('%H:%M:%S')}")
                else:
                    print(f"⚠️ Using cached data - API issues")
                    
            except Exception as e:
                self.log_error(f"Feed loop error: {e}")
                time.sleep(5)
    
    def get_top_movers(self, limit: int = 5) -> Dict:
        """Get top gainers and losers"""
        if not self.price_cache:
            return {"gainers": [], "losers": []}
            
        sorted_by_change = sorted(
            self.price_cache.values(),
            key=lambda x: x.get("change_24h", 0),
            reverse=True
        )
        
        return {
            "gainers": sorted_by_change[:limit],
            "losers": sorted_by_change[-limit:]
        }
    
    def get_market_summary(self) -> Dict:
        """Get market summary statistics"""
        if not self.price_cache:
            return {}
            
        total_market_cap = sum(
            coin.get("market_cap", 0) 
            for coin in self.price_cache.values()
        )
        
        avg_change = sum(
            coin.get("change_24h", 0) 
            for coin in self.price_cache.values()
        ) / len(self.price_cache) if self.price_cache else 0
        
        return {
            "total_market_cap": total_market_cap,
            "average_change_24h": avg_change,
            "coins_tracked": len(self.price_cache),
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "status": self.status
        }
    
    def get_price(self, symbol: str) -> Optional[float]:
        """Get cached price for symbol"""
        data = self.price_cache.get(symbol)
        return data["price"] if data else None
    
    def get_all_prices(self) -> Dict:
        """Get all cached prices"""
        return self.price_cache.copy()
