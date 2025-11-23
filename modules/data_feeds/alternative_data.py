"""
Alternative Data Sources - Beyond Price Data
Sentiment, On-Chain Metrics, Funding Rates, Order Flow
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import json
import re


logger = logging.getLogger(__name__)


@dataclass
class SentimentData:
    """Social sentiment metrics"""
    symbol: str
    overall_score: float  # -1 (bearish) to +1 (bullish)
    twitter_sentiment: float
    reddit_sentiment: float
    news_sentiment: float
    social_volume: int
    social_dominance: float
    fear_greed_index: int  # 0-100
    timestamp: datetime


@dataclass
class OnChainData:
    """Blockchain metrics"""
    symbol: str
    active_addresses: int
    transaction_count: int
    transaction_volume: float
    exchange_inflow: float  # Coins moving to exchanges (sell pressure)
    exchange_outflow: float  # Coins leaving exchanges (accumulation)
    exchange_netflow: float  # net = inflow - outflow
    whale_transactions: int  # Large transactions > $100k
    holder_composition: Dict[str, float]  # Distribution by holder size
    nvt_ratio: float  # Network Value to Transactions
    mvrv_ratio: float  # Market Value to Realized Value
    timestamp: datetime


@dataclass
class FundingData:
    """Perpetual futures funding rates"""
    symbol: str
    funding_rate: float  # Current funding rate
    predicted_rate: float  # Next funding rate
    open_interest: float  # Total open interest
    open_interest_change: float  # 24h change
    long_short_ratio: float  # Longs / Shorts
    liquidations_24h: float  # Total liquidations
    liquidations_long: float
    liquidations_short: float
    timestamp: datetime


@dataclass
class OrderFlowData:
    """Order flow and market microstructure"""
    symbol: str
    buy_volume: float
    sell_volume: float
    volume_delta: float  # buy - sell
    cvd: float  # Cumulative Volume Delta
    large_buy_orders: int  # Orders > $50k
    large_sell_orders: int
    bid_ask_imbalance: float  # -1 to +1
    trade_intensity: float  # Trades per minute
    avg_trade_size: float
    timestamp: datetime


class AlternativeDataFeed:
    """
    Aggregates alternative data from multiple sources

    Data Sources:
    - Sentiment: LunarCrush, Santiment, Fear & Greed Index
    - On-Chain: Glassnode, IntoTheBlock, CryptoQuant
    - Funding: Exchange APIs (Binance, FTX style)
    - Order Flow: Real-time trade aggregation
    """

    # Free/freemium API endpoints
    ENDPOINTS = {
        "fear_greed": "https://api.alternative.me/fng/",
        "coingecko": "https://api.coingecko.com/api/v3",
        "binance_funding": "https://fapi.binance.com/fapi/v1/fundingRate",
        "binance_oi": "https://fapi.binance.com/fapi/v1/openInterest",
        "binance_long_short": "https://fapi.binance.com/futures/data/globalLongShortAccountRatio",
    }

    def __init__(
        self,
        api_keys: Optional[Dict[str, str]] = None,
        cache_ttl: int = 300  # 5 minutes
    ):
        self.api_keys = api_keys or {}
        self.cache_ttl = cache_ttl

        # Data caches
        self._sentiment_cache: Dict[str, SentimentData] = {}
        self._onchain_cache: Dict[str, OnChainData] = {}
        self._funding_cache: Dict[str, FundingData] = {}
        self._orderflow_cache: Dict[str, OrderFlowData] = {}

        # Cache timestamps
        self._cache_times: Dict[str, datetime] = {}

        # HTTP session
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close HTTP session"""
        if self._session:
            await self._session.close()

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid"""
        if key not in self._cache_times:
            return False
        return (datetime.now() - self._cache_times[key]).seconds < self.cache_ttl

    # ========== Sentiment Data ==========

    async def get_sentiment(self, symbol: str = "BTC") -> Optional[SentimentData]:
        """Get aggregated sentiment data"""
        cache_key = f"sentiment_{symbol}"

        if self._is_cache_valid(cache_key) and symbol in self._sentiment_cache:
            return self._sentiment_cache[symbol]

        try:
            # Fetch Fear & Greed Index
            fear_greed = await self._fetch_fear_greed()

            # Aggregate sentiment (using available free sources)
            sentiment = SentimentData(
                symbol=symbol,
                overall_score=self._normalize_fear_greed(fear_greed),
                twitter_sentiment=0.0,  # Would need paid API
                reddit_sentiment=0.0,
                news_sentiment=0.0,
                social_volume=0,
                social_dominance=0.0,
                fear_greed_index=fear_greed,
                timestamp=datetime.now()
            )

            self._sentiment_cache[symbol] = sentiment
            self._cache_times[cache_key] = datetime.now()

            return sentiment

        except Exception as e:
            logger.error(f"Error fetching sentiment: {e}")
            return self._sentiment_cache.get(symbol)

    async def _fetch_fear_greed(self) -> int:
        """Fetch Fear & Greed Index"""
        try:
            session = await self._get_session()
            async with session.get(self.ENDPOINTS["fear_greed"]) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return int(data["data"][0]["value"])
        except Exception as e:
            logger.error(f"Fear & Greed API error: {e}")
        return 50  # Neutral default

    def _normalize_fear_greed(self, value: int) -> float:
        """Convert Fear & Greed (0-100) to sentiment score (-1 to +1)"""
        return (value - 50) / 50

    # ========== On-Chain Data ==========

    async def get_onchain_metrics(self, symbol: str = "BTC") -> Optional[OnChainData]:
        """Get on-chain metrics (simplified without paid APIs)"""
        cache_key = f"onchain_{symbol}"

        if self._is_cache_valid(cache_key) and symbol in self._onchain_cache:
            return self._onchain_cache[symbol]

        try:
            # CoinGecko provides some basic metrics
            cg_data = await self._fetch_coingecko_data(symbol.lower())

            onchain = OnChainData(
                symbol=symbol,
                active_addresses=0,  # Would need Glassnode
                transaction_count=0,
                transaction_volume=cg_data.get("total_volume", {}).get("usd", 0),
                exchange_inflow=0,  # Would need CryptoQuant
                exchange_outflow=0,
                exchange_netflow=0,
                whale_transactions=0,
                holder_composition={},
                nvt_ratio=0,
                mvrv_ratio=0,
                timestamp=datetime.now()
            )

            self._onchain_cache[symbol] = onchain
            self._cache_times[cache_key] = datetime.now()

            return onchain

        except Exception as e:
            logger.error(f"Error fetching on-chain data: {e}")
            return self._onchain_cache.get(symbol)

    async def _fetch_coingecko_data(self, coin_id: str) -> Dict:
        """Fetch data from CoinGecko"""
        try:
            session = await self._get_session()
            url = f"{self.ENDPOINTS['coingecko']}/coins/{coin_id}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"CoinGecko API error: {e}")
        return {}

    # ========== Funding Rate Data ==========

    async def get_funding_data(self, symbol: str = "BTCUSDT") -> Optional[FundingData]:
        """Get perpetual futures funding data from Binance"""
        cache_key = f"funding_{symbol}"

        if self._is_cache_valid(cache_key) and symbol in self._funding_cache:
            return self._funding_cache[symbol]

        try:
            session = await self._get_session()

            # Fetch funding rate
            funding_url = f"{self.ENDPOINTS['binance_funding']}?symbol={symbol}&limit=1"
            async with session.get(funding_url) as resp:
                funding_data = await resp.json() if resp.status == 200 else []

            # Fetch open interest
            oi_url = f"{self.ENDPOINTS['binance_oi']}?symbol={symbol}"
            async with session.get(oi_url) as resp:
                oi_data = await resp.json() if resp.status == 200 else {}

            # Fetch long/short ratio
            ls_url = f"{self.ENDPOINTS['binance_long_short']}?symbol={symbol}&period=1h&limit=1"
            async with session.get(ls_url) as resp:
                ls_data = await resp.json() if resp.status == 200 else []

            funding = FundingData(
                symbol=symbol,
                funding_rate=float(funding_data[0]["fundingRate"]) if funding_data else 0,
                predicted_rate=0,  # Would need additional API
                open_interest=float(oi_data.get("openInterest", 0)),
                open_interest_change=0,
                long_short_ratio=float(ls_data[0]["longShortRatio"]) if ls_data else 1.0,
                liquidations_24h=0,  # Would need websocket
                liquidations_long=0,
                liquidations_short=0,
                timestamp=datetime.now()
            )

            self._funding_cache[symbol] = funding
            self._cache_times[cache_key] = datetime.now()

            return funding

        except Exception as e:
            logger.error(f"Error fetching funding data: {e}")
            return self._funding_cache.get(symbol)

    # ========== Order Flow Analysis ==========

    async def get_orderflow(self, symbol: str) -> Optional[OrderFlowData]:
        """Get order flow metrics (requires real-time trade feed)"""
        # This would normally aggregate from websocket trade stream
        # For now, return cached/placeholder data
        return self._orderflow_cache.get(symbol)

    def update_orderflow(self, symbol: str, trade: Dict):
        """Update order flow from incoming trade"""
        if symbol not in self._orderflow_cache:
            self._orderflow_cache[symbol] = OrderFlowData(
                symbol=symbol,
                buy_volume=0,
                sell_volume=0,
                volume_delta=0,
                cvd=0,
                large_buy_orders=0,
                large_sell_orders=0,
                bid_ask_imbalance=0,
                trade_intensity=0,
                avg_trade_size=0,
                timestamp=datetime.now()
            )

        flow = self._orderflow_cache[symbol]

        # Update based on trade
        is_buy = trade.get("side", "").lower() == "buy"
        amount = float(trade.get("amount", 0))
        price = float(trade.get("price", 0))
        value = amount * price

        if is_buy:
            flow.buy_volume += value
            if value > 50000:
                flow.large_buy_orders += 1
        else:
            flow.sell_volume += value
            if value > 50000:
                flow.large_sell_orders += 1

        flow.volume_delta = flow.buy_volume - flow.sell_volume
        flow.cvd += value if is_buy else -value
        flow.timestamp = datetime.now()

    # ========== Aggregated Signals ==========

    async def get_alternative_signals(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Get aggregated alternative data signals"""
        perp_symbol = f"{symbol}USDT"

        # Fetch all data sources
        sentiment = await self.get_sentiment(symbol)
        onchain = await self.get_onchain_metrics(symbol)
        funding = await self.get_funding_data(perp_symbol)
        orderflow = await self.get_orderflow(symbol)

        signals = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
        }

        # Sentiment signal
        if sentiment:
            signals["sentiment"] = {
                "score": sentiment.overall_score,
                "fear_greed": sentiment.fear_greed_index,
                "signal": "bullish" if sentiment.overall_score > 0.2 else "bearish" if sentiment.overall_score < -0.2 else "neutral"
            }

        # Funding signal
        if funding:
            # High positive funding = crowded long (bearish)
            # High negative funding = crowded short (bullish)
            funding_signal = -funding.funding_rate * 1000  # Scale up
            signals["funding"] = {
                "rate": funding.funding_rate,
                "rate_annualized": funding.funding_rate * 3 * 365 * 100,  # Approx APR
                "open_interest": funding.open_interest,
                "long_short_ratio": funding.long_short_ratio,
                "signal": "bullish" if funding_signal > 0.1 else "bearish" if funding_signal < -0.1 else "neutral"
            }

        # Order flow signal
        if orderflow:
            imbalance = orderflow.volume_delta / (orderflow.buy_volume + orderflow.sell_volume + 1)
            signals["orderflow"] = {
                "buy_volume": orderflow.buy_volume,
                "sell_volume": orderflow.sell_volume,
                "cvd": orderflow.cvd,
                "imbalance": imbalance,
                "signal": "bullish" if imbalance > 0.1 else "bearish" if imbalance < -0.1 else "neutral"
            }

        # Combined signal
        bullish_count = sum(1 for k, v in signals.items() if isinstance(v, dict) and v.get("signal") == "bullish")
        bearish_count = sum(1 for k, v in signals.items() if isinstance(v, dict) and v.get("signal") == "bearish")

        if bullish_count > bearish_count + 1:
            signals["combined_signal"] = "bullish"
            signals["combined_strength"] = bullish_count / max(bullish_count + bearish_count, 1)
        elif bearish_count > bullish_count + 1:
            signals["combined_signal"] = "bearish"
            signals["combined_strength"] = bearish_count / max(bullish_count + bearish_count, 1)
        else:
            signals["combined_signal"] = "neutral"
            signals["combined_strength"] = 0.5

        return signals


# Edge Detection Signals
class EdgeDetector:
    """
    Detect tradeable edges from alternative data

    Edges to exploit:
    1. Funding rate arbitrage (high funding = expect reversal)
    2. Sentiment extremes (fear = buy, greed = sell)
    3. Order flow imbalance (large buyer/seller walls)
    4. Exchange flow (inflow = sell pressure coming)
    """

    def __init__(self, data_feed: AlternativeDataFeed):
        self.data_feed = data_feed

        # Thresholds
        self.funding_threshold = 0.01  # 1% funding = extreme
        self.sentiment_threshold = 25  # Fear & Greed extremes
        self.flow_threshold = 0.3  # 30% imbalance

    async def detect_edges(self, symbol: str) -> List[Dict]:
        """Detect all current edges for a symbol"""
        edges = []

        signals = await self.data_feed.get_alternative_signals(symbol)

        # Edge 1: Funding rate extreme
        if "funding" in signals:
            rate = signals["funding"]["rate"]
            if abs(rate) > self.funding_threshold:
                edges.append({
                    "type": "funding_extreme",
                    "direction": "short" if rate > 0 else "long",
                    "strength": min(abs(rate) / self.funding_threshold, 2.0),
                    "reason": f"Funding rate at {rate*100:.2f}% - crowd positioned {'long' if rate > 0 else 'short'}"
                })

        # Edge 2: Sentiment extreme
        if "sentiment" in signals:
            fg = signals["sentiment"]["fear_greed"]
            if fg < self.sentiment_threshold:
                edges.append({
                    "type": "sentiment_extreme",
                    "direction": "long",
                    "strength": (self.sentiment_threshold - fg) / self.sentiment_threshold,
                    "reason": f"Extreme fear (F&G: {fg}) - contrarian buy"
                })
            elif fg > (100 - self.sentiment_threshold):
                edges.append({
                    "type": "sentiment_extreme",
                    "direction": "short",
                    "strength": (fg - (100 - self.sentiment_threshold)) / self.sentiment_threshold,
                    "reason": f"Extreme greed (F&G: {fg}) - contrarian sell"
                })

        # Edge 3: Order flow imbalance
        if "orderflow" in signals:
            imbalance = signals["orderflow"]["imbalance"]
            if abs(imbalance) > self.flow_threshold:
                edges.append({
                    "type": "orderflow_imbalance",
                    "direction": "long" if imbalance > 0 else "short",
                    "strength": min(abs(imbalance) / self.flow_threshold, 2.0),
                    "reason": f"Strong {'buying' if imbalance > 0 else 'selling'} pressure"
                })

        return edges

    async def get_trade_recommendation(self, symbol: str) -> Dict:
        """Get trade recommendation based on detected edges"""
        edges = await self.detect_edges(symbol)

        if not edges:
            return {
                "action": "hold",
                "confidence": 0,
                "reason": "No significant edges detected"
            }

        # Aggregate edge directions
        long_strength = sum(e["strength"] for e in edges if e["direction"] == "long")
        short_strength = sum(e["strength"] for e in edges if e["direction"] == "short")

        if long_strength > short_strength and long_strength > 1.0:
            return {
                "action": "buy",
                "confidence": min(long_strength / 2, 1.0),
                "edges": [e for e in edges if e["direction"] == "long"],
                "reason": "; ".join(e["reason"] for e in edges if e["direction"] == "long")
            }
        elif short_strength > long_strength and short_strength > 1.0:
            return {
                "action": "sell",
                "confidence": min(short_strength / 2, 1.0),
                "edges": [e for e in edges if e["direction"] == "short"],
                "reason": "; ".join(e["reason"] for e in edges if e["direction"] == "short")
            }
        else:
            return {
                "action": "hold",
                "confidence": 0.5,
                "reason": "Mixed signals - no clear edge"
            }


# Factory function
def create_alternative_feed(api_keys: Optional[Dict[str, str]] = None) -> AlternativeDataFeed:
    """Create alternative data feed instance"""
    return AlternativeDataFeed(api_keys)
