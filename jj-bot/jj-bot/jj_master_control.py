#!/usr/bin/env python3
"""
JJ-Bot Master Control Script
Manages all components of the professional trading platform
"""

import asyncio
import subprocess
import time
import signal
import sys
from pathlib import Path

class JJBotMaster:
    """Master controller for all JJ-Bot services"""
    
    def __init__(self):
        self.services = {}
        self.running = False
        
    async def start_api_server(self):
        """Start the main API server"""
        print("🌐 Starting API server...")
        process = await asyncio.create_subprocess_exec(
            'uvicorn', 'glue.api.main:app', '--host', '0.0.0.0', '--port', '8000', '--reload',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        self.services['api'] = process
        return process
    
    async def start_notification_monitor(self):
        """Start notification monitoring"""
        print("📱 Starting notification monitor...")
        process = await asyncio.create_subprocess_exec(
            'python3', 'glue/api/notification_integration.py',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        self.services['notifications'] = process
        return process
    
    async def start_system_monitor(self):
        """Start system monitoring"""
        print("🖥️ Starting system monitor...")
        
        # Import and start the system monitor
        from hands.system_monitor import system_monitor
        
        # Start monitoring in background task
        monitor_task = asyncio.create_task(system_monitor.start_monitoring(interval=60))
        self.services['system_monitor'] = monitor_task
        
        return monitor_task
    
    async def start_all_services(self):
        """Start all JJ-Bot services"""
        print("🚀 Starting JJ-Bot Professional Trading Platform...")
        print("=" * 60)
        
        self.running = True
        
        try:
            # Start core services
            await self.start_api_server()
            await asyncio.sleep(3)  # Wait for API to start
            
            await self.start_system_monitor()
            await asyncio.sleep(2)
            
            await self.start_notification_monitor()
            
            print("\n✅ All services started successfully!")
            print("\n🌐 Access your trading platform:")
            print("   Dashboard: http://127.0.0.1:8000/dashboard/")
            print("   API Docs:  http://127.0.0.1:8000/docs")
            print("\n📊 Available endpoints:")
            print("   /api/trades/log - Recent trades")
            print("   /api/analytics/performance - Performance metrics") 
            print("   /api/market/live/BTCUSDT - Live market data")
            print("   /api/strategies/analysis - Strategy signals")
            print("   /api/system/overview - System overview")
            print("\n🎮 Control commands:")
            print("   ./jj trade   - Start trade simulator")
            print("   ./jj live    - Start live trading")
            print("   ./jj alerts  - Manage notifications")
            print("   ./jj status  - Check system status")
            
            # Keep services running
            while self.running:
                await self.check_service_health()
                await asyncio.sleep(30)
                
        except KeyboardInterrupt:
            print("\n🛑 Shutting down JJ-Bot...")
            await self.stop_all_services()
        except Exception as e:
            print(f"❌ Error starting services: {e}")
            await self.stop_all_services()
    
    async def check_service_health(self):
        """Check health of all services"""
        for service_name, service in self.services.items():
            if isinstance(service, asyncio.subprocess.Process):
                if service.returncode is not None:
                    print(f"⚠️ Service {service_name} has stopped (code: {service.returncode})")
            elif isinstance(service, asyncio.Task):
                if service.done():
                    print(f"⚠️ Task {service_name} has completed")
    
    async def stop_all_services(self):
        """Stop all services gracefully"""
        print("🛑 Stopping all services...")
        
        self.running = False
        
        for service_name, service in self.services.items():
            try:
                if isinstance(service, asyncio.subprocess.Process):
                    service.terminate()
                    await service.wait()
                elif isinstance(service, asyncio.Task):
                    service.cancel()
                    try:
                        await service
                    except asyncio.CancelledError:
                        pass
                        
                print(f"✅ Stopped {service_name}")
            except Exception as e:
                print(f"❌ Error stopping {service_name}: {e}")
        
        print("🛑 All services stopped")

async def main():
    """Main entry point"""
    master = JJBotMaster()
    
    # Handle shutdown gracefully
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}")
        master.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    await master.start_all_services()

if __name__ == "__main__":
    asyncio.run(main())
