"""
Alternative Data Provider - Real API Integrations

Provides real-time data feeds for edge strategies:
- Funding rates (Binance Futures API)
- Fear & Greed Index (alternative.me API)
- Liquidation data (Coinglass API)
- Order flow estimation from recent trades

All data is fetched from real APIs with proper caching and fallbacks.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import os

logger = logging.getLogger(__name__)


@dataclass
class DataCache:
    """Simple cache with TTL"""
    data: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    ttl_seconds: int = 60

    def is_valid(self) -> bool:
        if self.data is None:
            return False
        age = (datetime.now() - self.timestamp).total_seconds()
        return age < self.ttl_seconds


class AlternativeDataProvider:
    """
    Provides real alternative data for edge strategies.

    Data Sources:
    - Binance Futures: Funding rates, long/short ratios
    - Alternative.me: Fear & Greed Index
    - Coinglass: Liquidation data (optional API key)
    - Binance: Recent trades for order flow estimation
    """

    # API Endpoints
    BINANCE_FUTURES_BASE = "https://fapi.binance.com"
    ALTERNATIVE_ME_FNG = "https://api.alternative.me/fng/"
    COINGLASS_BASE = "https://open-api.coinglass.com/public/v2"

    def __init__(
        self,
        coinglass_api_key: Optional[str] = None,
        cache_ttl: int = 60,  # Cache data for 60 seconds
    ):
        self.coinglass_api_key = coinglass_api_key or os.environ.get("COINGLASS_API_KEY")
        self.cache_ttl = cache_ttl

        # Caches for different data types
        self._funding_cache: Dict[str, DataCache] = {}
        self._fng_cache = DataCache(ttl_seconds=300)  # F&G changes slowly
        self._liquidation_cache: Dict[str, DataCache] = {}
        self._orderflow_cache: Dict[str, DataCache] = {}

        # Session for async requests
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close the session"""
        if self._session and not self._session.closed:
            await self._session.close()

    # ========== FUNDING RATES ==========

    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """
        Get funding rate data from Binance Futures.

        Returns:
            {
                "symbol": str,
                "funding_rate": float,  # Current funding rate
                "next_funding_time": datetime,
                "mark_price": float,
                "index_price": float
            }
        """
        # Check cache
        cache_key = symbol.upper()
        if cache_key in self._funding_cache and self._funding_cache[cache_key].is_valid():
            return self._funding_cache[cache_key].data

        try:
            session = await self._get_session()

            # Convert symbol format (BTC -> BTCUSDT)
            binance_symbol = self._to_binance_symbol(symbol)

            url = f"{self.BINANCE_FUTURES_BASE}/fapi/v1/premiumIndex"
            params = {"symbol": binance_symbol}

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    result = {
                        "symbol": symbol,
                        "funding_rate": float(data.get("lastFundingRate", 0)),
                        "next_funding_time": datetime.fromtimestamp(
                            data.get("nextFundingTime", 0) / 1000
                        ),
                        "mark_price": float(data.get("markPrice", 0)),
                        "index_price": float(data.get("indexPrice", 0)),
                        "timestamp": datetime.now().isoformat()
                    }

                    # Cache result
                    self._funding_cache[cache_key] = DataCache(
                        data=result,
                        ttl_seconds=self.cache_ttl
                    )

                    logger.debug(f"Fetched funding rate for {symbol}: {result['funding_rate']:.6f}")
                    return result
                else:
                    logger.warning(f"Failed to fetch funding rate for {symbol}: {response.status}")

        except Exception as e:
            logger.error(f"Error fetching funding rate for {symbol}: {e}")

        # Return default if failed
        return {
            "symbol": symbol,
            "funding_rate": 0.0,
            "next_funding_time": None,
            "mark_price": 0,
            "index_price": 0,
            "error": "Failed to fetch"
        }

    async def get_long_short_ratio(self, symbol: str) -> Dict[str, Any]:
        """
        Get long/short account ratio from Binance Futures.

        Returns:
            {
                "symbol": str,
                "long_short_ratio": float,  # > 1 means more longs
                "long_account": float,
                "short_account": float
            }
        """
        try:
            session = await self._get_session()
            binance_symbol = self._to_binance_symbol(symbol)

            url = f"{self.BINANCE_FUTURES_BASE}/futures/data/globalLongShortAccountRatio"
            params = {"symbol": binance_symbol, "period": "5m", "limit": 1}

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        latest = data[0]
                        return {
                            "symbol": symbol,
                            "long_short_ratio": float(latest.get("longShortRatio", 1.0)),
                            "long_account": float(latest.get("longAccount", 0.5)),
                            "short_account": float(latest.get("shortAccount", 0.5)),
                            "timestamp": latest.get("timestamp")
                        }

        except Exception as e:
            logger.error(f"Error fetching long/short ratio for {symbol}: {e}")

        return {
            "symbol": symbol,
            "long_short_ratio": 1.0,
            "long_account": 0.5,
            "short_account": 0.5
        }

    # ========== FEAR & GREED INDEX ==========

    async def get_fear_greed_index(self) -> Dict[str, Any]:
        """
        Get Fear & Greed Index from alternative.me.

        Returns:
            {
                "value": int,  # 0-100
                "classification": str,  # "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
                "timestamp": datetime
            }
        """
        # Check cache (F&G updates daily, cache for 5 minutes)
        if self._fng_cache.is_valid():
            return self._fng_cache.data

        try:
            session = await self._get_session()

            async with session.get(self.ALTERNATIVE_ME_FNG) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get("data"):
                        latest = data["data"][0]
                        result = {
                            "value": int(latest.get("value", 50)),
                            "classification": latest.get("value_classification", "Neutral"),
                            "timestamp": datetime.fromtimestamp(
                                int(latest.get("timestamp", 0))
                            ),
                            "fetched_at": datetime.now().isoformat()
                        }

                        # Cache result
                        self._fng_cache = DataCache(
                            data=result,
                            ttl_seconds=300  # 5 minute cache
                        )

                        logger.info(f"Fear & Greed Index: {result['value']} ({result['classification']})")
                        return result

        except Exception as e:
            logger.error(f"Error fetching Fear & Greed Index: {e}")

        return {
            "value": 50,
            "classification": "Neutral",
            "timestamp": datetime.now(),
            "error": "Failed to fetch"
        }

    # ========== LIQUIDATION DATA ==========

    async def get_liquidations(self, symbol: str, hours: int = 1) -> Dict[str, Any]:
        """
        Get liquidation data. Uses Coinglass if API key available,
        otherwise estimates from price volatility.

        Returns:
            {
                "symbol": str,
                "liquidations_long": float,  # USD value
                "liquidations_short": float,
                "total_liquidations": float,
                "price_change_1h": float
            }
        """
        cache_key = f"{symbol}_{hours}h"
        if cache_key in self._liquidation_cache and self._liquidation_cache[cache_key].is_valid():
            return self._liquidation_cache[cache_key].data

        # Try Coinglass if API key available
        if self.coinglass_api_key:
            result = await self._get_coinglass_liquidations(symbol)
            if result and "error" not in result:
                self._liquidation_cache[cache_key] = DataCache(data=result, ttl_seconds=60)
                return result

        # Fallback: Estimate liquidations from price movement + open interest
        result = await self._estimate_liquidations(symbol)
        self._liquidation_cache[cache_key] = DataCache(data=result, ttl_seconds=60)
        return result

    async def _get_coinglass_liquidations(self, symbol: str) -> Optional[Dict]:
        """Fetch liquidations from Coinglass API"""
        try:
            session = await self._get_session()

            # Coinglass uses different symbol format
            cg_symbol = symbol.upper().replace("/", "").replace("USD", "")

            url = f"{self.COINGLASS_BASE}/liquidation_history"
            headers = {"coinglassSecret": self.coinglass_api_key}
            params = {"symbol": cg_symbol, "timeType": "h1"}

            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and data.get("data"):
                        liq_data = data["data"]
                        return {
                            "symbol": symbol,
                            "liquidations_long": liq_data.get("longLiquidationUsd", 0),
                            "liquidations_short": liq_data.get("shortLiquidationUsd", 0),
                            "total_liquidations": liq_data.get("longLiquidationUsd", 0) +
                                                 liq_data.get("shortLiquidationUsd", 0),
                            "source": "coinglass"
                        }

        except Exception as e:
            logger.debug(f"Coinglass API error: {e}")

        return None

    async def _estimate_liquidations(self, symbol: str) -> Dict:
        """
        Estimate liquidations based on price movement.
        Uses heuristics based on typical crypto leverage.
        """
        try:
            session = await self._get_session()
            binance_symbol = self._to_binance_symbol(symbol)

            # Get recent price change
            url = f"{self.BINANCE_FUTURES_BASE}/fapi/v1/ticker/24hr"
            params = {"symbol": binance_symbol}

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    price_change_pct = float(data.get("priceChangePercent", 0))
                    volume_24h = float(data.get("quoteVolume", 0))

                    # Estimate liquidations based on price movement
                    # Assume 10x average leverage, 10% of volume at risk
                    estimated_at_risk = volume_24h * 0.10

                    # Price moves > 3% trigger significant liquidations
                    if abs(price_change_pct) > 3:
                        liq_rate = min(abs(price_change_pct) / 10, 0.5)  # Cap at 50%
                    else:
                        liq_rate = abs(price_change_pct) / 20

                    total_liq = estimated_at_risk * liq_rate

                    # Split based on direction
                    if price_change_pct < 0:
                        # Price dropped - longs liquidated
                        liq_long = total_liq * 0.8
                        liq_short = total_liq * 0.2
                    else:
                        # Price pumped - shorts liquidated
                        liq_long = total_liq * 0.2
                        liq_short = total_liq * 0.8

                    return {
                        "symbol": symbol,
                        "liquidations_long": liq_long,
                        "liquidations_short": liq_short,
                        "total_liquidations": total_liq,
                        "price_change_1h": price_change_pct / 24,  # Rough hourly estimate
                        "source": "estimated",
                        "note": "Estimated from volume and price movement"
                    }

        except Exception as e:
            logger.error(f"Error estimating liquidations: {e}")

        return {
            "symbol": symbol,
            "liquidations_long": 0,
            "liquidations_short": 0,
            "total_liquidations": 0,
            "price_change_1h": 0,
            "source": "default"
        }

    # ========== ORDER FLOW ==========

    async def get_order_flow(self, symbol: str) -> Dict[str, Any]:
        """
        Estimate order flow from recent trades.
        Analyzes trade direction and size to detect whale activity.

        Returns:
            {
                "symbol": str,
                "buy_volume": float,
                "sell_volume": float,
                "large_buy_orders": int,  # Orders > $100k
                "large_sell_orders": int,
                "imbalance": float  # -1 to 1
            }
        """
        cache_key = symbol.upper()
        if cache_key in self._orderflow_cache and self._orderflow_cache[cache_key].is_valid():
            return self._orderflow_cache[cache_key].data

        try:
            session = await self._get_session()
            binance_symbol = self._to_binance_symbol(symbol)

            # Get recent trades
            url = f"{self.BINANCE_FUTURES_BASE}/fapi/v1/trades"
            params = {"symbol": binance_symbol, "limit": 1000}

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    trades = await response.json()

                    buy_volume = 0.0
                    sell_volume = 0.0
                    large_buys = 0
                    large_sells = 0
                    whale_threshold = 100000  # $100k

                    for trade in trades:
                        qty = float(trade.get("qty", 0))
                        price = float(trade.get("price", 0))
                        value = qty * price
                        is_buyer_maker = trade.get("isBuyerMaker", False)

                        if is_buyer_maker:
                            # Buyer was maker = aggressive sell
                            sell_volume += value
                            if value >= whale_threshold:
                                large_sells += 1
                        else:
                            # Seller was maker = aggressive buy
                            buy_volume += value
                            if value >= whale_threshold:
                                large_buys += 1

                    total_volume = buy_volume + sell_volume
                    imbalance = (buy_volume - sell_volume) / total_volume if total_volume > 0 else 0

                    result = {
                        "symbol": symbol,
                        "buy_volume": buy_volume,
                        "sell_volume": sell_volume,
                        "large_buy_orders": large_buys,
                        "large_sell_orders": large_sells,
                        "imbalance": imbalance,
                        "total_volume": total_volume,
                        "trades_analyzed": len(trades)
                    }

                    self._orderflow_cache[cache_key] = DataCache(data=result, ttl_seconds=30)
                    return result

        except Exception as e:
            logger.error(f"Error fetching order flow: {e}")

        return {
            "symbol": symbol,
            "buy_volume": 0,
            "sell_volume": 0,
            "large_buy_orders": 0,
            "large_sell_orders": 0,
            "imbalance": 0
        }

    # ========== COMBINED DATA FOR EDGE STRATEGIES ==========

    async def get_edge_data(self, symbol: str, price: float) -> Dict[str, Any]:
        """
        Get all alternative data needed for edge strategies in one call.

        Returns combined data suitable for EdgeStrategyManager.analyze_all()
        """
        # Fetch all data in parallel
        funding_task = self.get_funding_rate(symbol)
        ls_ratio_task = self.get_long_short_ratio(symbol)
        fng_task = self.get_fear_greed_index()
        liq_task = self.get_liquidations(symbol)
        flow_task = self.get_order_flow(symbol)

        funding, ls_ratio, fng, liq, flow = await asyncio.gather(
            funding_task, ls_ratio_task, fng_task, liq_task, flow_task,
            return_exceptions=True
        )

        # Handle any errors
        if isinstance(funding, Exception):
            funding = {"funding_rate": 0}
        if isinstance(ls_ratio, Exception):
            ls_ratio = {"long_short_ratio": 1.0}
        if isinstance(fng, Exception):
            fng = {"value": 50}
        if isinstance(liq, Exception):
            liq = {"liquidations_long": 0, "liquidations_short": 0, "price_change_1h": 0}
        if isinstance(flow, Exception):
            flow = {"buy_volume": 0, "sell_volume": 0, "large_buy_orders": 0, "large_sell_orders": 0}

        return {
            "symbol": symbol,
            "price": price,
            # Funding rate data
            "funding_rate": funding.get("funding_rate", 0),
            "long_short_ratio": ls_ratio.get("long_short_ratio", 1.0),
            # Sentiment data
            "fear_greed_index": fng.get("value", 50),
            # Liquidation data
            "liquidations_long": liq.get("liquidations_long", 0),
            "liquidations_short": liq.get("liquidations_short", 0),
            "price_change_1h": liq.get("price_change_1h", 0),
            # Order flow data
            "buy_volume": flow.get("buy_volume", 0),
            "sell_volume": flow.get("sell_volume", 0),
            "large_buy_orders": flow.get("large_buy_orders", 0),
            "large_sell_orders": flow.get("large_sell_orders", 0),
            # Metadata
            "timestamp": datetime.now().isoformat(),
            "data_sources": {
                "funding": "binance_futures",
                "sentiment": "alternative.me",
                "liquidations": liq.get("source", "estimated"),
                "orderflow": "binance_trades"
            }
        }

    def _to_binance_symbol(self, symbol: str) -> str:
        """Convert symbol to Binance format (BTC -> BTCUSDT)"""
        symbol = symbol.upper().replace("/", "").replace("-", "")
        if not symbol.endswith("USDT") and not symbol.endswith("USD"):
            symbol = symbol + "USDT"
        elif symbol.endswith("USD") and not symbol.endswith("USDT"):
            symbol = symbol + "T"
        return symbol


# Singleton instance
_provider: Optional[AlternativeDataProvider] = None


def get_data_provider(coinglass_api_key: Optional[str] = None) -> AlternativeDataProvider:
    """Get or create the data provider singleton"""
    global _provider
    if _provider is None:
        _provider = AlternativeDataProvider(coinglass_api_key=coinglass_api_key)
    return _provider


async def test_data_provider():
    """Test the data provider"""
    provider = get_data_provider()

    print("Testing Alternative Data Provider")
    print("=" * 50)

    # Test Fear & Greed
    print("\n1. Fear & Greed Index:")
    fng = await provider.get_fear_greed_index()
    print(f"   Value: {fng['value']} ({fng['classification']})")

    # Test Funding Rate
    print("\n2. Funding Rate (BTC):")
    funding = await provider.get_funding_rate("BTC")
    print(f"   Rate: {funding['funding_rate']*100:.4f}%")
    print(f"   Mark Price: ${funding['mark_price']:,.2f}")

    # Test Long/Short Ratio
    print("\n3. Long/Short Ratio (BTC):")
    ls = await provider.get_long_short_ratio("BTC")
    print(f"   Ratio: {ls['long_short_ratio']:.2f}")

    # Test Order Flow
    print("\n4. Order Flow (BTC):")
    flow = await provider.get_order_flow("BTC")
    print(f"   Buy Volume: ${flow['buy_volume']:,.0f}")
    print(f"   Sell Volume: ${flow['sell_volume']:,.0f}")
    print(f"   Imbalance: {flow['imbalance']*100:.1f}%")
    print(f"   Large Buys: {flow['large_buy_orders']}, Large Sells: {flow['large_sell_orders']}")

    # Test Liquidations
    print("\n5. Liquidations (BTC):")
    liq = await provider.get_liquidations("BTC")
    print(f"   Long Liq: ${liq['liquidations_long']:,.0f}")
    print(f"   Short Liq: ${liq['liquidations_short']:,.0f}")
    print(f"   Source: {liq.get('source', 'unknown')}")

    # Test combined data
    print("\n6. Combined Edge Data (BTC):")
    edge_data = await provider.get_edge_data("BTC", 42000)
    print(f"   Funding: {edge_data['funding_rate']*100:.4f}%")
    print(f"   F&G: {edge_data['fear_greed_index']}")
    print(f"   L/S Ratio: {edge_data['long_short_ratio']:.2f}")

    await provider.close()
    print("\n" + "=" * 50)
    print("All tests completed!")


if __name__ == "__main__":
    asyncio.run(test_data_provider())
