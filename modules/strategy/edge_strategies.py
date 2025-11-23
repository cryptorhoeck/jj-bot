"""
Edge-Focused Trading Strategies
Simple strategies that exploit specific market inefficiencies

Philosophy: One good edge > Complex system with no edge
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import numpy as np


logger = logging.getLogger(__name__)


class SignalStrength(Enum):
    NONE = 0
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    VERY_STRONG = 4


@dataclass
class TradeSignal:
    """Trade signal with edge information"""
    symbol: str
    direction: str  # "long", "short", "flat"
    strength: SignalStrength
    confidence: float  # 0-1
    edge_type: str  # Which edge triggered this
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: str = ""
    metadata: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class EdgeStrategy(ABC):
    """Base class for edge-based strategies"""

    def __init__(self, name: str, symbols: List[str]):
        self.name = name
        self.symbols = symbols
        self.enabled = True
        self.last_signals: Dict[str, TradeSignal] = {}

    @abstractmethod
    async def analyze(self, data: Dict) -> Optional[TradeSignal]:
        """Analyze data and return trade signal if edge detected"""
        pass

    def get_position_size(self, signal: TradeSignal, account_equity: float) -> float:
        """Calculate position size based on signal strength"""
        base_size = account_equity * 0.02  # 2% base risk

        multipliers = {
            SignalStrength.WEAK: 0.5,
            SignalStrength.MODERATE: 1.0,
            SignalStrength.STRONG: 1.5,
            SignalStrength.VERY_STRONG: 2.0,
        }

        return base_size * multipliers.get(signal.strength, 1.0) * signal.confidence


class FundingRateArbitrage(EdgeStrategy):
    """
    Funding Rate Edge Strategy

    The Edge:
    - High positive funding = traders paying to be long = crowded long
    - When funding is extreme, price tends to revert (shorts get paid to be short)
    - Exploit: Fade extreme funding rates

    Entry: When funding rate > 0.1% (annualized > 36%)
    Exit: When funding normalizes or take profit hit
    """

    def __init__(
        self,
        symbols: List[str],
        entry_threshold: float = 0.0003,  # 0.03% per 8h = ~33% APR
        exit_threshold: float = 0.0001,   # Exit when normalized
        max_holding_hours: int = 24,
    ):
        super().__init__("funding_arbitrage", symbols)
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.max_holding_hours = max_holding_hours

    async def analyze(self, data: Dict) -> Optional[TradeSignal]:
        """
        Analyze funding rate for arbitrage opportunity

        data should contain:
        - symbol: str
        - funding_rate: float
        - price: float
        - long_short_ratio: float
        """
        symbol = data.get("symbol")
        funding_rate = data.get("funding_rate", 0)
        price = data.get("price", 0)
        ls_ratio = data.get("long_short_ratio", 1.0)

        if abs(funding_rate) < self.entry_threshold:
            return None

        # Determine direction (fade the crowd)
        if funding_rate > self.entry_threshold:
            # Crowded long - go short
            direction = "short"
            strength = self._calculate_strength(funding_rate, self.entry_threshold)
            stop_loss = price * 1.02  # 2% stop
            take_profit = price * 0.97  # 3% target
        elif funding_rate < -self.entry_threshold:
            # Crowded short - go long
            direction = "long"
            strength = self._calculate_strength(-funding_rate, self.entry_threshold)
            stop_loss = price * 0.98
            take_profit = price * 1.03
        else:
            return None

        # Confidence based on how extreme the rate is
        confidence = min(abs(funding_rate) / (self.entry_threshold * 3), 1.0)

        # Boost confidence if long/short ratio confirms
        if direction == "short" and ls_ratio > 1.5:
            confidence = min(confidence * 1.2, 1.0)
        elif direction == "long" and ls_ratio < 0.7:
            confidence = min(confidence * 1.2, 1.0)

        return TradeSignal(
            symbol=symbol,
            direction=direction,
            strength=strength,
            confidence=confidence,
            edge_type="funding_arbitrage",
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason=f"Funding rate extreme: {funding_rate*100:.4f}% - fade crowded {'longs' if direction == 'short' else 'shorts'}",
            metadata={"funding_rate": funding_rate, "ls_ratio": ls_ratio}
        )

    def _calculate_strength(self, rate: float, threshold: float) -> SignalStrength:
        ratio = rate / threshold
        if ratio > 4:
            return SignalStrength.VERY_STRONG
        elif ratio > 2.5:
            return SignalStrength.STRONG
        elif ratio > 1.5:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK


class SentimentExtremeStrategy(EdgeStrategy):
    """
    Sentiment Extreme Edge Strategy

    The Edge:
    - Fear & Greed Index extremes predict reversals
    - "Be fearful when others are greedy, greedy when others are fearful"
    - Historically, extreme fear (< 20) precedes rallies

    Entry: F&G < 20 (extreme fear) or > 80 (extreme greed)
    """

    def __init__(
        self,
        symbols: List[str],
        fear_threshold: int = 20,
        greed_threshold: int = 80,
    ):
        super().__init__("sentiment_extreme", symbols)
        self.fear_threshold = fear_threshold
        self.greed_threshold = greed_threshold

    async def analyze(self, data: Dict) -> Optional[TradeSignal]:
        """
        Analyze sentiment for extreme opportunities

        data should contain:
        - symbol: str
        - fear_greed_index: int (0-100)
        - price: float
        - sentiment_change: float (how fast sentiment changed)
        """
        symbol = data.get("symbol")
        fg_index = data.get("fear_greed_index", 50)
        price = data.get("price", 0)

        if self.fear_threshold < fg_index < self.greed_threshold:
            return None

        if fg_index <= self.fear_threshold:
            # Extreme fear - buy opportunity
            direction = "long"
            strength = self._fear_strength(fg_index)
            confidence = (self.fear_threshold - fg_index) / self.fear_threshold
            stop_loss = price * 0.95  # 5% stop (wider for contrarian)
            take_profit = price * 1.15  # 15% target
            reason = f"Extreme fear (F&G: {fg_index}) - contrarian buy"

        elif fg_index >= self.greed_threshold:
            # Extreme greed - sell opportunity
            direction = "short"
            strength = self._greed_strength(fg_index)
            confidence = (fg_index - self.greed_threshold) / (100 - self.greed_threshold)
            stop_loss = price * 1.05
            take_profit = price * 0.85
            reason = f"Extreme greed (F&G: {fg_index}) - contrarian sell"

        else:
            return None

        return TradeSignal(
            symbol=symbol,
            direction=direction,
            strength=strength,
            confidence=min(confidence, 0.9),  # Cap at 90%
            edge_type="sentiment_extreme",
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason=reason,
            metadata={"fear_greed": fg_index}
        )

    def _fear_strength(self, fg: int) -> SignalStrength:
        if fg <= 5:
            return SignalStrength.VERY_STRONG
        elif fg <= 10:
            return SignalStrength.STRONG
        elif fg <= 15:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK

    def _greed_strength(self, fg: int) -> SignalStrength:
        if fg >= 95:
            return SignalStrength.VERY_STRONG
        elif fg >= 90:
            return SignalStrength.STRONG
        elif fg >= 85:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK


class OrderFlowImbalanceStrategy(EdgeStrategy):
    """
    Order Flow Imbalance Edge Strategy

    The Edge:
    - Large imbalances in buy vs sell volume predict short-term moves
    - Cumulative Volume Delta (CVD) divergences signal reversals
    - Large orders (whale activity) often precede moves

    Entry: Significant buy/sell imbalance or whale activity
    """

    def __init__(
        self,
        symbols: List[str],
        imbalance_threshold: float = 0.3,  # 30% imbalance
        whale_threshold: int = 5,  # Number of whale orders
    ):
        super().__init__("orderflow_imbalance", symbols)
        self.imbalance_threshold = imbalance_threshold
        self.whale_threshold = whale_threshold

    async def analyze(self, data: Dict) -> Optional[TradeSignal]:
        """
        Analyze order flow for imbalances

        data should contain:
        - symbol: str
        - buy_volume: float
        - sell_volume: float
        - large_buy_orders: int
        - large_sell_orders: int
        - price: float
        """
        symbol = data.get("symbol")
        buy_vol = data.get("buy_volume", 0)
        sell_vol = data.get("sell_volume", 0)
        large_buys = data.get("large_buy_orders", 0)
        large_sells = data.get("large_sell_orders", 0)
        price = data.get("price", 0)

        total_vol = buy_vol + sell_vol
        if total_vol == 0:
            return None

        # Calculate imbalance
        imbalance = (buy_vol - sell_vol) / total_vol
        whale_imbalance = large_buys - large_sells

        # Check thresholds
        if abs(imbalance) < self.imbalance_threshold and abs(whale_imbalance) < self.whale_threshold:
            return None

        # Determine direction
        if imbalance > self.imbalance_threshold or whale_imbalance >= self.whale_threshold:
            direction = "long"
            strength = self._calculate_strength(imbalance, whale_imbalance, True)
            stop_loss = price * 0.99  # Tight stop for flow trades
            take_profit = price * 1.02  # Quick target
            reason = f"Strong buying pressure: {imbalance*100:.1f}% imbalance, {large_buys} whale buys"

        elif imbalance < -self.imbalance_threshold or whale_imbalance <= -self.whale_threshold:
            direction = "short"
            strength = self._calculate_strength(-imbalance, -whale_imbalance, False)
            stop_loss = price * 1.01
            take_profit = price * 0.98
            reason = f"Strong selling pressure: {-imbalance*100:.1f}% imbalance, {large_sells} whale sells"

        else:
            return None

        confidence = min(abs(imbalance) + abs(whale_imbalance) * 0.1, 1.0)

        return TradeSignal(
            symbol=symbol,
            direction=direction,
            strength=strength,
            confidence=confidence,
            edge_type="orderflow_imbalance",
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason=reason,
            metadata={
                "imbalance": imbalance,
                "whale_buys": large_buys,
                "whale_sells": large_sells
            }
        )

    def _calculate_strength(self, imbalance: float, whale: int, is_long: bool) -> SignalStrength:
        score = imbalance * 2 + whale * 0.2
        if score > 1.0:
            return SignalStrength.VERY_STRONG
        elif score > 0.7:
            return SignalStrength.STRONG
        elif score > 0.4:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK


class LiquidationCascadeStrategy(EdgeStrategy):
    """
    Liquidation Cascade Edge Strategy

    The Edge:
    - Large liquidations create cascading price moves
    - After major liquidation events, price often rebounds
    - Exploit the overreaction

    Entry: After large liquidation event on one side
    """

    def __init__(
        self,
        symbols: List[str],
        liquidation_threshold: float = 10_000_000,  # $10M in liquidations
        rebound_expected_pct: float = 0.02,  # Expect 2% rebound
    ):
        super().__init__("liquidation_cascade", symbols)
        self.liquidation_threshold = liquidation_threshold
        self.rebound_expected_pct = rebound_expected_pct

    async def analyze(self, data: Dict) -> Optional[TradeSignal]:
        """
        Analyze liquidation data for cascade opportunities

        data should contain:
        - symbol: str
        - liquidations_long: float
        - liquidations_short: float
        - price: float
        - price_change_1h: float
        """
        symbol = data.get("symbol")
        liq_long = data.get("liquidations_long", 0)
        liq_short = data.get("liquidations_short", 0)
        price = data.get("price", 0)
        price_change = data.get("price_change_1h", 0)

        # Check for significant liquidation event
        if liq_long < self.liquidation_threshold and liq_short < self.liquidation_threshold:
            return None

        if liq_long > self.liquidation_threshold and price_change < -0.03:
            # Long liquidation cascade (price dumped) - expect bounce
            direction = "long"
            strength = self._liq_strength(liq_long)
            confidence = min(liq_long / (self.liquidation_threshold * 3), 0.85)
            stop_loss = price * 0.97  # 3% stop
            take_profit = price * (1 + self.rebound_expected_pct)
            reason = f"Long liquidation cascade: ${liq_long/1e6:.1f}M liquidated - expect rebound"

        elif liq_short > self.liquidation_threshold and price_change > 0.03:
            # Short liquidation cascade (price pumped) - expect pullback
            direction = "short"
            strength = self._liq_strength(liq_short)
            confidence = min(liq_short / (self.liquidation_threshold * 3), 0.85)
            stop_loss = price * 1.03
            take_profit = price * (1 - self.rebound_expected_pct)
            reason = f"Short liquidation cascade: ${liq_short/1e6:.1f}M liquidated - expect pullback"

        else:
            return None

        return TradeSignal(
            symbol=symbol,
            direction=direction,
            strength=strength,
            confidence=confidence,
            edge_type="liquidation_cascade",
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason=reason,
            metadata={
                "liq_long": liq_long,
                "liq_short": liq_short,
                "price_change_1h": price_change
            }
        )

    def _liq_strength(self, liq_amount: float) -> SignalStrength:
        ratio = liq_amount / self.liquidation_threshold
        if ratio > 5:
            return SignalStrength.VERY_STRONG
        elif ratio > 3:
            return SignalStrength.STRONG
        elif ratio > 2:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK


class EdgeStrategyManager:
    """
    Manages multiple edge strategies and combines signals
    """

    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.strategies: List[EdgeStrategy] = []
        self.signals_history: List[TradeSignal] = []
        self.max_history = 1000

        # Initialize default strategies
        self._init_strategies()

    def _init_strategies(self):
        """Initialize default edge strategies"""
        self.strategies = [
            FundingRateArbitrage(self.symbols),
            SentimentExtremeStrategy(self.symbols),
            OrderFlowImbalanceStrategy(self.symbols),
            LiquidationCascadeStrategy(self.symbols),
        ]

    def add_strategy(self, strategy: EdgeStrategy):
        """Add a custom strategy"""
        self.strategies.append(strategy)

    async def analyze_all(self, data: Dict) -> List[TradeSignal]:
        """Run all strategies and collect signals"""
        signals = []

        for strategy in self.strategies:
            if not strategy.enabled:
                continue

            try:
                signal = await strategy.analyze(data)
                if signal:
                    signals.append(signal)
                    self.signals_history.append(signal)

                    # Trim history
                    if len(self.signals_history) > self.max_history:
                        self.signals_history = self.signals_history[-self.max_history:]

            except Exception as e:
                logger.error(f"Strategy {strategy.name} error: {e}")

        return signals

    def get_combined_signal(self, signals: List[TradeSignal]) -> Optional[TradeSignal]:
        """Combine multiple signals into one trade decision"""
        if not signals:
            return None

        # Group by direction
        long_signals = [s for s in signals if s.direction == "long"]
        short_signals = [s for s in signals if s.direction == "short"]

        # Calculate weighted scores
        def calc_score(sigs: List[TradeSignal]) -> float:
            return sum(s.strength.value * s.confidence for s in sigs)

        long_score = calc_score(long_signals)
        short_score = calc_score(short_signals)

        # Need clear winner
        if long_score > short_score * 1.5 and long_signals:
            best = max(long_signals, key=lambda s: s.strength.value * s.confidence)
            combined = TradeSignal(
                symbol=best.symbol,
                direction="long",
                strength=best.strength,
                confidence=min(long_score / (long_score + short_score + 1), 0.95),
                edge_type="combined",
                entry_price=best.entry_price,
                stop_loss=best.stop_loss,
                take_profit=best.take_profit,
                reason=f"Combined signal from {len(long_signals)} edges: " + "; ".join(s.edge_type for s in long_signals)
            )
            return combined

        elif short_score > long_score * 1.5 and short_signals:
            best = max(short_signals, key=lambda s: s.strength.value * s.confidence)
            combined = TradeSignal(
                symbol=best.symbol,
                direction="short",
                strength=best.strength,
                confidence=min(short_score / (long_score + short_score + 1), 0.95),
                edge_type="combined",
                entry_price=best.entry_price,
                stop_loss=best.stop_loss,
                take_profit=best.take_profit,
                reason=f"Combined signal from {len(short_signals)} edges: " + "; ".join(s.edge_type for s in short_signals)
            )
            return combined

        return None  # No clear edge

    def get_strategy_performance(self) -> Dict[str, Dict]:
        """Calculate performance metrics per strategy"""
        performance = {}

        for strategy in self.strategies:
            strategy_signals = [s for s in self.signals_history if s.edge_type == strategy.name]

            if not strategy_signals:
                performance[strategy.name] = {"trades": 0}
                continue

            performance[strategy.name] = {
                "trades": len(strategy_signals),
                "avg_confidence": np.mean([s.confidence for s in strategy_signals]),
                "long_signals": len([s for s in strategy_signals if s.direction == "long"]),
                "short_signals": len([s for s in strategy_signals if s.direction == "short"]),
            }

        return performance


# Factory function
def create_edge_manager(symbols: List[str]) -> EdgeStrategyManager:
    """Create edge strategy manager"""
    return EdgeStrategyManager(symbols)
