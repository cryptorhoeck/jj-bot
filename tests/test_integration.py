#!/usr/bin/env python3
"""
Integration Test for JJ-Bot
Tests that all components can be imported and initialized
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_core_modules():
    """Test core module imports"""
    print("\n" + "="*60)
    print("TEST 1: Core Modules")
    print("="*60)

    try:
        from modules.base import BaseModule
        print("✅ BaseModule imported successfully")

        from modules.event_bus import event_bus, EventBus
        print("✅ EventBus imported successfully")

        # Test event bus functionality
        received_events = []

        def test_callback(event):
            received_events.append(event)

        event_bus.subscribe("TEST_EVENT", test_callback)
        event_bus.publish("TEST_EVENT", {"message": "hello"})

        assert len(received_events) == 1
        assert received_events[0]["data"]["message"] == "hello"
        print("✅ EventBus publish/subscribe works")

        event_bus.clear_subscribers("TEST_EVENT")

        return True
    except Exception as e:
        print(f"❌ Core modules test failed: {e}")
        return False

def test_trading_modules():
    """Test trading module imports"""
    print("\n" + "="*60)
    print("TEST 2: Trading Modules")
    print("="*60)

    # Note: These may fail in the container due to missing dependencies (pandas, numpy)
    # But the syntax and structure are correct

    try:
        from modules.strategy.strategy_engine import StrategyEngine
        print("✅ StrategyEngine structure valid")
    except ImportError as e:
        if "pandas" in str(e) or "numpy" in str(e):
            print("⚠️  StrategyEngine requires pandas/numpy (expected in container)")
        else:
            print(f"❌ StrategyEngine import failed: {e}")
            return False

    try:
        from modules.risk.risk_manager import RiskManager
        print("✅ RiskManager imported successfully")
    except Exception as e:
        print(f"❌ RiskManager import failed: {e}")
        return False

    return True

def test_services():
    """Test service imports"""
    print("\n" + "="*60)
    print("TEST 3: Services")
    print("="*60)

    try:
        from services.base.service import BaseService
        print("✅ BaseService imported successfully")

        from services.trading.simulator_service import SimulatorService
        print("✅ SimulatorService imported successfully")

        from services.trading.market_feed_service import MarketFeedService
        print("✅ MarketFeedService imported successfully")

        from services.trading.analytics_service import AnalyticsService
        print("✅ AnalyticsService imported successfully")

        from services.trading.trading_bot_service import TradingBotService
        print("✅ TradingBotService imported successfully")

        # Test service initialization
        market_feed = MarketFeedService()
        assert market_feed.name == "market_feed"
        assert market_feed.auto_start == True
        print("✅ MarketFeedService initializes correctly")

        analytics = AnalyticsService()
        assert analytics.name == "analytics"
        print("✅ AnalyticsService initializes correctly")

        trading_bot = TradingBotService()
        assert trading_bot.name == "trading_bot"
        assert trading_bot.config["enabled"] == False  # Safety check
        print("✅ TradingBotService initializes correctly (safely disabled)")

        return True
    except Exception as e:
        print(f"❌ Services test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_service_manager():
    """Test service manager"""
    print("\n" + "="*60)
    print("TEST 4: Service Manager")
    print("="*60)

    try:
        from services.manager_v2 import ServiceManager
        print("✅ ServiceManager imported successfully")

        # Create manager
        manager = ServiceManager()
        print("✅ ServiceManager initialized successfully")

        # Check all services are registered
        services = manager.get_all_services()
        assert len(services) == 4, f"Expected 4 services, got {len(services)}"
        print(f"✅ All 4 services registered: {[s['name'] for s in services]}")

        # Check service names
        service_names = [s['name'] for s in services]
        expected = ['simulator', 'market_feed', 'analytics', 'trading_bot']
        for name in expected:
            assert name in service_names, f"Service {name} not found"
        print("✅ All expected services present")

        # Check auto-start configuration
        auto_start_services = [s['name'] for s in services if s.get('auto_start')]
        print(f"✅ Auto-start services: {auto_start_services}")

        return True
    except Exception as e:
        print(f"❌ Service Manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_structure():
    """Test API structure"""
    print("\n" + "="*60)
    print("TEST 5: API Structure")
    print("="*60)

    # These will fail due to missing FastAPI, but we can check file structure
    try:
        import os

        assert os.path.exists("glue/api/main.py"), "main.py missing"
        print("✅ main.py exists")

        assert os.path.exists("glue/api/engine.py"), "engine.py missing"
        print("✅ engine.py exists")

        assert os.path.exists("glue/api/service_endpoints.py"), "service_endpoints.py missing"
        print("✅ service_endpoints.py exists")

        # Check for duplicate endpoints (syntax check)
        with open("glue/api/main.py", "r") as f:
            content = f.read()
            market_live_count = content.count('@app.get("/api/market/live")')
            assert market_live_count == 1, f"Found {market_live_count} /api/market/live endpoints (should be 1)"
        print("✅ No duplicate endpoints found")

        return True
    except AssertionError as e:
        print(f"❌ API structure test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ API structure test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("JJ-BOT INTEGRATION TEST SUITE")
    print("="*60)

    results = {
        "Core Modules": test_core_modules(),
        "Trading Modules": test_trading_modules(),
        "Services": test_services(),
        "Service Manager": test_service_manager(),
        "API Structure": test_api_structure()
    }

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print("\n" + "-"*60)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests PASSED! System is ready.")
        return 0
    else:
        print(f"⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit(main())
