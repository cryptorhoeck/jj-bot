"""
Realistic Simulator Service

Replaces the old random trade generator with a proper simulation that:
- Generates realistic prices using GBM with regime switching
- Executes real strategies via StrategyEngine
- Tracks positions with proper P&L calculation
- Uses market mechanics (slippage, commission, spreads)
- Integrates with the learning system (adaptive selector)

This creates a realistic trading environment where strategies are
actually tested and the learning system can make meaningful recommendations.
"""

import time
import sys
import os
import sqlite3
import requests
from datetime import datetime
from typing import Dict, Optional

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'glue'))

from services.base.service import BaseService
from modules.simulator.price_generator import (
    MultiSymbolPriceGenerator,
    MarketRegime,
    PriceTickdata
)
from modules.simulator.market_simulator import (
    MarketSimulator,
    PositionSide
)
from modules.strategy.strategy_engine import StrategyEngine
from modules.database.connection import init_all_databases
from modules.learning.price_history import PriceHistory
from modules.learning.strategy_performance_tracker import StrategyPerformanceTracker

# Try to import adaptive selector, but make it optional
try:
    from modules.learning.adaptive_strategy_selector import AdaptiveStrategySelector
    HAS_ADAPTIVE_SELECTOR = True
except ImportError:
    HAS_ADAPTIVE_SELECTOR = False
    print("⚠️ Adaptive strategy selector not available - using fixed strategy")


def fetch_top_100_coins() -> Dict[str, float]:
    """
    Fetch cryptocurrency prices from Kraken public API (no keys required).

    Returns:
        Dictionary mapping symbol -> current USD price
    """
    try:
        # Kraken symbol mapping (Kraken pair -> standard symbol)
        kraken_pairs = [
            "XBTUSD", "ETHUSD", "SOLUSD", "XRPUSD", "ADAUSD",
            "DOGEUSD", "AVAXUSD", "DOTUSD", "LINKUSD", "UNIUSD",
            "ATOMUSD", "LTCUSD", "XLMUSD", "ALGOUSD", "NEARUSD",
            "ICPUSD", "FILUSD", "APTUSD", "ARBUSD", "OPUSD"
        ]

        pair_to_symbol = {
            "XXBTZUSD": "BTC", "XETHZUSD": "ETH", "SOLUSD": "SOL",
            "XXRPZUSD": "XRP", "ADAUSD": "ADA", "XDGUSD": "DOGE",
            "AVAXUSD": "AVAX", "DOTUSD": "DOT", "LINKUSD": "LINK",
            "UNIUSD": "UNI", "ATOMUSD": "ATOM", "XLTCZUSD": "LTC",
            "XXLMZUSD": "XLM", "ALGOUSD": "ALGO", "NEARUSD": "NEAR",
            "ICPUSD": "ICP", "FILUSD": "FIL", "APTUSD": "APT",
            "ARBUSD": "ARB", "OPUSD": "OP"
        }

        print("🌐 Fetching cryptocurrency prices from Kraken (no API key required)...")

        url = "https://api.kraken.com/0/public/Ticker"
        params = {"pair": ",".join(kraken_pairs)}

        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            data = response.json()

            if data.get("error") and len(data["error"]) > 0:
                print(f"⚠️ Kraken API error: {data['error']}")
                return {}

            prices = {}
            for kraken_pair, ticker in data.get("result", {}).items():
                symbol = pair_to_symbol.get(kraken_pair)
                if symbol:
                    # Kraken ticker 'c' = last trade closed [price, lot volume]
                    price = float(ticker["c"][0])
                    prices[symbol] = price

            print(f"✅ Fetched {len(prices)} cryptocurrencies from Kraken")
            print(f"   Symbols: {list(prices.keys())}")
            if prices:
                print(f"   Price range: ${min(prices.values()):.6f} - ${max(prices.values()):,.2f}")

            return prices
        else:
            print(f"⚠️ Kraken API returned status {response.status_code}")
            return {}

    except Exception as e:
        print(f"⚠️ Failed to fetch from Kraken: {e}")
        return {}


class RealisticSimulatorService(BaseService):
    """
    Realistic trading simulator with proper strategy execution.

    Flow:
    1. Price Generator creates realistic market prices
    2. Adaptive Selector recommends best strategy
    3. Strategy Engine analyzes prices and generates signals
    4. Market Simulator executes trades with realistic mechanics
    5. Results feed back to learning system
    6. Loop continues

    This replaces the old random trade generator.
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        tick_interval_seconds: int = 2,  # FAST: 2 seconds between ticks
        trade_frequency_ticks: int = 1,  # FAST: Check signals every tick
    ):
        """
        Initialize realistic simulator.

        Args:
            initial_capital: Starting capital for trading
            tick_interval_seconds: Time between price updates
            trade_frequency_ticks: How often to evaluate trading signals
        """
        super().__init__(name="realistic_simulator", auto_start=False)

        self.initial_capital = initial_capital
        self.tick_interval = tick_interval_seconds
        self.trade_frequency = trade_frequency_ticks

        # Symbol configuration (will be populated from API)
        self.symbols_config = {}

        # Components (initialized in start())
        self.price_generator: Optional[MultiSymbolPriceGenerator] = None
        self.market_simulator: Optional[MarketSimulator] = None
        self.strategy_engine: Optional[StrategyEngine] = None
        self.adaptive_selector: Optional[AdaptiveStrategySelector] = None
        self.price_history: Optional[PriceHistory] = None
        self.performance_tracker: Optional[StrategyPerformanceTracker] = None

        # State
        self.current_strategy = "rsi_strategy"  # Default
        self.tick_count = 0
        self.trades_generated = 0
        self.last_selector_check = 0

    def _initialize_components(self):
        """Initialize all simulator components"""
        try:
            # Initialize databases first
            print("📦 Initializing databases...")
            init_all_databases()

            # Fetch top 100 cryptocurrencies by market cap
            top_100_prices = fetch_top_100_coins()
            if top_100_prices:
                # Use the fetched prices
                self.symbols_config = top_100_prices
                print(f"✅ Tracking {len(self.symbols_config)} cryptocurrencies")
            else:
                # Fallback to top 10 if API fails
                print("⚠️ API failed, using fallback top 10 symbols")
                self.symbols_config = {
                    'BTC': 45000, 'ETH': 2500, 'SOL': 100, 'BNB': 350, 'ADA': 0.50,
                    'DOT': 7, 'LINK': 15, 'POL': 0.45, 'UNI': 6, 'AVAX': 35
                }

            # Price generator
            self.price_generator = MultiSymbolPriceGenerator(
                symbols_config=self.symbols_config,
                correlation=0.3,  # 30% correlation between crypto prices
                tick_interval_seconds=self.tick_interval
            )
            print("✅ Price generator initialized")

            # Market simulator
            self.market_simulator = MarketSimulator(
                initial_capital=self.initial_capital,
                commission_rate=0.001,      # 0.1%
                slippage_rate=0.0005,       # 0.05%
                position_size_pct=0.10,     # 10% per trade
                use_stop_loss=True,
                stop_loss_pct=0.02,         # 2% stop-loss
                use_take_profit=True,
                take_profit_pct=0.05        # 5% take-profit
            )
            print("✅ Market simulator initialized")

            # Strategy engine
            self.strategy_engine = StrategyEngine()
            print("✅ Strategy engine initialized")

            # Price history for learning system
            self.price_history = PriceHistory()
            print("✅ Price history tracker initialized")

            # Performance tracker for learning system
            self.performance_tracker = StrategyPerformanceTracker()
            print("✅ Performance tracker initialized")

            # Adaptive selector (optional)
            if HAS_ADAPTIVE_SELECTOR:
                self.adaptive_selector = AdaptiveStrategySelector(
                    reevaluation_interval=10,  # Check every 10 trades
                    min_confidence=0.6
                )

                # Load initial strategy recommendation
                state = self.adaptive_selector.get_state()
                if state:
                    self.current_strategy = state["current_strategy"]
                    print(f"✅ Loaded strategy: {self.current_strategy}")
                else:
                    print(f"✅ Using default strategy: {self.current_strategy}")
            else:
                self.adaptive_selector = None
                print(f"✅ Using fixed strategy: {self.current_strategy}")

        except Exception as e:
            print(f"Failed to initialize components: {e}")
            raise

    def _get_strategy_signal(
        self,
        symbol: str,
        price_data: PriceTickdata,
        price_history: list
    ) -> Optional[str]:
        """
        Get trading signal from current strategy.

        Args:
            symbol: Trading symbol
            price_data: Current price tick
            price_history: Recent price history

        Returns:
            "BUY", "SELL", or None
        """
        try:
            # Prepare data for strategy engine
            if len(price_history) < 20:
                return None  # Need enough history

            # Calculate indicators
            self.strategy_engine.calculate_indicators(price_history)

            indicators = self.strategy_engine.get_indicators()
            if not indicators:
                return None

            # Get signal from strategy dispatcher
            return self._dispatch_strategy_signal(indicators, price_history)

        except Exception as e:
            print(f"Error getting strategy signal: {e}")
            return None

    def _dispatch_strategy_signal(
        self,
        indicators: Dict,
        price_history: list
    ) -> Optional[str]:
        """
        Dispatch signal generation to appropriate strategy.

        Implements multiple trading strategies that can be selected by the
        adaptive selector based on performance.

        Args:
            indicators: Calculated technical indicators
            price_history: Recent price history

        Returns:
            "BUY", "SELL", or None
        """
        strategy = self.current_strategy

        # RSI-based strategies
        if strategy == "rsi_strategy":
            return self._rsi_strategy(indicators)
        elif strategy == "rsi_aggressive":
            return self._rsi_aggressive_strategy(indicators)
        elif strategy == "rsi_conservative":
            return self._rsi_conservative_strategy(indicators)

        # Moving average strategies
        elif strategy == "sma_crossover":
            return self._sma_crossover_strategy(indicators)
        elif strategy == "ema_crossover":
            return self._ema_crossover_strategy(indicators)
        elif strategy == "triple_ma":
            return self._triple_ma_strategy(indicators)

        # MACD strategies
        elif strategy == "macd":
            return self._macd_strategy(indicators)
        elif strategy == "macd_histogram":
            return self._macd_histogram_strategy(indicators)

        # Bollinger Band strategies
        elif strategy == "bollinger_bounce":
            return self._bollinger_bounce_strategy(indicators)
        elif strategy == "bollinger_breakout":
            return self._bollinger_breakout_strategy(indicators)

        # Momentum strategies
        elif strategy == "momentum":
            return self._momentum_strategy(indicators, price_history)
        elif strategy == "mean_reversion":
            return self._mean_reversion_strategy(indicators, price_history)

        # Combined strategies
        elif strategy == "rsi_macd_combo":
            return self._rsi_macd_combo_strategy(indicators)
        elif strategy == "triple_confirmation":
            return self._triple_confirmation_strategy(indicators)

        # Default to RSI
        return self._rsi_strategy(indicators)

    def _rsi_strategy(self, indicators: Dict) -> Optional[str]:
        """Standard RSI strategy: Buy < 30, Sell > 70"""
        rsi = indicators.get("rsi")
        if rsi is None:
            return None
        if rsi < 30:
            return "BUY"
        elif rsi > 70:
            return "SELL"
        return None

    def _rsi_aggressive_strategy(self, indicators: Dict) -> Optional[str]:
        """Aggressive RSI: Buy < 40, Sell > 60"""
        rsi = indicators.get("rsi")
        if rsi is None:
            return None
        if rsi < 40:
            return "BUY"
        elif rsi > 60:
            return "SELL"
        return None

    def _rsi_conservative_strategy(self, indicators: Dict) -> Optional[str]:
        """Conservative RSI: Buy < 20, Sell > 80"""
        rsi = indicators.get("rsi")
        if rsi is None:
            return None
        if rsi < 20:
            return "BUY"
        elif rsi > 80:
            return "SELL"
        return None

    def _sma_crossover_strategy(self, indicators: Dict) -> Optional[str]:
        """SMA crossover: Short SMA crosses Long SMA"""
        sma_short = indicators.get("sma_short")
        sma_long = indicators.get("sma_long")
        if sma_short is None or sma_long is None:
            return None
        if sma_short > sma_long:
            return "BUY"
        elif sma_short < sma_long:
            return "SELL"
        return None

    def _ema_crossover_strategy(self, indicators: Dict) -> Optional[str]:
        """EMA crossover (faster response than SMA)"""
        ema_short = indicators.get("ema_short", indicators.get("sma_short"))
        ema_long = indicators.get("ema_long", indicators.get("sma_long"))
        if ema_short is None or ema_long is None:
            return None
        if ema_short > ema_long * 1.005:  # 0.5% threshold
            return "BUY"
        elif ema_short < ema_long * 0.995:
            return "SELL"
        return None

    def _triple_ma_strategy(self, indicators: Dict) -> Optional[str]:
        """Triple MA: Fast, Medium, Slow alignment"""
        sma_short = indicators.get("sma_short")
        sma_long = indicators.get("sma_long")
        rsi = indicators.get("rsi", 50)
        if sma_short is None or sma_long is None:
            return None
        # Buy when short > long and RSI not overbought
        if sma_short > sma_long and rsi < 65:
            return "BUY"
        elif sma_short < sma_long and rsi > 35:
            return "SELL"
        return None

    def _macd_strategy(self, indicators: Dict) -> Optional[str]:
        """MACD crossover strategy"""
        macd = indicators.get("macd")
        macd_signal = indicators.get("macd_signal")
        if macd is None or macd_signal is None:
            return None
        if macd > macd_signal:
            return "BUY"
        elif macd < macd_signal:
            return "SELL"
        return None

    def _macd_histogram_strategy(self, indicators: Dict) -> Optional[str]:
        """MACD histogram momentum"""
        macd = indicators.get("macd")
        macd_signal = indicators.get("macd_signal")
        if macd is None or macd_signal is None:
            return None
        histogram = macd - macd_signal
        # Strong momentum signal
        if histogram > 0.5:
            return "BUY"
        elif histogram < -0.5:
            return "SELL"
        return None

    def _bollinger_bounce_strategy(self, indicators: Dict) -> Optional[str]:
        """Bollinger Band bounce: Buy at lower, Sell at upper"""
        bb_upper = indicators.get("bb_upper")
        bb_lower = indicators.get("bb_lower")
        bb_middle = indicators.get("bb_middle")
        if bb_upper is None or bb_lower is None or bb_middle is None:
            return None
        # Approximate current price from middle band
        current = bb_middle
        if current <= bb_lower * 1.01:  # Near lower band
            return "BUY"
        elif current >= bb_upper * 0.99:  # Near upper band
            return "SELL"
        return None

    def _bollinger_breakout_strategy(self, indicators: Dict) -> Optional[str]:
        """Bollinger breakout: Trade the trend"""
        bb_upper = indicators.get("bb_upper")
        bb_lower = indicators.get("bb_lower")
        bb_middle = indicators.get("bb_middle")
        rsi = indicators.get("rsi", 50)
        if bb_upper is None or bb_lower is None:
            return None
        # Breakout with momentum confirmation
        if bb_middle and bb_middle > bb_upper * 0.98 and rsi > 50:
            return "BUY"  # Bullish breakout
        elif bb_middle and bb_middle < bb_lower * 1.02 and rsi < 50:
            return "SELL"  # Bearish breakout
        return None

    def _momentum_strategy(
        self, indicators: Dict, price_history: list
    ) -> Optional[str]:
        """Price momentum strategy"""
        if len(price_history) < 10:
            return None
        recent_prices = price_history[-10:]
        oldest = recent_prices[0]
        newest = recent_prices[-1]
        change_pct = (newest - oldest) / oldest * 100
        # Strong momentum signals
        if change_pct > 2:
            return "BUY"
        elif change_pct < -2:
            return "SELL"
        return None

    def _mean_reversion_strategy(
        self, indicators: Dict, price_history: list
    ) -> Optional[str]:
        """Mean reversion: Buy oversold, Sell overbought"""
        if len(price_history) < 20:
            return None
        mean_price = sum(price_history[-20:]) / 20
        current_price = price_history[-1]
        deviation = (current_price - mean_price) / mean_price * 100
        # Reversion signals
        if deviation < -3:  # 3% below mean
            return "BUY"
        elif deviation > 3:  # 3% above mean
            return "SELL"
        return None

    def _rsi_macd_combo_strategy(self, indicators: Dict) -> Optional[str]:
        """Combined RSI + MACD confirmation"""
        rsi = indicators.get("rsi")
        macd = indicators.get("macd")
        macd_signal = indicators.get("macd_signal")
        if rsi is None or macd is None or macd_signal is None:
            return None
        # Both indicators must agree
        if rsi < 40 and macd > macd_signal:
            return "BUY"
        elif rsi > 60 and macd < macd_signal:
            return "SELL"
        return None

    def _triple_confirmation_strategy(self, indicators: Dict) -> Optional[str]:
        """Requires RSI, MACD, and SMA alignment"""
        rsi = indicators.get("rsi")
        macd = indicators.get("macd")
        macd_signal = indicators.get("macd_signal")
        sma_short = indicators.get("sma_short")
        sma_long = indicators.get("sma_long")

        if any(v is None for v in [rsi, macd, macd_signal, sma_short, sma_long]):
            return None

        # All three must confirm
        rsi_bullish = rsi < 50
        macd_bullish = macd > macd_signal
        sma_bullish = sma_short > sma_long

        rsi_bearish = rsi > 50
        macd_bearish = macd < macd_signal
        sma_bearish = sma_short < sma_long

        if rsi_bullish and macd_bullish and sma_bullish:
            return "BUY"
        elif rsi_bearish and macd_bearish and sma_bearish:
            return "SELL"
        return None

    def record_trade(self, trade):
        """Record trade and notify adaptive selector."""
        self._save_trade_to_db(trade)

        # Notify adaptive selector for re-evaluation
        if self.adaptive_selector:
            self.adaptive_selector.notify_trade()

    def _save_trade_to_db(self, trade):
        """Save completed trade to database"""
        try:
            db_path = os.path.join(
                os.path.dirname(__file__), '..', '..', 'data', 'trades.db'
            )
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO trades (
                    timestamp, symbol, signal, last_price, vwap, pnl,
                    strategy, entry_price, exit_price
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.timestamp.isoformat(),
                trade.symbol,
                trade.signal,
                trade.exit_price,  # last_price = exit price
                (trade.entry_price + trade.exit_price) / 2,  # vwap approximation
                trade.pnl,
                trade.strategy,
                trade.entry_price,
                trade.exit_price
            ))

            conn.commit()
            conn.close()

            self.trades_generated += 1

            # Record performance metrics for learning system
            self.performance_tracker.record_trade(
                strategy_name=trade.strategy,
                pnl=trade.pnl,
                entry_price=trade.entry_price,
                exit_price=trade.exit_price,
                timestamp=trade.timestamp
            )

            print(
                f"💾 {trade.signal} {trade.symbol} | "
                f"Entry: ${trade.entry_price:.2f} | "
                f"Exit: ${trade.exit_price:.2f} | "
                f"P&L: ${trade.pnl:+.2f} ({trade.pnl_percentage:+.2f}%) | "
                f"Strategy: {trade.strategy}"
            )

        except Exception as e:
            print(f"Error saving trade to database: {e}")

    def _check_adaptive_selector(self):
        """Check if adaptive selector wants to switch strategies"""
        # Skip if adaptive selector not available
        if not HAS_ADAPTIVE_SELECTOR or self.adaptive_selector is None:
            return

        try:
            # Check every 10 trades
            if self.trades_generated - self.last_selector_check >= 10:
                recommendation = self.adaptive_selector.select_best_strategy()

                if recommendation["switched"]:
                    old_strategy = self.current_strategy
                    self.current_strategy = recommendation["strategy"]

                    print(
                        f"🔄 Strategy switch: {old_strategy} → {self.current_strategy} "
                        f"(confidence: {recommendation['confidence']:.2f})"
                    )

                self.last_selector_check = self.trades_generated

        except Exception as e:
            print(f"Error checking adaptive selector: {e}")

    def _run(self):
        """Main simulator loop"""
        print("🚀 Realistic Simulator starting...")

        # Initialize components
        try:
            self._initialize_components()
        except Exception as e:
            print(f"Failed to initialize: {e}")
            self.status = "error"
            return

        # Price history for each symbol (for indicators)
        price_histories: Dict[str, list] = {
            symbol: [] for symbol in self.symbols_config.keys()
        }

        print(f"💰 Initial capital: ${self.initial_capital:,.2f}")
        print(f"📊 Trading {len(self.symbols_config)} symbols")
        print(f"🎯 Starting strategy: {self.current_strategy}")
        print("=" * 60)

        try:
            while self.status == "running":
                # Generate next price tick for all symbols
                price_ticks = self.price_generator.generate_next_ticks()

                # Update price histories
                for symbol, tick in price_ticks.items():
                    price_histories[symbol].append(tick.price)

                    # Keep only recent history (last 100 ticks) - FAST mode
                    if len(price_histories[symbol]) > 100:
                        price_histories[symbol].pop(0)

                    # Store price to database for learning system
                    self.price_history.add_price_tick(
                        symbol=symbol,
                        price=tick.price,
                        volume=tick.volume,
                        timestamp=tick.timestamp
                    )

                # Update open positions and check stop-loss/take-profit
                prices = {symbol: tick.price for symbol, tick in price_ticks.items()}
                bids = {symbol: tick.bid for symbol, tick in price_ticks.items()}
                asks = {symbol: tick.ask for symbol, tick in price_ticks.items()}

                closed_trades = self.market_simulator.update_positions(
                    prices=prices,
                    bids=bids,
                    asks=asks,
                    timestamp=datetime.now()
                )

                # Save any trades closed by stop-loss/take-profit
                for trade in closed_trades:
                    self._save_trade_to_db(trade)

                # Check for new trading signals (every N ticks)
                if self.tick_count % self.trade_frequency == 0:
                    for symbol, tick in price_ticks.items():
                        # Skip if position already open
                        if not self.market_simulator.can_open_position(symbol, tick.price):
                            continue

                        # Get signal from strategy
                        signal = self._get_strategy_signal(
                            symbol=symbol,
                            price_data=tick,
                            price_history=price_histories[symbol]
                        )

                        if signal == "BUY":
                            # Open long position
                            position = self.market_simulator.open_position(
                                symbol=symbol,
                                side=PositionSide.LONG,
                                price=tick.price,
                                strategy=self.current_strategy,
                                bid=tick.bid,
                                ask=tick.ask,
                                timestamp=tick.timestamp
                            )

                            if position:
                                print(
                                    f"🟢 LONG {symbol} @ ${position.entry_price:.2f} | "
                                    f"Qty: {position.quantity:.4f} | "
                                    f"Stop: ${position.stop_loss:.2f} | "
                                    f"Target: ${position.take_profit:.2f}"
                                )

                        elif signal == "SELL":
                            # Check if we have a long position to close
                            trade = self.market_simulator.close_position(
                                symbol=symbol,
                                price=tick.price,
                                bid=tick.bid,
                                ask=tick.ask,
                                timestamp=tick.timestamp,
                                reason="signal"
                            )

                            if trade:
                                self._save_trade_to_db(trade)

                # Check adaptive selector for strategy changes
                self._check_adaptive_selector()

                # Update statistics
                stats = self.market_simulator.get_statistics()
                self.stats.update({
                    "tick_count": self.tick_count,
                    "trades_generated": self.trades_generated,
                    "current_strategy": self.current_strategy,
                    "capital": stats["current_capital"],
                    "pnl": stats["total_pnl"],
                    "return_pct": stats["total_return_pct"],
                    "win_rate": stats["win_rate"],
                    "open_positions": stats["open_positions"],
                    "market_regime": self.price_generator.market_regime.value
                })

                # Log status every 5 ticks (FAST mode)
                if self.tick_count % 5 == 0:
                    print(
                        f"📊 Tick {self.tick_count} | "
                        f"Cash: ${stats['available_capital']:,.2f} | "
                        f"Positions: ${stats['positions_value']:,.2f} | "
                        f"Total: ${stats['current_capital']:,.2f} | "
                        f"P&L: ${stats['total_pnl']:+,.2f} ({stats['total_return_pct']:+.2f}%) | "
                        f"Trades: {self.trades_generated} | "
                        f"Regime: {self.price_generator.market_regime.value}"
                    )

                self.tick_count += 1

                # Wait for next tick
                time.sleep(self.tick_interval)

        except Exception as e:
            print(f"Simulator error: {e}")
            self.status = "error"
            self.stats["error"] = str(e)

    def _cleanup(self):
        """Cleanup simulator resources"""
        print("🛑 Realistic Simulator stopping...")

        if self.market_simulator:
            stats = self.market_simulator.get_statistics()
            print("=" * 60)
            print("📈 Final Statistics:")
            print(f"   Initial Capital: ${stats['initial_capital']:,.2f}")
            print(f"   Final Capital:   ${stats['current_capital']:,.2f}")
            print(f"   Total P&L:       ${stats['total_pnl']:+,.2f}")
            print(f"   Return:          {stats['total_return_pct']:+.2f}%")
            print(f"   Total Trades:    {stats['total_trades']}")
            print(f"   Win Rate:        {stats['win_rate']:.2f}%")
            print(f"   Commission Paid: ${stats['total_commission_paid']:.2f}")
            print(f"   Slippage Paid:   ${stats['total_slippage_paid']:.2f}")
            print("=" * 60)
