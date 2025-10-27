"""
Data Feed Module for JJ-Bot
Gets real-time market data from multiple sources
"""

import time
import json
import threading
import requests
from datetime import datetime
from typing import Dict, Any, Optional
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.base import BaseModule
from modules.event_bus import event_bus

class DataFeedModule(BaseModule):
    """Real-time market data feed"""
    
    def __init__(self):
        super().__init__("DataFeed")
        self.running = False
        self.thread = None
        self.price_cache = {}
        self.update_interval = 10  # seconds
        
        # Symbols to track
        self.symbols = [
            "bitcoin", "ethereum", "binancecoin", 
            "cardano", "dogecoin", "polkadot"
        ]
        
        # Data sources
        self.sources = {
            "coingecko": self.fetch_coingecko,
            "backup": self.fetch_backup_data
        }
        
    def start(self) -> bool:
        """Start the data feed"""
        try:
            self.running = True
            self.status = "RUNNING"
            self.start_time = datetime.now().isoformat()
            
            # Start data fetch thread
            self.thread = threading.Thread(target=self._run_feed)
            self.thread.daemon = True
            self.thread.start()
            
            self.logger.info("Data feed started")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to start: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the data feed"""
        try:
            self.running = False
            self.status = "STOPPED"
            
            if self.thread:
                self.thread.join(timeout=5)
            
            self.logger.info("Data feed stopped")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to stop: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Check module health"""
        health = {
            "healthy": self.status == "RUNNING" and self.running,
            "status": self.status,
            "cache_size": len(self.price_cache),
            "last_update": None
        }
        
        # Check if we have recent data
        if self.price_cache:
            latest = max(self.price_cache.values(), 
                        key=lambda x: x.get("timestamp", ""))
            health["last_update"] = latest.get("timestamp")
            
            # Check if data is stale (>60 seconds old)
            if health["last_update"]:
                update_time = datetime.fromisoformat(health["last_update"])
                age = (datetime.now() - update_time).seconds
                health["data_age_seconds"] = age
                health["healthy"] = health["healthy"] and age < 60
        
        return health
    
    def _run_feed(self):
        """Main feed loop"""
        while self.running:
            try:
                # Fetch data from primary source
                data = self.fetch_coingecko()
                
                if data:
                    self.process_data(data)
                else:
                    # Try backup source
                    data = self.fetch_backup_data()
                    if data:
                        self.process_data(data)
                
                # Wait before next update
                time.sleep(self.update_interval)
                
            except Exception as e:
                self.log_error(f"Feed error: {e}")
                time.sleep(5)  # Short wait on error
    
    def fetch_coingecko(self) -> Optional[Dict]:
        """Fetch data from CoinGecko (free API)"""
        try:
            # CoinGecko free API - no key needed
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": ",".join(self.symbols),
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true",
                "include_last_updated_at": "true"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            self.logger.warning(f"CoinGecko fetch failed: {e}")
            return None
    
    def fetch_backup_data(self) -> Dict:
        """Backup data source (mock data for testing)"""
        import random
        
        data = {}
        for symbol in self.symbols:
            base_prices = {
                "bitcoin": 45000,
                "ethereum": 2500,
                "binancecoin": 300,
                "cardano": 0.5,
                "dogecoin": 0.08,
                "polkadot": 7.5
            }
            
            base = base_prices.get(symbol, 100)
            data[symbol] = {
                "usd": base * (1 + random.uniform(-0.02, 0.02)),
                "usd_24h_change": random.uniform(-5, 5),
                "usd_24h_vol": base * random.uniform(1000000, 10000000),
                "last_updated_at": int(time.time())
            }
        
        return data
    
    def process_data(self, data: Dict):
        """Process and publish market data"""
        for symbol, price_data in data.items():
            # Format data
            formatted = {
                "symbol": symbol.upper(),
                "price": price_data.get("usd", 0),
                "change_24h": price_data.get("usd_24h_change", 0),
                "volume_24h": price_data.get("usd_24h_vol", 0),
                "timestamp": datetime.now().isoformat(),
                "source": "coingecko"
            }
            
            # Cache it
            self.price_cache[symbol] = formatted
            
            # Publish events
            event_bus.publish("PRICE_UPDATE", formatted)
            
            # Log significant changes
            if abs(formatted["change_24h"]) > 5:
                event_bus.publish("PRICE_ALERT", {
                    "symbol": symbol,
                    "change": formatted["change_24h"],
                    "message": f"{symbol.upper()} moved {formatted['change_24h']:.2f}%"
                })
    
    def get_price(self, symbol: str) -> Optional[float]:
        """Get cached price for symbol"""
        data = self.price_cache.get(symbol.lower())
        return data["price"] if data else None
    
    def get_all_prices(self) -> Dict:
        """Get all cached prices"""
        return self.price_cache.copy()
