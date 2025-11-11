"""
Adaptive Strategy Selector

Automatically selects the best performing trading strategy based on:
- Recent performance metrics
- Market regime
- Strategy suitability for conditions

Switches strategies when a better option is found with sufficient confidence.
"""

from datetime import datetime
from typing import Dict, Optional
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from modules.learning.strategy_performance_tracker import StrategyPerformanceTracker
from modules.learning.market_regime_detector import MarketRegimeDetector, MarketRegime
from modules.database.connection import get_db_connection, LEARNING_DB_PATH


class AdaptiveStrategySelector:
    """
    Adaptively selects best trading strategy.

    Features:
    - Performance-based selection
    - Regime-aware recommendations
    - Confidence scoring
    - State persistence
    """

    def __init__(
        self,
        reevaluation_interval: int = 10,
        min_confidence: float = 0.6,
        lookback_hours: int = 24
    ):
        """
        Initialize adaptive strategy selector.

        Args:
            reevaluation_interval: Re-evaluate every N trades
            min_confidence: Minimum confidence to switch (0-1)
            lookback_hours: Hours of performance history to analyze
        """
        self.reevaluation_interval = reevaluation_interval
        self.min_confidence = min_confidence
        self.lookback_hours = lookback_hours

        self.performance_tracker = StrategyPerformanceTracker()
        self.regime_detector = MarketRegimeDetector()
        self.learning_db = LEARNING_DB_PATH

        # Initialize state
        self._load_state()

    def select_best_strategy(self, force: bool = False) -> Dict:
        """
        Select best strategy based on current performance.

        Args:
            force: Force re-evaluation regardless of interval

        Returns:
            Dict with strategy selection info
        """
        # Get current state
        state = self.get_state()

        if not state:
            # No state exists, initialize with default
            self._initialize_state()
            state = self.get_state()

        # Check if we should re-evaluate
        trades_since_switch = state['trades_since_switch']

        if not force and trades_since_switch < self.reevaluation_interval:
            # Not time to re-evaluate yet
            return {
                'strategy': state['current_strategy'],
                'switched': False,
                'confidence': state['confidence'],
                'trades_until_next_eval': self.reevaluation_interval - trades_since_switch
            }

        # Get performance recommendation
        recommendation = self.performance_tracker.recommend_strategy(
            period_hours=self.lookback_hours
        )

        if not recommendation:
            # No data, keep current
            return {
                'strategy': state['current_strategy'],
                'switched': False,
                'confidence': 0.0,
                'reason': 'No performance data available'
            }

        recommended_strategy = recommendation['strategy']
        confidence = recommendation['confidence']

        # Check if we should switch
        should_switch = False
        switch_reason = ""

        if recommended_strategy != state['current_strategy']:
            if confidence >= self.min_confidence:
                should_switch = True
                switch_reason = f"Better performance (confidence: {confidence:.2f})"

        if should_switch:
            # Update state with new strategy
            self._update_state(
                strategy=recommended_strategy,
                confidence=confidence
            )

            return {
                'strategy': recommended_strategy,
                'switched': True,
                'confidence': confidence,
                'reason': switch_reason,
                'previous_strategy': state['current_strategy'],
                'metrics': recommendation['metrics']
            }
        else:
            # Increment trades counter
            self._increment_trades_counter()

            return {
                'strategy': state['current_strategy'],
                'switched': False,
                'confidence': confidence,
                'reason': 'Current strategy still optimal' if recommended_strategy == state['current_strategy'] else f'Insufficient confidence ({confidence:.2f} < {self.min_confidence})',
                'trades_until_next_eval': self.reevaluation_interval
            }

    def get_state(self) -> Optional[Dict]:
        """
        Get current selector state.

        Returns:
            Dict with state info or None if no state exists
        """
        with get_db_connection(self.learning_db) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT current_strategy, confidence, trades_since_switch, last_switch_timestamp
                FROM strategy_selector_state
                WHERE id = 1
            """)

            row = cur.fetchone()

            if not row:
                return None

            return {
                'current_strategy': row[0],
                'confidence': row[1],
                'trades_since_switch': row[2],
                'last_switch_timestamp': row[3]
            }

    def _load_state(self):
        """Load state from database on initialization."""
        state = self.get_state()
        if not state:
            self._initialize_state()

    def _initialize_state(self, strategy: str = "rsi_strategy"):
        """
        Initialize selector state with default strategy.

        Args:
            strategy: Initial strategy to use
        """
        with get_db_connection(self.learning_db) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO strategy_selector_state
                (id, current_strategy, confidence, trades_since_switch, last_switch_timestamp)
                VALUES (1, ?, ?, ?, ?)
            """, (
                strategy,
                0.5,  # Default confidence
                0,    # No trades yet
                datetime.now().isoformat()
            ))
            conn.commit()

        print(f"📥 Initialized selector state: {strategy}")

    def _update_state(self, strategy: str, confidence: float):
        """
        Update selector state with new strategy.

        Args:
            strategy: New strategy name
            confidence: Confidence score
        """
        with get_db_connection(self.learning_db) as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE strategy_selector_state
                SET current_strategy = ?,
                    confidence = ?,
                    trades_since_switch = 0,
                    last_switch_timestamp = ?,
                    updated_at = datetime('now')
                WHERE id = 1
            """, (strategy, confidence, datetime.now().isoformat()))
            conn.commit()

        print(f"🔄 Strategy switched to: {strategy} (confidence: {confidence:.2f})")

    def _increment_trades_counter(self):
        """Increment trades since last switch counter."""
        with get_db_connection(self.learning_db) as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE strategy_selector_state
                SET trades_since_switch = trades_since_switch + 1,
                    updated_at = datetime('now')
                WHERE id = 1
            """)
            conn.commit()

    def notify_trade(self):
        """
        Notify selector that a trade occurred.

        Increments trade counter for re-evaluation timing.
        """
        self._increment_trades_counter()

    def force_strategy(self, strategy: str):
        """
        Force a specific strategy (for testing/manual control).

        Args:
            strategy: Strategy to force
        """
        self._update_state(strategy, 1.0)
        print(f"⚠️ Strategy manually forced to: {strategy}")
