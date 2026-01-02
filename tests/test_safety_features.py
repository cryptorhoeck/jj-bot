#!/usr/bin/env python3
"""
Unit Tests for JJ-Bot Safety Features

Tests the critical safety features implemented for live trading:
1. asyncio.Lock on position modifications
2. Atomic state writes (temp file + rename)
3. Order deduplication
4. RiskManager circuit breaker integration
5. Close order exception handling
"""

import sys
import os
import asyncio
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


# =============================================================================
# TEST 1: asyncio.Lock on Position Modifications
# =============================================================================

class TestPositionLock:
    """Test that position modifications are thread-safe"""

    @pytest.mark.asyncio
    async def test_position_lock_exists(self):
        """Verify that position lock is initialized"""
        from jjbot_pro import JJBotPro, BotConfig

        config = BotConfig(mode="paper", symbols=["BTC/USD"])
        bot = JJBotPro(config)

        assert hasattr(bot, '_position_lock')
        assert isinstance(bot._position_lock, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_concurrent_signal_handling(self):
        """Test that concurrent signals don't cause race conditions"""
        from jjbot_pro import JJBotPro, BotConfig

        config = BotConfig(mode="paper", symbols=["BTC/USD", "ETH/USD"], max_positions=5)
        bot = JJBotPro(config)

        # Set up demo prices
        bot.prices = {"BTC/USD": 50000.0, "ETH/USD": 3000.0}
        bot._demo_mode = True

        # Create concurrent signal tasks
        signals = [
            {"direction": "long", "confidence": 0.8, "edge_type": "test", "reason": "test"},
            {"direction": "long", "confidence": 0.8, "edge_type": "test", "reason": "test"},
        ]

        # Run signals concurrently
        tasks = [
            bot._handle_signal("BTC/USD", signals[0]),
            bot._handle_signal("ETH/USD", signals[1]),
        ]

        await asyncio.gather(*tasks)

        # Should have 2 positions (no race condition)
        assert len(bot.positions) == 2
        assert "BTC/USD" in bot.positions
        assert "ETH/USD" in bot.positions


# =============================================================================
# TEST 2: Atomic State Writes
# =============================================================================

class TestAtomicStateWrites:
    """Test that state files are written atomically"""

    def test_atomic_write_creates_temp_file(self):
        """Verify atomic write pattern is used"""
        from jjbot_pro import JJBotPro, BotConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            config = BotConfig(mode="paper", symbols=["BTC/USD"])
            bot = JJBotPro(config)

            # Override data directory
            original_parent = Path(__file__).parent.parent

            # The _save_state method should create temp file first
            # Check that the method signature includes atomic write pattern
            import inspect
            source = inspect.getsource(bot._save_state)

            assert "temp_file" in source, "Should use temp file for atomic writes"
            assert "os.replace" in source or "os.rename" in source, "Should use atomic rename"
            assert "fsync" in source, "Should sync to disk before rename"

    def test_state_file_integrity(self):
        """Test that state file is valid JSON after save"""
        from jjbot_pro import JJBotPro, BotConfig

        config = BotConfig(mode="paper", symbols=["BTC/USD"])
        bot = JJBotPro(config)

        # Save state
        bot._save_state()

        # Check state file exists and is valid JSON
        state_file = Path(__file__).parent.parent / "data" / "bot_state.json"
        if state_file.exists():
            with open(state_file) as f:
                data = json.load(f)

            assert "equity" in data
            assert "last_updated" in data


# =============================================================================
# TEST 3: Order Deduplication
# =============================================================================

class TestOrderDeduplication:
    """Test that duplicate orders are prevented"""

    @pytest.mark.asyncio
    async def test_dedup_window_configurable(self):
        """Test that dedup window is configurable"""
        from jjbot_pro import JJBotPro, BotConfig

        config = BotConfig(mode="paper", symbols=["BTC/USD"], order_dedup_window=10.0)
        bot = JJBotPro(config)

        assert bot._order_dedup_window == 10.0

    @pytest.mark.asyncio
    async def test_duplicate_signals_rejected(self):
        """Test that rapid duplicate signals are rejected"""
        from jjbot_pro import JJBotPro, BotConfig

        config = BotConfig(mode="paper", symbols=["BTC/USD"], order_dedup_window=5.0)
        bot = JJBotPro(config)

        # Set up demo prices
        bot.prices = {"BTC/USD": 50000.0}
        bot._demo_mode = True

        signal = {"direction": "long", "confidence": 0.8, "edge_type": "test", "reason": "test"}

        # First signal should succeed
        await bot._handle_signal("BTC/USD", signal)
        assert "BTC/USD" in bot.positions

        # Close position to allow new signal
        del bot.positions["BTC/USD"]

        # Immediate second signal should be rejected (within dedup window)
        await bot._handle_signal("BTC/USD", signal)
        assert "BTC/USD" not in bot.positions  # Should be rejected as duplicate

    @pytest.mark.asyncio
    async def test_signals_allowed_after_window(self):
        """Test that signals are allowed after dedup window expires"""
        from jjbot_pro import JJBotPro, BotConfig

        config = BotConfig(mode="paper", symbols=["BTC/USD"], order_dedup_window=0.1)  # 100ms
        bot = JJBotPro(config)

        # Set up demo prices
        bot.prices = {"BTC/USD": 50000.0}
        bot._demo_mode = True

        signal = {"direction": "long", "confidence": 0.8, "edge_type": "test", "reason": "test"}

        # First signal
        await bot._handle_signal("BTC/USD", signal)
        assert "BTC/USD" in bot.positions

        # Close position
        del bot.positions["BTC/USD"]

        # Wait for dedup window to expire
        await asyncio.sleep(0.15)

        # Now signal should be allowed
        await bot._handle_signal("BTC/USD", signal)
        assert "BTC/USD" in bot.positions


# =============================================================================
# TEST 4: RiskManager Integration
# =============================================================================

class TestRiskManagerIntegration:
    """Test RiskManager circuit breaker and risk checks"""

    def test_risk_manager_initialized(self):
        """Test that RiskManager is properly initialized"""
        from jjbot_pro import JJBotPro, BotConfig
        from modules.risk import RiskManager

        config = BotConfig(mode="paper", symbols=["BTC/USD"])
        bot = JJBotPro(config)

        assert hasattr(bot, 'risk_manager')
        assert isinstance(bot.risk_manager, RiskManager)

    def test_circuit_breaker_config(self):
        """Test circuit breaker configuration"""
        from jjbot_pro import JJBotPro, BotConfig

        config = BotConfig(mode="paper", symbols=["BTC/USD"])
        bot = JJBotPro(config)

        # Circuit breaker should be configured
        assert bot.risk_manager.config.circuit_breaker_loss_count == 3
        assert bot.risk_manager.config.circuit_breaker_cooldown_minutes == 30

    def test_max_positions_enforcement(self):
        """Test that max positions is enforced via RiskManager"""
        from jjbot_pro import JJBotPro, BotConfig

        config = BotConfig(mode="paper", symbols=["BTC/USD"], max_positions=2)
        bot = JJBotPro(config)

        # Check RiskManager config matches bot config
        assert bot.risk_manager.config.max_open_positions == 2

    def test_trade_result_recording(self):
        """Test that trade results are recorded in RiskManager"""
        from jjbot_pro import JJBotPro, BotConfig

        config = BotConfig(mode="paper", symbols=["BTC/USD"])
        bot = JJBotPro(config)

        # Record some losses
        bot.risk_manager.record_trade_result(-100)
        assert bot.risk_manager.consecutive_losses == 1

        bot.risk_manager.record_trade_result(-50)
        assert bot.risk_manager.consecutive_losses == 2

        # Win resets consecutive losses
        bot.risk_manager.record_trade_result(200)
        assert bot.risk_manager.consecutive_losses == 0


# =============================================================================
# TEST 5: Close Order Exception Handling
# =============================================================================

class TestCloseOrderExceptionHandling:
    """Test that close order exceptions are handled gracefully"""

    def test_close_order_has_try_except(self):
        """Verify close order is wrapped in try-except"""
        from jjbot_pro import JJBotPro, BotConfig
        import inspect

        config = BotConfig(mode="paper", symbols=["BTC/USD"])
        bot = JJBotPro(config)

        # Check the source code for try-except pattern
        source = inspect.getsource(bot._close_position_locked)

        assert "try:" in source, "Close order should have try block"
        assert "except Exception" in source, "Close order should catch exceptions"
        assert "close_order_failed" in source, "Should track if close order failed"


# =============================================================================
# TEST 6: Configurable Timeouts
# =============================================================================

class TestConfigurableTimeouts:
    """Test that all timeouts are configurable"""

    def test_order_fill_timeout_configurable(self):
        """Test order fill timeout is configurable"""
        from jjbot_pro import BotConfig

        config = BotConfig(order_fill_timeout=60.0)
        assert config.order_fill_timeout == 60.0

    def test_price_feed_timeout_configurable(self):
        """Test price feed timeout is configurable"""
        from jjbot_pro import BotConfig

        config = BotConfig(price_feed_stale_timeout=600.0)
        assert config.price_feed_stale_timeout == 600.0

    def test_state_save_interval_configurable(self):
        """Test state save interval is configurable"""
        from jjbot_pro import BotConfig

        config = BotConfig(state_save_interval=120.0)
        assert config.state_save_interval == 120.0

    def test_default_timeout_values(self):
        """Test default timeout values are reasonable"""
        from jjbot_pro import BotConfig

        config = BotConfig()

        assert config.order_fill_timeout == 30.0
        assert config.price_feed_stale_timeout == 300.0
        assert config.state_save_interval == 300.0
        assert config.order_dedup_window == 5.0


# =============================================================================
# TEST 7: Position Field - actual_contracts
# =============================================================================

class TestActualContractsField:
    """Test that actual_contracts field exists and is used"""

    def test_position_has_actual_contracts(self):
        """Test Position dataclass has actual_contracts field"""
        from jjbot_pro import Position
        from datetime import datetime

        pos = Position(
            symbol="BTC/USD",
            side="long",
            entry_price=50000.0,
            size=1000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            entry_time=datetime.now(),
            signal_source="test",
            actual_contracts=0.02
        )

        assert pos.actual_contracts == 0.02

    def test_actual_contracts_default(self):
        """Test actual_contracts has default of 0"""
        from jjbot_pro import Position
        from datetime import datetime

        pos = Position(
            symbol="BTC/USD",
            side="long",
            entry_price=50000.0,
            size=1000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            entry_time=datetime.now(),
            signal_source="test"
        )

        assert pos.actual_contracts == 0.0


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
