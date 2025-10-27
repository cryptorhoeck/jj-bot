#!/usr/bin/env python3
"""
Quick test script for JJ-Bot enhancements
"""

import requests
import json

def test_api_endpoints():
    base_url = "http://127.0.0.1:8000"
    
    endpoints = [
        "/api/summary",
        "/api/analytics/performance", 
        "/api/system/health",
        "/api/market/prices"
    ]
    
    print("Testing Enhanced JJ-Bot API Endpoints...")
    print("=" * 50)
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint} - OK")
            else:
                print(f"❌ {endpoint} - Status: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint} - Error: {str(e)}")
    
    print("=" * 50)
    print("Test complete!")

if __name__ == "__main__":
    test_api_endpoints()
