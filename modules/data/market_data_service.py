"""
Market Data Service - Fetches real OHLCV data from multiple sources
Supports: Kraken (crypto), Yahoo Finance (stocks/traditional assets)
Fallback: Generates realistic historical data based on current prices
"""

import requests
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import json
import random
import math


class MarketDataService:
    """Unified service for fetching market data from multiple sources"""

    def __init__(self):
        self.kraken_base_url = "https://api.kraken.com/0/public"
        self.yahoo_base_url = "https://query1.finance.yahoo.com/v8/finance/chart"

    # ===== KRAKEN API (Crypto) =====

    def get_kraken_ohlc(self, pair: str, interval: int = 60, since: Optional[int] = None) -> Dict:
        """
        Fetch OHLC data from Kraken

        Args:
            pair: Trading pair (e.g., 'XBTUSD' for BTC/USD, 'ETHUSD' for ETH/USD)
            interval: Timeframe in minutes (1, 5, 15, 30, 60, 240, 1440, 10080, 21600)
            since: Unix timestamp to fetch data from (optional)

        Returns:
            Dict with OHLC data and metadata
        """
        try:
            url = f"{self.kraken_base_url}/OHLC"
            params = {
                "pair": pair,
                "interval": interval
            }
            if since:
                params["since"] = since

            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()

            if data.get("error") and len(data["error"]) > 0:
                return {"success": False, "error": data["error"]}

            # Kraken returns data in format: [time, open, high, low, close, vwap, volume, count]
            result_key = list(data["result"].keys())[0]  # Get the pair key
            ohlc_data = data["result"][result_key]
            last = data["result"]["last"]

            # Convert to standardized format
            candles = []
            for candle in ohlc_data:
                candles.append({
                    "time": int(candle[0]),
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "vwap": float(candle[5]),
                    "volume": float(candle[6]),
                    "count": int(candle[7])
                })

            return {
                "success": True,
                "pair": pair,
                "interval": interval,
                "candles": candles,
                "last": last,
                "count": len(candles)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_kraken_ticker(self, pairs: List[str]) -> Dict:
        """
        Get current ticker information for multiple pairs

        Args:
            pairs: List of trading pairs (e.g., ['XBTUSD', 'ETHUSD'])

        Returns:
            Dict with ticker data for each pair
        """
        try:
            url = f"{self.kraken_base_url}/Ticker"
            params = {"pair": ",".join(pairs)}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if data.get("error") and len(data["error"]) > 0:
                return {"success": False, "error": data["error"]}

            # Standardize ticker format
            tickers = {}
            for pair, ticker_data in data["result"].items():
                tickers[pair] = {
                    "ask": float(ticker_data["a"][0]),
                    "bid": float(ticker_data["b"][0]),
                    "last": float(ticker_data["c"][0]),
                    "volume": float(ticker_data["v"][1]),  # 24h volume
                    "vwap": float(ticker_data["p"][1]),    # 24h vwap
                    "trades": int(ticker_data["t"][1]),    # 24h trades
                    "low": float(ticker_data["l"][1]),     # 24h low
                    "high": float(ticker_data["h"][1]),    # 24h high
                    "open": float(ticker_data["o"])
                }

            return {"success": True, "tickers": tickers}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ===== YAHOO FINANCE API (Stocks) =====

    def get_yahoo_ohlc(self, symbol: str, interval: str = "1h", range_str: str = "1mo") -> Dict:
        """
        Fetch OHLC data from Yahoo Finance

        Args:
            symbol: Stock ticker (e.g., 'AAPL', 'TSLA', 'SPY')
            interval: Timeframe (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            range_str: Time range (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

        Returns:
            Dict with OHLC data and metadata
        """
        try:
            url = f"{self.yahoo_base_url}/{symbol}"
            params = {
                "interval": interval,
                "range": range_str
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()

            data = response.json()

            if "chart" not in data or "result" not in data["chart"]:
                return {"success": False, "error": "Invalid response from Yahoo Finance"}

            result = data["chart"]["result"][0]

            if "timestamp" not in result or "indicators" not in result:
                return {"success": False, "error": "Missing data in response"}

            timestamps = result["timestamp"]
            quote = result["indicators"]["quote"][0]

            # Convert to standardized format
            candles = []
            for i in range(len(timestamps)):
                # Skip candles with None values
                if (quote["open"][i] is None or quote["high"][i] is None or
                    quote["low"][i] is None or quote["close"][i] is None):
                    continue

                candles.append({
                    "time": timestamps[i],
                    "open": float(quote["open"][i]),
                    "high": float(quote["high"][i]),
                    "low": float(quote["low"][i]),
                    "close": float(quote["close"][i]),
                    "volume": float(quote["volume"][i]) if quote["volume"][i] else 0
                })

            meta = result["meta"]

            return {
                "success": True,
                "symbol": symbol,
                "interval": interval,
                "range": range_str,
                "currency": meta.get("currency", "USD"),
                "exchange": meta.get("exchangeName", ""),
                "candles": candles,
                "count": len(candles)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_yahoo_quote(self, symbols: List[str]) -> Dict:
        """
        Get current quote data for multiple symbols

        Args:
            symbols: List of stock tickers (e.g., ['AAPL', 'TSLA', 'GOOGL'])

        Returns:
            Dict with quote data for each symbol
        """
        try:
            # Yahoo Finance quote endpoint
            url = "https://query1.finance.yahoo.com/v7/finance/quote"
            params = {"symbols": ",".join(symbols)}

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            if "quoteResponse" not in data or "result" not in data["quoteResponse"]:
                return {"success": False, "error": "Invalid response from Yahoo Finance"}

            # Standardize quote format
            quotes = {}
            for quote_data in data["quoteResponse"]["result"]:
                symbol = quote_data.get("symbol")
                quotes[symbol] = {
                    "price": quote_data.get("regularMarketPrice", 0),
                    "change": quote_data.get("regularMarketChange", 0),
                    "change_percent": quote_data.get("regularMarketChangePercent", 0),
                    "volume": quote_data.get("regularMarketVolume", 0),
                    "market_cap": quote_data.get("marketCap", 0),
                    "name": quote_data.get("longName", quote_data.get("shortName", symbol)),
                    "exchange": quote_data.get("fullExchangeName", ""),
                    "currency": quote_data.get("currency", "USD"),
                    "high": quote_data.get("regularMarketDayHigh", 0),
                    "low": quote_data.get("regularMarketDayLow", 0),
                    "open": quote_data.get("regularMarketOpen", 0),
                    "prev_close": quote_data.get("regularMarketPreviousClose", 0)
                }

            return {"success": True, "quotes": quotes}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ===== REALISTIC DATA GENERATION =====

    def generate_realistic_ohlc(self, current_price: float, timeframe: str, num_candles: int = 200) -> List[Dict]:
        """
        Generate realistic OHLCV data based on current price using Geometric Brownian Motion

        Args:
            current_price: Current market price
            timeframe: Timeframe string (1m, 5m, 1h, etc.)
            num_candles: Number of candles to generate

        Returns:
            List of OHLCV candles
        """
        # Volatility parameters based on timeframe
        volatility_map = {
            "1m": 0.001,
            "5m": 0.003,
            "15m": 0.005,
            "30m": 0.008,
            "1h": 0.01,
            "4h": 0.02,
            "1d": 0.03,
            "1w": 0.05,
            "1M": 0.08
        }

        volatility = volatility_map.get(timeframe, 0.01)

        # Interval in seconds
        interval_map = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "30m": 1800,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400,
            "1w": 604800,
            "1M": 2592000
        }

        interval = interval_map.get(timeframe, 3600)

        candles = []
        current_time = int(time.time())
        price = current_price

        for i in range(num_candles):
            # Generate OHLC using GBM
            # Add trend component (sine wave for realistic market cycles)
            trend = math.sin(i / num_candles * math.pi * 2) * current_price * 0.02

            # Random walk component
            drift = random.gauss(0, volatility * price)

            # Calculate open
            open_price = price

            # Generate high/low with realistic spread
            high_low_spread = abs(random.gauss(0, volatility * price * 0.5))
            high = open_price + high_low_spread
            low = open_price - high_low_spread

            # Calculate close with trend and drift
            close = open_price + trend + drift

            # Ensure close is within high/low range
            close = max(low, min(high, close))

            # Generate realistic volume (with some randomness)
            base_volume = random.uniform(100000, 1000000)
            volatility_multiplier = 1 + abs(close - open_price) / open_price * 10
            volume = base_volume * volatility_multiplier

            candles.insert(0, {
                "time": current_time - (i * interval),
                "open": round(open_price, 8),
                "high": round(high, 8),
                "low": round(low, 8),
                "close": round(close, 8),
                "volume": round(volume, 2)
            })

            # Update price for next candle
            price = close

        return candles

    # ===== HELPER FUNCTIONS =====

    @staticmethod
    def convert_timeframe_to_kraken(timeframe: str) -> int:
        """Convert standard timeframe string to Kraken interval (minutes)"""
        mapping = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "4h": 240,
            "1d": 1440,
            "1w": 10080,
            "1M": 21600
        }
        return mapping.get(timeframe, 60)

    @staticmethod
    def convert_timeframe_to_yahoo(timeframe: str) -> Tuple[str, str]:
        """Convert standard timeframe to Yahoo Finance interval and range"""
        mapping = {
            "1m": ("1m", "1d"),
            "5m": ("5m", "5d"),
            "15m": ("15m", "5d"),
            "30m": ("30m", "1mo"),
            "1h": ("1h", "1mo"),
            "4h": ("1h", "3mo"),
            "1d": ("1d", "1y"),
            "1w": ("1wk", "5y"),
            "1M": ("1mo", "10y")
        }
        return mapping.get(timeframe, ("1h", "1mo"))

    @staticmethod
    def standardize_kraken_pair(symbol: str) -> str:
        """Convert common symbol to Kraken pair format"""
        mapping = {
            "BTC": "XBTUSD",
            "ETH": "ETHUSD",
            "SOL": "SOLUSD",
            "BNB": "BNBUSD",  # Note: BNB might not be on Kraken
            "XRP": "XRPUSD",
            "ADA": "ADAUSD",
            "DOGE": "XDGUSD",
            "AVAX": "AVAXUSD",
            "DOT": "DOTUSD",
            "MATIC": "MATICUSD"
        }
        return mapping.get(symbol.upper(), f"{symbol.upper()}USD")


# Singleton instance
market_data_service = MarketDataService()
