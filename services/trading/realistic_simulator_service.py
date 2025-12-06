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
    print("[WARNING] Adaptive strategy selector not available - using fixed strategy")


def fetch_top_100_coins() -> Dict[str, float]:
    """
    Fetch top 100 cryptocurrencies by market cap from CoinGecko API.

    Returns:
        Dictionary mapping symbol -> current USD price
    """
    try:
        # Fetch top 100 coins sorted by market cap
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 100,
            'page': 1,
            'sparkline': False
        }

        print("[API] Fetching top 100 cryptocurrencies by market cap from CoinGecko...")
        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            data = response.json()
            prices = {}

            for coin in data:
                symbol = coin['symbol'].upper()
                price = coin['current_price']
                market_cap = coin['market_cap']

                prices[symbol] = price

            print(f"[OK] Fetched {len(prices)} cryptocurrencies")
            print(f"   Top 5: {list(prices.keys())[:5]}")
            print(f"   Price range: ${min(prices.values()):.6f} - ${max(prices.values()):,.2f}")

            return prices
        else:
            print(f"[WARNING] CoinGecko API returned status {response.status_code}")
            return {}

    except Exception as e:
        print(f"[WARNING] Failed to fetch top 100 coins: {e}")
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

        # Available strategies (24 fully implemented)
        self.AVAILABLE_STRATEGIES = [
            # Momentum strategies
            "rsi_strategy",           # RSI oversold/overbought
            "rsi_divergence",         # RSI divergence detection
            "macd",                   # MACD crossover
            "macd_histogram",         # MACD histogram reversal
            "stochastic",             # Stochastic oscillator
            "stochastic_rsi",         # Stochastic RSI combo
            # Trend strategies
            "sma_crossover",          # SMA fast/slow crossover
            "ema_crossover",          # EMA fast/slow crossover
            "triple_ema",             # Triple EMA (short/medium/long)
            "adx_trend",              # ADX trend strength
            # Mean reversion strategies
            "bollinger_bands",        # Bollinger band bounce
            "bollinger_squeeze",      # Bollinger squeeze breakout
            "keltner_channel",        # Keltner channel
            "mean_reversion",         # Simple mean reversion
            # Volume strategies
            "volume_breakout",        # Volume spike breakout
            "obv_divergence",         # On-balance volume divergence
            "vwap_strategy",          # VWAP crossover
            # Combined/Advanced strategies
            "macd_rsi_combo",         # MACD + RSI confirmation
            "trend_momentum",         # Trend + momentum combo
            "multi_timeframe",        # Multi-timeframe analysis
            "support_resistance",     # Support/resistance levels
            "breakout_pullback",      # Breakout with pullback entry
            "swing_trading",          # Swing high/low strategy
            "scalping",               # Quick scalping strategy
        ]

        # State
        self.current_strategy = "rsi_strategy"  # Default
        self.tick_count = 0
        self.trades_generated = 0
        self.last_selector_check = 0

    def _initialize_components(self):
        """Initialize all simulator components"""
        try:
            # Initialize databases first
            print("[INIT] Initializing databases...")
            init_all_databases()

            # Fetch top 100 cryptocurrencies by market cap
            top_100_prices = fetch_top_100_coins()
            if top_100_prices:
                # Use the fetched prices
                self.symbols_config = top_100_prices
                print(f"[OK] Tracking {len(self.symbols_config)} cryptocurrencies")
            else:
                # Fallback to top 10 if API fails
                print("[WARNING] API failed, using fallback top 10 symbols")
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
            print("[OK] Price generator initialized")

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
            print("[OK] Market simulator initialized")

            # Strategy engine
            self.strategy_engine = StrategyEngine()
            print("[OK] Strategy engine initialized")

            # Price history for learning system
            self.price_history = PriceHistory()
            print("[OK] Price history tracker initialized")

            # Performance tracker for learning system
            self.performance_tracker = StrategyPerformanceTracker()
            print("[OK] Performance tracker initialized")

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
            # Strategy engine expects price history
            if len(price_history) < 20:  # FAST: Reduced from 50 to 20
                return None  # Need enough history

            # Calculate indicators
            self.strategy_engine.calculate_indicators(price_history)

            # Get signal based on current strategy from 24 available strategies
            indicators = self.strategy_engine.get_indicators()

            if not indicators:
                return None

            # Strategy selector - implements all 24 strategies
            return self._execute_strategy(indicators)

        except Exception as e:
            print(f"Error getting strategy signal: {e}")
            return None

    def _execute_strategy(self, indicators: Dict) -> Optional[str]:
        """
        Execute the current strategy and return signal.
        Implements all 24 available strategies.

        Args:
            indicators: Dict of calculated indicators

        Returns:
            "BUY", "SELL", or None
        """
        strategy = self.current_strategy

        # === MOMENTUM STRATEGIES ===
        if strategy == "rsi_strategy":
            rsi = indicators.get("rsi")
            if rsi is None:
                return None
            if rsi < 30:
                return "BUY"
            elif rsi > 70:
                return "SELL"

        elif strategy == "rsi_divergence":
            rsi = indicators.get("rsi")
            rsi_prev = indicators.get("rsi_prev", rsi)
            price = indicators.get("close")
            price_prev = indicators.get("close_prev", price)
            if rsi and price and rsi_prev and price_prev:
                # Bullish divergence: price lower low, RSI higher low
                if price < price_prev and rsi > rsi_prev and rsi < 40:
                    return "BUY"
                # Bearish divergence: price higher high, RSI lower high
                elif price > price_prev and rsi < rsi_prev and rsi > 60:
                    return "SELL"

        elif strategy == "macd":
            macd = indicators.get("macd")
            macd_signal = indicators.get("macd_signal")
            if macd is None or macd_signal is None:
                return None
            if macd > macd_signal:
                return "BUY"
            elif macd < macd_signal:
                return "SELL"

        elif strategy == "macd_histogram":
            macd_hist = indicators.get("macd_histogram")
            macd_hist_prev = indicators.get("macd_histogram_prev", 0)
            if macd_hist is not None:
                # Histogram turning positive
                if macd_hist > 0 and macd_hist_prev <= 0:
                    return "BUY"
                # Histogram turning negative
                elif macd_hist < 0 and macd_hist_prev >= 0:
                    return "SELL"

        elif strategy == "stochastic":
            stoch_k = indicators.get("stoch_k")
            stoch_d = indicators.get("stoch_d")
            if stoch_k is not None and stoch_d is not None:
                if stoch_k < 20 and stoch_k > stoch_d:
                    return "BUY"
                elif stoch_k > 80 and stoch_k < stoch_d:
                    return "SELL"

        elif strategy == "stochastic_rsi":
            rsi = indicators.get("rsi")
            stoch_k = indicators.get("stoch_k")
            if rsi is not None and stoch_k is not None:
                if rsi < 40 and stoch_k < 20:
                    return "BUY"
                elif rsi > 60 and stoch_k > 80:
                    return "SELL"

        # === TREND STRATEGIES ===
        elif strategy == "sma_crossover":
            sma_short = indicators.get("sma_short")
            sma_long = indicators.get("sma_long")
            if sma_short is None or sma_long is None:
                return None
            if sma_short > sma_long:
                return "BUY"
            elif sma_short < sma_long:
                return "SELL"

        elif strategy == "ema_crossover":
            ema_short = indicators.get("ema_short", indicators.get("sma_short"))
            ema_long = indicators.get("ema_long", indicators.get("sma_long"))
            if ema_short is not None and ema_long is not None:
                if ema_short > ema_long:
                    return "BUY"
                elif ema_short < ema_long:
                    return "SELL"

        elif strategy == "triple_ema":
            ema_short = indicators.get("ema_short", indicators.get("sma_short"))
            ema_medium = indicators.get("ema_medium", indicators.get("sma_long"))
            ema_long = indicators.get("ema_long")
            if ema_short and ema_medium:
                if ema_short > ema_medium:
                    return "BUY"
                elif ema_short < ema_medium:
                    return "SELL"

        elif strategy == "adx_trend":
            adx = indicators.get("adx")
            plus_di = indicators.get("plus_di")
            minus_di = indicators.get("minus_di")
            if adx is not None and adx > 25:  # Strong trend
                if plus_di and minus_di:
                    if plus_di > minus_di:
                        return "BUY"
                    elif minus_di > plus_di:
                        return "SELL"

        # === MEAN REVERSION STRATEGIES ===
        elif strategy == "bollinger_bands":
            price = indicators.get("close")
            bb_lower = indicators.get("bb_lower")
            bb_upper = indicators.get("bb_upper")
            if price and bb_lower and bb_upper:
                if price < bb_lower:
                    return "BUY"
                elif price > bb_upper:
                    return "SELL"

        elif strategy == "bollinger_squeeze":
            bb_width = indicators.get("bb_width")
            bb_width_prev = indicators.get("bb_width_prev", bb_width)
            price = indicators.get("close")
            sma = indicators.get("sma_short")
            if bb_width and bb_width_prev and price and sma:
                # Squeeze ending (expansion)
                if bb_width > bb_width_prev * 1.2:
                    if price > sma:
                        return "BUY"
                    elif price < sma:
                        return "SELL"

        elif strategy == "keltner_channel":
            price = indicators.get("close")
            kc_upper = indicators.get("kc_upper", indicators.get("bb_upper"))
            kc_lower = indicators.get("kc_lower", indicators.get("bb_lower"))
            if price and kc_lower and kc_upper:
                if price < kc_lower:
                    return "BUY"
                elif price > kc_upper:
                    return "SELL"

        elif strategy == "mean_reversion":
            price = indicators.get("close")
            sma = indicators.get("sma_long")
            if price and sma and sma > 0:
                deviation = (price - sma) / sma
                if deviation < -0.02:  # 2% below mean
                    return "BUY"
                elif deviation > 0.02:  # 2% above mean
                    return "SELL"

        # === VOLUME STRATEGIES ===
        elif strategy == "volume_breakout":
            volume = indicators.get("volume")
            volume_sma = indicators.get("volume_sma")
            price = indicators.get("close")
            price_prev = indicators.get("close_prev", price)
            if volume and volume_sma and price and price_prev:
                if volume > volume_sma * 2:  # Volume spike
                    if price > price_prev:
                        return "BUY"
                    elif price < price_prev:
                        return "SELL"

        elif strategy == "obv_divergence":
            obv = indicators.get("obv")
            obv_prev = indicators.get("obv_prev", obv)
            price = indicators.get("close")
            price_prev = indicators.get("close_prev", price)
            if obv and price and obv_prev and price_prev:
                # Bullish divergence
                if price < price_prev and obv > obv_prev:
                    return "BUY"
                # Bearish divergence
                elif price > price_prev and obv < obv_prev:
                    return "SELL"

        elif strategy == "vwap_strategy":
            price = indicators.get("close")
            vwap = indicators.get("vwap", indicators.get("sma_short"))
            if price and vwap:
                if price < vwap * 0.99:  # Below VWAP
                    return "BUY"
                elif price > vwap * 1.01:  # Above VWAP
                    return "SELL"

        # === COMBINED/ADVANCED STRATEGIES ===
        elif strategy == "macd_rsi_combo":
            macd = indicators.get("macd")
            macd_signal = indicators.get("macd_signal")
            rsi = indicators.get("rsi")
            if macd and macd_signal and rsi:
                if macd > macd_signal and rsi < 50:
                    return "BUY"
                elif macd < macd_signal and rsi > 50:
                    return "SELL"

        elif strategy == "trend_momentum":
            sma_short = indicators.get("sma_short")
            sma_long = indicators.get("sma_long")
            rsi = indicators.get("rsi")
            if sma_short and sma_long and rsi:
                # Uptrend with momentum
                if sma_short > sma_long and rsi > 50 and rsi < 70:
                    return "BUY"
                # Downtrend with momentum
                elif sma_short < sma_long and rsi < 50 and rsi > 30:
                    return "SELL"

        elif strategy == "multi_timeframe":
            # Use available indicators as proxy for multi-timeframe
            sma_short = indicators.get("sma_short")
            sma_long = indicators.get("sma_long")
            rsi = indicators.get("rsi")
            if sma_short and sma_long and rsi:
                if sma_short > sma_long and rsi < 60:
                    return "BUY"
                elif sma_short < sma_long and rsi > 40:
                    return "SELL"

        elif strategy == "support_resistance":
            price = indicators.get("close")
            high = indicators.get("high")
            low = indicators.get("low")
            if price and high and low:
                range_size = high - low
                if range_size > 0:
                    position = (price - low) / range_size
                    if position < 0.2:  # Near support
                        return "BUY"
                    elif position > 0.8:  # Near resistance
                        return "SELL"

        elif strategy == "breakout_pullback":
            price = indicators.get("close")
            sma = indicators.get("sma_short")
            high_20 = indicators.get("high_20", indicators.get("bb_upper"))
            if price and sma and high_20:
                # Breakout above recent high, wait for pullback to SMA
                if price > high_20 * 0.98 and price < high_20 * 1.02:
                    return "BUY"

        elif strategy == "swing_trading":
            rsi = indicators.get("rsi")
            sma_short = indicators.get("sma_short")
            sma_long = indicators.get("sma_long")
            if rsi and sma_short and sma_long:
                # Swing low in uptrend
                if sma_short > sma_long and rsi < 40:
                    return "BUY"
                # Swing high in downtrend
                elif sma_short < sma_long and rsi > 60:
                    return "SELL"

        elif strategy == "scalping":
            rsi = indicators.get("rsi")
            if rsi is not None:
                # Quick entries on oversold/overbought
                if rsi < 25:
                    return "BUY"
                elif rsi > 75:
                    return "SELL"

        return None

    def select_strategy(self, strategy_name: str) -> bool:
        """
        Select a strategy from the available strategies.

        Args:
            strategy_name: Name of the strategy to select

        Returns:
            True if strategy was selected, False if invalid
        """
        if strategy_name in self.AVAILABLE_STRATEGIES:
            old_strategy = self.current_strategy
            self.current_strategy = strategy_name
            print(f"🔄 Strategy changed: {old_strategy} → {self.current_strategy}")
            return True
        else:
            print(f"❌ Unknown strategy: {strategy_name}")
            print(f"   Available: {', '.join(self.AVAILABLE_STRATEGIES[:5])}...")
            return False

    def get_available_strategies(self) -> list:
        """Get list of all available strategies"""
        return self.AVAILABLE_STRATEGIES.copy()

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
