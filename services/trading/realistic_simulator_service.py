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


def fetch_real_prices() -> Dict[str, float]:
    """
    Fetch current real market prices from CoinGecko API.

    Returns:
        Dictionary mapping symbol -> current USD price
    """
    # Symbol mapping from CoinGecko IDs to our symbols
    coin_mapping = {
        'bitcoin': 'BTC',
        'ethereum': 'ETH',
        'solana': 'SOL',
        'binancecoin': 'BNB',
        'cardano': 'ADA',
        'polkadot': 'DOT',
        'chainlink': 'LINK',
        'polygon': 'MATIC',
        'uniswap': 'UNI',
        'avalanche-2': 'AVAX'
    }

    try:
        # Fetch prices from CoinGecko
        coin_ids = ','.join(coin_mapping.keys())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_ids}&vs_currencies=usd"

        print("🌐 Fetching real market prices from CoinGecko...")
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            prices = {}

            for coin_id, symbol in coin_mapping.items():
                if coin_id in data and 'usd' in data[coin_id]:
                    prices[symbol] = data[coin_id]['usd']
                    print(f"   {symbol}: ${prices[symbol]:,.2f}")

            print(f"✅ Fetched {len(prices)} real prices")
            return prices
        else:
            print(f"⚠️ CoinGecko API returned status {response.status_code}")
            return {}

    except Exception as e:
        print(f"⚠️ Failed to fetch real prices: {e}")
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

        # Symbol configuration
        self.symbols_config = {
            'BTC': 45000,
            'ETH': 2500,
            'SOL': 100,
            'BNB': 350,
            'ADA': 0.50,
            'DOT': 7,
            'LINK': 15,
            'MATIC': 0.80,
            'UNI': 6,
            'AVAX': 35
        }

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

            # Fetch REAL current market prices
            real_prices = fetch_real_prices()
            if real_prices:
                # Update symbol config with real prices
                self.symbols_config.update(real_prices)
                print(f"✅ Using REAL market prices for {len(real_prices)} symbols")
            else:
                print("⚠️ Using fallback prices (failed to fetch real data)")

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
            # Strategy engine expects price history
            if len(price_history) < 20:  # FAST: Reduced from 50 to 20
                return None  # Need enough history

            # Calculate indicators
            self.strategy_engine.calculate_indicators(price_history)

            # Get signal based on current strategy
            # For now, use RSI strategy as example
            # TODO: Implement strategy selector to choose from 24 strategies

            indicators = self.strategy_engine.get_indicators()

            if not indicators:
                return None

            # RSI strategy (default)
            if self.current_strategy == "rsi_strategy":
                rsi = indicators.get("rsi")
                if rsi is None:
                    return None

                if rsi < 30:
                    return "BUY"
                elif rsi > 70:
                    return "SELL"

            # SMA crossover strategy
            elif self.current_strategy == "sma_crossover":
                sma_short = indicators.get("sma_short")
                sma_long = indicators.get("sma_long")

                if sma_short is None or sma_long is None:
                    return None

                # Bullish crossover
                if sma_short > sma_long:
                    return "BUY"
                # Bearish crossover
                elif sma_short < sma_long:
                    return "SELL"

            # MACD strategy
            elif self.current_strategy == "macd":
                macd = indicators.get("macd")
                macd_signal = indicators.get("macd_signal")

                if macd is None or macd_signal is None:
                    return None

                # Bullish crossover
                if macd > macd_signal:
                    return "BUY"
                # Bearish crossover
                elif macd < macd_signal:
                    return "SELL"

            return None

        except Exception as e:
            print(f"Error getting strategy signal: {e}")
            return None

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
