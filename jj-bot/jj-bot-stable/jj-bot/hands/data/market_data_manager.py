import asyncio
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path

from .providers.binance_provider import BinanceDataProvider, CoinGeckoProvider

class MarketDataManager:
    """Central manager for all market data"""
    
    def __init__(self):
        self.binance = BinanceDataProvider()
        self.coingecko = CoinGeckoProvider()
        self.cache = {}
        self.cache_duration = 30  # Cache data for 30 seconds
        
        # Default symbols to track
        self.symbols = [
            'BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 
            'LINKUSDT', 'BNBUSDT', 'SOLUSDT', 'AVAXUSDT'
        ]
        
        self.is_running = False
        self.subscribers = []
    
    def add_subscriber(self, callback):
        """Add a callback function to receive market updates"""
        self.subscribers.append(callback)
    
    def notify_subscribers(self, data):
        """Notify all subscribers of market data updates"""
        for callback in self.subscribers:
            try:
                callback(data)
            except Exception as e:
                print(f"Error notifying subscriber: {e}")
    
    def get_live_data(self, symbol: str = "BTCUSDT") -> Dict:
        """Get real-time market data for a symbol"""
        cache_key = f"{symbol}_live"
        now = time.time()
        
        # Check cache first
        if cache_key in self.cache:
            cache_time, cached_data = self.cache[cache_key]
            if now - cache_time < self.cache_duration:
                return cached_data
        
        # Fetch fresh data
        try:
            # Try Binance first
            ticker_data = self.binance.get_ticker_24hr(symbol)
            if ticker_data:
                vwap = self.binance.get_vwap(symbol)
                order_book = self.binance.get_order_book(symbol)
                
                market_data = {
                    **ticker_data,
                    'vwap': vwap,
                    'order_book': order_book,
                    'data_source': 'binance',
                    'last_update': datetime.now().isoformat()
                }
                
                # Cache the data
                self.cache[cache_key] = (now, market_data)
                return market_data
            else:
                raise Exception("Binance data failed")
                
        except Exception as e:
            print(f"Binance error, trying CoinGecko: {e}")
            
            # Fallback to CoinGecko
            try:
                # Map symbol to CoinGecko ID
                coin_map = {
                    'BTCUSDT': 'bitcoin',
                    'ETHUSDT': 'ethereum', 
                    'ADAUSDT': 'cardano',
                    'DOTUSDT': 'polkadot',
                    'LINKUSDT': 'chainlink'
                }
                
                coin_id = coin_map.get(symbol, 'bitcoin')
                fallback_data = self.coingecko.get_price_data(coin_id)
                
                if fallback_data:
                    # Add missing fields with estimates
                    fallback_data.update({
                        'vwap': fallback_data['price'] * 0.998,  # Estimate
                        'order_book': None,
                        'data_source': 'coingecko_fallback'
                    })
                    
                    self.cache[cache_key] = (now, fallback_data)
                    return fallback_data
                
            except Exception as e2:
                print(f"CoinGecko fallback also failed: {e2}")
        
        # Return cached data if available, even if old
        if cache_key in self.cache:
            _, cached_data = self.cache[cache_key]
            cached_data['data_source'] = 'stale_cache'
            return cached_data
        
        # Last resort: return dummy data
        return self._get_dummy_data(symbol)
    
    def _get_dummy_data(self, symbol: str) -> Dict:
        """Generate dummy data when APIs are unavailable"""
        import random
        
        base_price = 99500 if 'BTC' in symbol else 3500
        
        return {
            'symbol': symbol,
            'price': base_price + random.randint(-1000, 1000),
            'price_change_24h': random.uniform(-5, 5),
            'volume_24h': random.randint(1000000000, 3000000000),
            'vwap': base_price + random.randint(-500, 500),
            'data_source': 'dummy_data',
            'timestamp': datetime.now().isoformat()
        }
    
    def get_market_overview(self) -> Dict:
        """Get overview of multiple markets"""
        overview = {
            'timestamp': datetime.now().isoformat(),
            'markets': {},
            'summary': {
                'total_volume': 0,
                'avg_change': 0,
                'trending_up': 0,
                'trending_down': 0
            }
        }
        
        changes = []
        total_volume = 0
        
        for symbol in self.symbols[:5]:  # Limit to avoid rate limits
            try:
                data = self.get_live_data(symbol)
                if data:
                    overview['markets'][symbol] = {
                        'price': data['price'],
                        'change_24h': data['price_change_24h'],
                        'volume_24h': data['volume_24h'],
                        'source': data['data_source']
                    }
                    
                    changes.append(data['price_change_24h'])
                    total_volume += data['volume_24h']
                    
                    if data['price_change_24h'] > 0:
                        overview['summary']['trending_up'] += 1
                    else:
                        overview['summary']['trending_down'] += 1
                        
            except Exception as e:
                print(f"Error getting data for {symbol}: {e}")
        
        # Calculate summary stats
        if changes:
            overview['summary']['avg_change'] = sum(changes) / len(changes)
            overview['summary']['total_volume'] = total_volume
        
        return overview
    
    async def start_live_updates(self, symbol: str = "BTCUSDT", interval: int = 5):
        """Start continuous market data updates"""
        self.is_running = True
        
        def price_callback(data):
            self.notify_subscribers(data)
        
        # Start WebSocket for real-time updates
        self.binance.start_websocket(symbol, price_callback)
        
        print(f"📡 Started live market data for {symbol}")
        
        # Periodic full data updates
        while self.is_running:
            try:
                full_data = self.get_live_data(symbol)
                self.notify_subscribers(full_data)
                await asyncio.sleep(interval)
            except Exception as e:
                print(f"Error in live updates: {e}")
                await asyncio.sleep(interval)
    
    def stop_live_updates(self):
        """Stop live market data updates"""
        self.is_running = False
        self.binance.stop_websocket()
        print("📡 Stopped live market data")

# Global market data manager instance
market_manager = MarketDataManager()
