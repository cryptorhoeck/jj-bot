import asyncio
import json
import websocket
import requests
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import threading

class BinanceDataProvider:
    """Real-time market data from Binance API"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.ws_url = "wss://stream.binance.com:9443/ws"
        self.subscribers = []
        self.ws = None
        self.is_connected = False
        
    def get_ticker_24hr(self, symbol: str) -> Dict:
        """Get 24hr ticker statistics"""
        try:
            url = f"{self.base_url}/ticker/24hr"
            params = {"symbol": symbol.upper()}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'symbol': data['symbol'],
                    'price': float(data['lastPrice']),
                    'price_change_24h': float(data['priceChangePercent']),
                    'volume_24h': float(data['volume']),
                    'volume_change_24h': float(data['count']),  # Trade count as proxy
                    'high_24h': float(data['highPrice']),
                    'low_24h': float(data['lowPrice']),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                raise Exception(f"Binance API error: {response.status_code}")
                
        except Exception as e:
            print(f"Error fetching ticker data: {e}")
            return None
    
    def get_vwap(self, symbol: str, interval: str = "1h", limit: int = 24) -> float:
        """Calculate VWAP from kline data"""
        try:
            url = f"{self.base_url}/klines"
            params = {
                "symbol": symbol.upper(),
                "interval": interval,
                "limit": limit
            }
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                klines = response.json()
                
                total_volume = 0
                total_price_volume = 0
                
                for kline in klines:
                    high = float(kline[2])
                    low = float(kline[3])
                    close = float(kline[4])
                    volume = float(kline[5])
                    
                    # Typical price (HLC/3)
                    typical_price = (high + low + close) / 3
                    
                    total_price_volume += typical_price * volume
                    total_volume += volume
                
                if total_volume > 0:
                    return total_price_volume / total_volume
                else:
                    return 0.0
                    
            else:
                raise Exception(f"Binance klines API error: {response.status_code}")
                
        except Exception as e:
            print(f"Error calculating VWAP: {e}")
            return 0.0
    
    def get_order_book(self, symbol: str, limit: int = 100) -> Dict:
        """Get order book data"""
        try:
            url = f"{self.base_url}/depth"
            params = {"symbol": symbol.upper(), "limit": limit}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Calculate weighted bid/ask
                bids = [[float(price), float(qty)] for price, qty in data['bids'][:10]]
                asks = [[float(price), float(qty)] for price, qty in data['asks'][:10]]
                
                # Calculate order book imbalance
                total_bid_vol = sum(qty for _, qty in bids)
                total_ask_vol = sum(qty for _, qty in asks)
                
                if total_bid_vol + total_ask_vol > 0:
                    buy_pressure = total_bid_vol / (total_bid_vol + total_ask_vol)
                else:
                    buy_pressure = 0.5
                
                return {
                    'best_bid': bids[0][0] if bids else 0,
                    'best_ask': asks[0][0] if asks else 0,
                    'bid_volume': total_bid_vol,
                    'ask_volume': total_ask_vol,
                    'buy_pressure': buy_pressure,
                    'spread': asks[0][0] - bids[0][0] if bids and asks else 0
                }
            else:
                raise Exception(f"Binance depth API error: {response.status_code}")
                
        except Exception as e:
            print(f"Error fetching order book: {e}")
            return None
    
    def start_websocket(self, symbol: str, callback: Callable):
        """Start WebSocket for real-time price updates"""
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if 'c' in data:  # Close price
                    price_data = {
                        'symbol': data['s'],
                        'price': float(data['c']),
                        'timestamp': datetime.now().isoformat()
                    }
                    callback(price_data)
            except Exception as e:
                print(f"WebSocket message error: {e}")
        
        def on_error(ws, error):
            print(f"WebSocket error: {error}")
            self.is_connected = False
        
        def on_close(ws, close_status_code, close_msg):
            print("WebSocket connection closed")
            self.is_connected = False
        
        def on_open(ws):
            print(f"WebSocket connected for {symbol}")
            self.is_connected = True
        
        # Create WebSocket connection
        stream = f"{symbol.lower()}@ticker"
        ws_url = f"{self.ws_url}/{stream}"
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        # Run WebSocket in a separate thread
        def run_ws():
            self.ws.run_forever()
        
        ws_thread = threading.Thread(target=run_ws, daemon=True)
        ws_thread.start()
    
    def stop_websocket(self):
        """Stop WebSocket connection"""
        if self.ws:
            self.ws.close()
            self.is_connected = False

class CoinGeckoProvider:
    """Backup provider using CoinGecko API"""
    
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
    
    def get_price_data(self, coin_id: str = "bitcoin") -> Dict:
        """Get basic price data from CoinGecko"""
        try:
            url = f"{self.base_url}/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true"
            }
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                coin_data = data.get(coin_id, {})
                
                return {
                    'symbol': f"{coin_id.upper()}USDT",
                    'price': coin_data.get('usd', 0),
                    'price_change_24h': coin_data.get('usd_24h_change', 0),
                    'volume_24h': coin_data.get('usd_24h_vol', 0),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                raise Exception(f"CoinGecko API error: {response.status_code}")
                
        except Exception as e:
            print(f"Error fetching CoinGecko data: {e}")
            return None
