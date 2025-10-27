#!/usr/bin/env python3
"""
Comprehensive test for Enterprise Backup/Restore and Developer Dashboard
"""

import asyncio
import requests
import time
import sys
from datetime import datetime

class EnterpriseSystemTest:
    """Test the new enterprise features"""
    
    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
        
    def test_backup_system(self):
        """Test backup creation"""
        try:
            from ops.backup.enterprise_backup_manager import backup_manager
            
            # Test backup creation
            result = backup_manager.create_backup('config', 'Test config backup')
            
            if result['status'] == 'completed':
                print("✅ Backup system: Working")
                return True
            else:
                print(f"❌ Backup system: Failed - {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Backup system: Error - {e}")
            return False
    
    def test_admin_endpoints(self):
        """Test admin dashboard endpoints"""
        admin_endpoints = [
            "/api/admin/dashboard",
            "/api/admin/backup/list",
            "/api/admin/logs/api",
            "/api/admin/database/stats",
            "/api/admin/config/list",
            "/api/admin/test/endpoints"
        ]
        
        passed = 0
        total = len(admin_endpoints)
        
        for endpoint in admin_endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                if response.status_code == 200:
                    print(f"✅ {endpoint}: Working")
                    passed += 1
                else:
                    print(f"❌ {endpoint}: HTTP {response.status_code}")
            except Exception as e:
                print(f"❌ {endpoint}: Error - {e}")
        
        print(f"📊 Admin endpoints: {passed}/{total} passed")
        return passed >= total * 0.8  # 80% pass rate
    
    def test_developer_dashboard(self):
        """Test developer dashboard accessibility"""
        try:
            # Test if dashboard loads
            response = requests.get(f"{self.base_url}/dashboard/", timeout=10)
            
            if response.status_code == 200:
                print("✅ Developer dashboard: Accessible")
                return True
            else:
                print(f"❌ Developer dashboard: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Developer dashboard: Error - {e}")
            return False
    
    def test_restore_system(self):
        """Test restore system (without actually restoring)"""
        try:
            from ops.restore.enterprise_restore_manager import restore_manager
            
            # Test listing backups for restore
            backups = restore_manager.list_available_backups()
            
            if isinstance(backups, list):
                print(f"✅ Restore system: Working ({len(backups)} backups available)")
                return True
            else:
                print("❌ Restore system: Failed to list backups")
                return False
                
        except Exception as e:
            print(f"❌ Restore system: Error - {e}")
            return False
    
    async def run_enterprise_tests(self):
        """Run all enterprise system tests"""
        print("🧪 JJ-Bot Enterprise System Test Suite")
        print("=" * 60)
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        tests = [
            ("Backup System", self.test_backup_system),
            ("Admin Endpoints", self.test_admin_endpoints),
            ("Developer Dashboard", self.test_developer_dashboard),
            ("Restore System", self.test_restore_system)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            print(f"🧪 Testing {test_name}...")
            if test_func():
                passed_tests += 1
            print()
        
        # Summary
        success_rate = (passed_tests / total_tests) * 100
        
        print(f"📊 Enterprise Test Results:")
        print(f"   Tests Passed: {passed_tests}/{total_tests}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print(f"\n🎉 Enterprise System is READY! 🚀")
            print(f"\n🛠️ Access Developer Dashboard at: http://127.0.0.1:8000/dashboard/")
            print(f"   Click the 'Developer' tab for full admin features")
        else:
            print(f"\n❌ Enterprise system has issues that need attention")
        
        return success_rate >= 80

async def main():
    """Main test runner"""
    tester = EnterpriseSystemTest()
    success = await tester.run_enterprise_tests()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
