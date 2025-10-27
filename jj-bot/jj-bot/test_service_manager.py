#!/usr/bin/env python3
"""
Test Service Manager
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.manager import ServiceManager

def main():
    print("="*50)
    print("TESTING SERVICE MANAGER")
    print("="*50)
    
    # Create manager
    manager = ServiceManager()
    
    # List services
    print("\nAll Services:")
    for service in manager.get_all_services():
        print(f"  {service['name']}: {service['status']} (auto={service['auto_start']})")
    
    # Start a service
    print("\nStarting simulator...")
    result = manager.start_service("simulator")
    print(f"  Result: {result}")
    
    # Check status
    print("\nService status after start:")
    status = manager.get_service_status("simulator")
    print(f"  Simulator: {status['status']}")
    
    # Stop service
    print("\nStopping simulator...")
    result = manager.stop_service("simulator")
    print(f"  Result: {result}")
    
    # Auto-start test
    print("\nTesting auto-start services...")
    started = manager.start_auto_services()
    print(f"  Started: {started}")
    
    print("\nFinal status:")
    for service in manager.get_all_services():
        print(f"  {service['name']}: {service['status']}")
    
    print("\n✅ Service Manager test complete!")

if __name__ == "__main__":
    main()
