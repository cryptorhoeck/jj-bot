"""
Cached Market Data Service - Intelligent data fetching with caching

Provides a unified interface for market data with automatic caching:
1. Check cache first
2. Return cached data if fresh
3. Fetch from API if cache is stale/missing
4. Store API results in cache
5. Fallback to generated data if API fails
"""

import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from .market_data_service import market_data_service
from .market_data_cache import market_data_cache


class CachedMarketDataService:
    """Market data service with intelligent caching"""

    def __init__(self):
        self.api = market_data_service
        self.cache = market_data_cache

        # Cache freshness settings (in seconds)
        self.cache_ttl = {
            "1m": 60,        # 1 minute data stays fresh for 1 minute
            "5m": 300,       # 5 minutes
            "15m": 900,      # 15 minutes
            "30m": 1800,     # 30 minutes
            "1h": 3600,      # 1 hour
            "4h": 14400,     # 4 hours
            "1d": 86400,     # 1 day
            "1w": 604800,    # 1 week
            "1M": 2592000    # 1 month
        }

    def get_ohlcv(
        self,
        symbol: str,
        source: str,
        timeframe: str = "1h",
        num_candles: int = 200,
        force_refresh: bool = False
    ) -> Dict:
        """
        Get OHLCV data with intelligent caching

        Args:
            symbol: Trading symbol (e.g., 'BTC', 'ETH', 'AAPL')
            source: Data source ('kraken', 'yahoo', 'auto')
            timeframe: Timeframe (e.g., '1m', '5m', '1h', '1d')
            num_candles: Number of candles to return
            force_refresh: Force API fetch even if cache is fresh

        Returns:
            Dict with success status and candles data
        """
        # Auto-detect source based on symbol
        if source == 'auto':
            source = self._detect_source(symbol)

        # Check cache freshness
        ttl = self.cache_ttl.get(timeframe, 3600)
        is_fresh = self.cache.is_cache_fresh(symbol, source, timeframe, max_age_seconds=ttl)

        # Use cache if fresh and not forcing refresh
        if is_fresh and not force_refresh:
            candles = self.cache.get_candles(symbol, source, timeframe, limit=num_candles)
            if candles:
                return {
                    "success": True,
                    "source": source,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "candles": candles,
                    "count": len(candles),
                    "from_cache": True,
                    "cache_age": self.cache.get_cache_age(symbol, source, timeframe)
                }

        # Cache miss or stale - fetch from API
        api_result = self._fetch_from_api(symbol, source, timeframe, num_candles)

        if api_result["success"]:
            # Store in cache
            inserted = self.cache.store_candles(
                symbol, source, timeframe, api_result["candles"]
            )
            print(f"💾 Cached {inserted} candles for {symbol} ({source}, {timeframe})")

            return {
                **api_result,
                "from_cache": False,
                "cached_count": inserted
            }
        else:
            # API failed - try to return stale cache data as fallback
            print(f"⚠️  API fetch failed: {api_result.get('error')}")
            candles = self.cache.get_candles(symbol, source, timeframe, limit=num_candles)

            if candles:
                print(f"ℹ️  Returning stale cached data (age: {self.cache.get_cache_age(symbol, source, timeframe)}s)")
                return {
                    "success": True,
                    "source": source,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "candles": candles,
                    "count": len(candles),
                    "from_cache": True,
                    "cache_stale": True,
                    "api_error": api_result.get('error')
                }
            else:
                # No cache available - generate realistic data as last resort
                print(f"ℹ️  Generating realistic data for {symbol}")
                return self._generate_fallback_data(symbol, timeframe, num_candles)

    def _fetch_from_api(self, symbol: str, source: str, timeframe: str, num_candles: int) -> Dict:
        """Fetch data from appropriate API based on source"""
        if source == 'kraken':
            return self._fetch_from_kraken(symbol, timeframe)
        elif source == 'yahoo':
            return self._fetch_from_yahoo(symbol, timeframe)
        else:
            return {"success": False, "error": f"Unknown source: {source}"}

    def _fetch_from_kraken(self, symbol: str, timeframe: str) -> Dict:
        """Fetch data from Kraken API"""
        pair = self.api.standardize_kraken_pair(symbol)
        interval = self.api.convert_timeframe_to_kraken(timeframe)

        result = self.api.get_kraken_ohlc(pair, interval)

        if result["success"]:
            return {
                "success": True,
                "source": "kraken",
                "symbol": symbol,
                "timeframe": timeframe,
                "candles": result["candles"],
                "count": result["count"]
            }
        else:
            return {"success": False, "error": result.get("error", "Unknown error")}

    def _fetch_from_yahoo(self, symbol: str, timeframe: str) -> Dict:
        """Fetch data from Yahoo Finance API"""
        interval, range_str = self.api.convert_timeframe_to_yahoo(timeframe)

        result = self.api.get_yahoo_ohlc(symbol, interval, range_str)

        if result["success"]:
            return {
                "success": True,
                "source": "yahoo",
                "symbol": symbol,
                "timeframe": timeframe,
                "candles": result["candles"],
                "count": result["count"]
            }
        else:
            return {"success": False, "error": result.get("error", "Unknown error")}

    def _generate_fallback_data(self, symbol: str, timeframe: str, num_candles: int) -> Dict:
        """Generate realistic data when API and cache both fail"""
        # Use a reasonable default price based on symbol
        default_prices = {
            "BTC": 45000.0,
            "ETH": 2500.0,
            "SOL": 100.0,
            "AAPL": 180.0,
            "TSLA": 250.0,
            "SPY": 450.0
        }

        current_price = default_prices.get(symbol.upper(), 100.0)
        candles = self.api.generate_realistic_ohlc(current_price, timeframe, num_candles)

        # Cache generated data for consistency
        self.cache.store_candles(symbol, "generated", timeframe, candles)

        return {
            "success": True,
            "source": "generated",
            "symbol": symbol,
            "timeframe": timeframe,
            "candles": candles,
            "count": len(candles),
            "from_cache": False,
            "warning": "Generated realistic data - API unavailable"
        }

    def _detect_source(self, symbol: str) -> str:
        """Auto-detect data source based on symbol"""
        crypto_symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'AVAX', 'DOT', 'MATIC']

        if symbol.upper() in crypto_symbols:
            return 'kraken'
        else:
            return 'yahoo'

    def get_current_price(self, symbol: str, source: str = 'auto') -> Dict:
        """
        Get current price for a symbol

        Args:
            symbol: Trading symbol
            source: Data source ('kraken', 'yahoo', 'auto')

        Returns:
            Dict with current price data
        """
        if source == 'auto':
            source = self._detect_source(symbol)

        if source == 'kraken':
            pair = self.api.standardize_kraken_pair(symbol)
            result = self.api.get_kraken_ticker([pair])

            if result["success"] and pair in result["tickers"]:
                ticker = result["tickers"][pair]
                return {
                    "success": True,
                    "symbol": symbol,
                    "price": ticker["last"],
                    "volume": ticker["volume"],
                    "high": ticker["high"],
                    "low": ticker["low"],
                    "source": "kraken"
                }

        elif source == 'yahoo':
            result = self.api.get_yahoo_quote([symbol])

            if result["success"] and symbol in result["quotes"]:
                quote = result["quotes"][symbol]
                return {
                    "success": True,
                    "symbol": symbol,
                    "price": quote["price"],
                    "volume": quote["volume"],
                    "high": quote["high"],
                    "low": quote["low"],
                    "source": "yahoo"
                }

        # Fallback - get from latest cached candle
        latest = self.cache.get_latest_candle(symbol, source, "1h")
        if latest:
            return {
                "success": True,
                "symbol": symbol,
                "price": latest["close"],
                "source": f"{source}_cache",
                "from_cache": True
            }

        return {"success": False, "error": "Unable to fetch current price"}

    def preload_cache(
        self,
        symbols: List[str],
        sources: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None
    ) -> Dict:
        """
        Preload cache with data for multiple symbols

        Args:
            symbols: List of symbols to cache
            sources: List of sources (default: auto-detect)
            timeframes: List of timeframes (default: ['1h', '1d'])

        Returns:
            Dict with statistics about the preload operation
        """
        if timeframes is None:
            timeframes = ['1h', '1d']

        stats = {
            "symbols_processed": 0,
            "candles_cached": 0,
            "errors": []
        }

        for symbol in symbols:
            source = sources[0] if sources else self._detect_source(symbol)

            for timeframe in timeframes:
                try:
                    result = self.get_ohlcv(symbol, source, timeframe, force_refresh=True)
                    if result["success"]:
                        stats["candles_cached"] += result.get("cached_count", 0)
                    else:
                        stats["errors"].append(f"{symbol}/{timeframe}: {result.get('error')}")
                except Exception as e:
                    stats["errors"].append(f"{symbol}/{timeframe}: {str(e)}")

                # Rate limiting - be nice to APIs
                time.sleep(0.5)

            stats["symbols_processed"] += 1

        return stats

    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return self.cache.get_statistics()

    def clear_old_cache(self, days: int = 7) -> int:
        """
        Clear cached data older than X days

        Args:
            days: Age threshold in days

        Returns:
            Number of candles deleted
        """
        seconds = days * 86400
        deleted = self.cache.clear_cache(older_than_seconds=seconds)
        print(f"🗑️  Deleted {deleted} candles older than {days} days")
        return deleted


# Singleton instance
cached_market_data_service = CachedMarketDataService()
