#!/usr/bin/env python3
"""
Final comprehensive system test for JJ-Bot Professional
"""

import asyncio
import requests
import time
import sys
from datetime import datetime

class JJBotSystemTest:
    """Comprehensive system test suite"""
    
    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
        self.results = {}
        
    def test_api_health(self):
        """Test basic API health"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200, response.json()
        except Exception as e:
            return False, str(e)
    
    def test_trading_endpoints(self):
        """Test trading-related endpoints"""
        endpoints = [
            "/api/trades/summary",
            "/api/trades/log", 
            "/risk_status"
        ]
        
        results = {}
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                results[endpoint] = {
                    "status": response.status_code,
                    "success": response.status_code == 200,
                    "data_size": len(response.text)
                }
            except Exception as e:
                results[endpoint] = {"success": False, "error": str(e)}
        
        return results
    
    def test_analytics_endpoints(self):
        """Test analytics endpoints"""
        endpoints = [
            "/api/analytics/performance",
            "/api/analytics/daily-pnl",
            "/api/analytics/metrics-summary"
        ]
        
        results = {}
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                results[endpoint] = {
                    "status": response.status_code,
                    "success": response.status_code == 200,
                    "data_size": len(response.text)
                }
            except Exception as e:
                results[endpoint] = {"success": False, "error": str(e)}
        
        return results
    
    def test_market_data_endpoints(self):
        """Test market data endpoints"""
        endpoints = [
            "/api/market/live/BTCUSDT",
            "/api/market/overview",
            "/api/market/status"
        ]
        
        results = {}
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                results[endpoint] = {
                    "status": response.status_code,
                    "success": response.status_code == 200,
                    "data_size": len(response.text)
                }
            except Exception as e:
                results[endpoint] = {"success": False, "error": str(e)}
        
        return results
    
    def test_strategy_endpoints(self):
        """Test strategy endpoints"""
        endpoints = [
            "/api/strategies/list",
            "/api/strategies/analysis"
        ]
        
        results = {}
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                results[endpoint] = {
                    "status": response.status_code,
                    "success": response.status_code == 200,
                    "data_size": len(response.text)
                }
            except Exception as e:
                results[endpoint] = {"success": False, "error": str(e)}
        
        return results
    
    def test_notification_endpoints(self):
        """Test notification endpoints"""
        endpoints = [
            "/api/notifications/status",
            "/api/notifications/config"
        ]
        
        results = {}
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                results[endpoint] = {
                    "status": response.status_code,
                    "success": response.status_code == 200,
                    "data_size": len(response.text)
                }
            except Exception as e:
                results[endpoint] = {"success": False, "error": str(e)}
        
        return results
    
    def test_system_endpoints(self):
        """Test system monitoring endpoints"""
        endpoints = [
            "/api/system/metrics",
            "/api/system/health",
            "/api/system/overview"
        ]
        
        results = {}
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                results[endpoint] = {
                    "status": response.status_code,
                    "success": response.status_code == 200,
                    "data_size": len(response.text)
                }
            except Exception as e:
                results[endpoint] = {"success": False, "error": str(e)}
        
        return results
    
    def test_dashboard_access(self):
        """Test dashboard accessibility"""
        try:
            response = requests.get(f"{self.base_url}/dashboard/", timeout=10)
            return {
                "status": response.status_code,
                "success": response.status_code == 200,
                "content_type": response.headers.get('content-type', ''),
                "size": len(response.text)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def run_comprehensive_test(self):
        """Run all system tests"""
        print("🧪 JJ-Bot Professional System Test Suite")
        print("=" * 60)
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Test 1: API Health
        print("🏥 Testing API Health...")
        health_ok, health_data = self.test_api_health()
        print(f"   {'✅' if health_ok else '❌'} API Health: {'OK' if health_ok else 'FAILED'}")
        if not health_ok:
            print(f"      Error: {health_data}")
            return False
        
        # Test 2: Trading Endpoints
        print("\n📈 Testing Trading Endpoints...")
        trading_results = self.test_trading_endpoints()
        for endpoint, result in trading_results.items():
            status = '✅' if result.get('success') else '❌'
            print(f"   {status} {endpoint}: {'OK' if result.get('success') else 'FAILED'}")
        
        # Test 3: Analytics Endpoints
        print("\n🧠 Testing Analytics Endpoints...")
        analytics_results = self.test_analytics_endpoints()
        for endpoint, result in analytics_results.items():
            status = '✅' if result.get('success') else '❌'
            print(f"   {status} {endpoint}: {'OK' if result.get('success') else 'FAILED'}")
        
        # Test 4: Market Data Endpoints
        print("\n🌍 Testing Market Data Endpoints...")
        market_results = self.test_market_data_endpoints()
        for endpoint, result in market_results.items():
            status = '✅' if result.get('success') else '❌'
            print(f"   {status} {endpoint}: {'OK' if result.get('success') else 'FAILED'}")
        
        # Test 5: Strategy Endpoints
        print("\n🎯 Testing Strategy Endpoints...")
        strategy_results = self.test_strategy_endpoints()
        for endpoint, result in strategy_results.items():
            status = '✅' if result.get('success') else '❌'
            print(f"   {status} {endpoint}: {'OK' if result.get('success') else 'FAILED'}")
        
        # Test 6: Notification Endpoints
        print("\n📱 Testing Notification Endpoints...")
        notification_results = self.test_notification_endpoints()
        for endpoint, result in notification_results.items():
            status = '✅' if result.get('success') else '❌'
            print(f"   {status} {endpoint}: {'OK' if result.get('success') else 'FAILED'}")
        
        # Test 7: System Monitoring Endpoints
        print("\n🖥️ Testing System Monitoring Endpoints...")
        system_results = self.test_system_endpoints()
        for endpoint, result in system_results.items():
            status = '✅' if result.get('success') else '❌'
            print(f"   {status} {endpoint}: {'OK' if result.get('success') else 'FAILED'}")
        
        # Test 8: Dashboard Access
        print("\n🌐 Testing Dashboard Access...")
        dashboard_result = self.test_dashboard_access()
        status = '✅' if dashboard_result.get('success') else '❌'
        print(f"   {status} Dashboard: {'OK' if dashboard_result.get('success') else 'FAILED'}")
        
        # Calculate overall success rate
        all_results = [
            trading_results, analytics_results, market_results, 
            strategy_results, notification_results, system_results
        ]
        
        total_tests = sum(len(results) for results in all_results) + 2  # +2 for health and dashboard
        successful_tests = sum(
            sum(1 for result in results.values() if result.get('success', False))
            for results in all_results
        )
        
        if health_ok:
            successful_tests += 1
        if dashboard_result.get('success'):
            successful_tests += 1
        
        success_rate = (successful_tests / total_tests) * 100
        
        print(f"\n📊 Test Results Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Successful: {successful_tests}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print(f"\n🎉 JJ-Bot Professional is READY FOR TRADING! 🚀")
            print(f"\n🌐 Access your platform at: http://127.0.0.1:8000/dashboard/")
        elif success_rate >= 70:
            print(f"\n⚠️ JJ-Bot is mostly functional but has some issues")
        else:
            print(f"\n❌ JJ-Bot has significant issues that need to be resolved")
        
        return success_rate >= 70

async def main():
    """Main test runner"""
    tester = JJBotSystemTest()
    success = await tester.run_comprehensive_test()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
