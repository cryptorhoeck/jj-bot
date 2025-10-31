"""
Integration Test Suite v3 - WebSocket and Backtesting
Tests the new WebSocket real-time updates and backtesting framework
"""

import sys
import os
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_websocket_manager():
    """Test WebSocket manager initialization"""
    print("\n" + "="*60)
    print("TEST 1: WebSocket Manager")
    print("="*60)

    try:
        from glue.api.websocket_manager import ws_manager

        # Check initialization
        assert ws_manager is not None, "WebSocket manager not initialized"
        assert ws_manager.stats is not None, "Stats not initialized"

        # Check stats structure
        required_stats = ["total_connections", "current_connections", "messages_sent", "events_received"]
        for stat in required_stats:
            assert stat in ws_manager.stats, f"Missing stat: {stat}"

        print("✅ PASS - WebSocket Manager initialized correctly")
        print(f"   Stats: {ws_manager.stats}")
        return True

    except Exception as e:
        print(f"❌ FAIL - WebSocket Manager error: {e}")
        return False


def test_strategy_service():
    """Test Strategy Service"""
    print("\n" + "="*60)
    print("TEST 2: Strategy Service")
    print("="*60)

    try:
        from services.trading.strategy_service import StrategyService

        # Create service
        service = StrategyService()

        # Check initialization
        assert service.name == "strategy_engine", "Service name incorrect"
        assert service.auto_start == True, "Auto-start should be enabled"
        assert service.config is not None, "Config not initialized"

        # Check configuration
        assert "rsi_oversold" in service.config
        assert "rsi_overbought" in service.config
        assert "sma_fast" in service.config
        assert "sma_slow" in service.config

        print("✅ PASS - Strategy Service initialized correctly")
        print(f"   Name: {service.name}")
        print(f"   Auto-start: {service.auto_start}")
        print(f"   Config: {service.config}")
        return True

    except Exception as e:
        print(f"❌ FAIL - Strategy Service error: {e}")
        return False


def test_backtester():
    """Test Backtesting Engine"""
    print("\n" + "="*60)
    print("TEST 3: Backtesting Engine")
    print("="*60)

    try:
        from modules.backtesting.backtester import Backtester

        # Create backtester
        backtester = Backtester(initial_capital=10000.0)

        # Check initialization
        assert backtester.initial_capital == 10000.0, "Initial capital incorrect"
        assert backtester.current_capital == 10000.0, "Current capital should match initial"
        assert backtester.strategy is not None, "Strategy not initialized"
        assert backtester.config is not None, "Config not initialized"

        # Check configuration
        assert "commission" in backtester.config
        assert "slippage" in backtester.config
        assert "position_size" in backtester.config

        print("✅ PASS - Backtesting Engine initialized correctly")
        print(f"   Initial Capital: ${backtester.initial_capital:,.2f}")
        print(f"   Commission: {backtester.config['commission']:.2%}")
        print(f"   Slippage: {backtester.config['slippage']:.2%}")
        print(f"   Position Size: {backtester.config['position_size']:.1%}")
        return True

    except Exception as e:
        print(f"❌ FAIL - Backtesting Engine error: {e}")
        return False


def test_backtest_execution():
    """Test running a simple backtest"""
    print("\n" + "="*60)
    print("TEST 4: Backtest Execution")
    print("="*60)

    try:
        from modules.backtesting.backtester import Backtester
        import random

        # Create backtester
        backtester = Backtester(initial_capital=10000.0)

        # Generate sample data
        print("   Generating sample data...")
        symbol = "BTC"
        data = []
        base_price = 45000
        current_price = base_price

        for i in range(100):  # 100 data points
            change = random.uniform(-0.01, 0.01)
            current_price *= (1 + change)

            data.append({
                "price": current_price,
                "timestamp": f"2024-01-{i//24 + 1:02d}T{i%24:02d}:00:00",
                "volume": random.uniform(1000, 5000)
            })

        # Load data
        success = backtester.load_historical_data(symbol, data)
        assert success, "Failed to load historical data"
        print(f"   ✓ Loaded {len(data)} data points")

        # Run backtest
        print("   Running backtest...")
        results = backtester.run_backtest(symbol)

        # Check results
        assert "error" not in results, f"Backtest error: {results.get('error')}"
        assert "metrics" in results, "Missing metrics in results"
        assert "trades" in results, "Missing trades in results"
        assert "equity_curve" in results, "Missing equity curve in results"

        print("✅ PASS - Backtest executed successfully")
        print(f"   Total Trades: {results['total_trades']}")
        print(f"   Final Capital: ${results['final_capital']:,.2f}")
        print(f"   Total Return: {results['total_return']:.2f}%")
        print(f"   Win Rate: {results['metrics']['win_rate']:.2f}%")
        return True

    except Exception as e:
        print(f"❌ FAIL - Backtest execution error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_service_manager_v3():
    """Test Service Manager with all 5 services"""
    print("\n" + "="*60)
    print("TEST 5: Service Manager (5 Services)")
    print("="*60)

    try:
        from services.manager_v2 import ServiceManager

        # Create manager
        manager = ServiceManager()

        # Check all services are registered
        expected_services = ["simulator", "market_feed", "strategy_engine", "analytics", "trading_bot"]

        for service_name in expected_services:
            assert service_name in manager.services, f"Service {service_name} not found"

        print("✅ PASS - All 5 services registered")
        for name in expected_services:
            print(f"   ✓ {name}")
        return True

    except Exception as e:
        print(f"❌ FAIL - Service Manager error: {e}")
        return False


def test_api_endpoints():
    """Test API structure with new endpoints"""
    print("\n" + "="*60)
    print("TEST 6: API Endpoints")
    print("="*60)

    try:
        # Check backtest endpoints file exists
        backtest_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "glue", "api", "backtest_endpoints.py"
        )
        assert os.path.exists(backtest_file), "Backtest endpoints file not found"

        # Check websocket manager exists
        ws_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "glue", "api", "websocket_manager.py"
        )
        assert os.path.exists(ws_file), "WebSocket manager file not found"

        print("✅ PASS - API structure validated")
        print("   ✓ backtest_endpoints.py exists")
        print("   ✓ websocket_manager.py exists")
        return True

    except Exception as e:
        print(f"❌ FAIL - API structure error: {e}")
        return False


def run_all_tests():
    """Run all integration tests"""
    print("\n" + "="*60)
    print("INTEGRATION TEST SUITE V3")
    print("Testing: WebSocket, Strategy Service, Backtesting")
    print("="*60)

    tests = [
        ("WebSocket Manager", test_websocket_manager),
        ("Strategy Service", test_strategy_service),
        ("Backtesting Engine", test_backtester),
        ("Backtest Execution", test_backtest_execution),
        ("Service Manager (5 Services)", test_service_manager_v3),
        ("API Endpoints", test_api_endpoints)
    ]

    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print("="*60)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests PASSED! System is ready.")
    else:
        print("⚠️ Some tests failed. Please review errors above.")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
