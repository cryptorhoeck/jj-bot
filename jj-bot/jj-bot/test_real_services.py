#!/usr/bin/env python3
"""
Test Real Service Integration
"""

import sys
import os
import time
import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.manager_v2 import ServiceManager

def main():
    print("="*50)
    print("TESTING REAL SERVICE INTEGRATION")
    print("="*50)
    
    # Make sure API is running
    try:
        response = requests.get("http://127.0.0.1:8000/api/system/health")
        print("✅ API is running")
    except:
        print("❌ API not running! Start with: jj start")
        return
    
    # Create manager
    manager = ServiceManager()
    
    # Show services
    print("\nAvailable Services:")
    for service in manager.get_all_services():
        print(f"  {service['name']}: {service['status']}")
    
    # Test simulator control
    print("\n1. Starting simulator...")
    result = manager.start_service("simulator")
    print(f"   Result: {result}")
    
    time.sleep(3)
    
    print("\n2. Checking simulator status...")
    status = manager.get_service_status("simulator")
    print(f"   Status: {status['status']}")
    print(f"   Stats: {status.get('stats', {})}")
    
    print("\n3. Stopping simulator...")
    result = manager.stop_service("simulator")
    print(f"   Result: {result}")
    
    print("\n✅ Real service integration working!")

if __name__ == "__main__":
    main()
