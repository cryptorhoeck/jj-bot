from datetime import datetime
"""
Service Manager API Endpoints
Separate file to avoid touching main.py
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import sys
import os

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from services.manager_v2 import ServiceManager

# Create router
router = APIRouter(prefix="/api/services", tags=["services"])

# Initialize service manager
service_manager = ServiceManager()

@router.get("/list")
async def list_services():
    """List all services and their status"""
    return {
        "services": service_manager.get_all_services(),
        "timestamp": datetime.now().isoformat()
    }

@router.post("/{service_name}/start")
async def start_service(service_name: str):
    """Start a specific service"""
    result = service_manager.start_service(service_name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.post("/{service_name}/stop")
async def stop_service(service_name: str):
    """Stop a specific service"""
    result = service_manager.stop_service(service_name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.get("/{service_name}/status")
async def get_service_status(service_name: str):
    """Get status of a specific service"""
    status = service_manager.get_service_status(service_name)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    return status

@router.post("/auto-start")
async def start_auto_services():
    """Start all auto-start services"""
    started = service_manager.start_auto_services()
    return {
        "started": started,
        "count": len(started)
    }

@router.get("/status")
async def get_all_services_status():
    """Get status of all services"""
    services = {}
    for name in service_manager.services.keys():
        services[name] = service_manager.get_service_status(name)
    return {
        "services": services,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/{service_name}/data")
async def get_service_data(service_name: str):
    """Get data from a specific service"""
    if service_name not in service_manager.services:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")

    service = service_manager.services[service_name]

    # Get service-specific data
    if hasattr(service, 'get_data'):
        data = service.get_data()
        return {
            "service": service_name,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "service": service_name,
            "data": {},
            "message": "Service does not provide data",
            "timestamp": datetime.now().isoformat()
        }

@router.post("/simulator/generate")
async def generate_trades(num_trades: int = 50):
    """Generate test trades using simulator"""
    if "simulator" not in service_manager.services:
        raise HTTPException(status_code=404, detail="Simulator service not found")

    service = service_manager.services["simulator"]

    # Call simulator's generate method
    if hasattr(service, 'generate_trades'):
        result = service.generate_trades(num_trades)
        return {
            "success": True,
            "trades_generated": num_trades,
            "message": f"Successfully generated {num_trades} trades",
            "timestamp": datetime.now().isoformat()
        }
    else:
        raise HTTPException(status_code=400, detail="Simulator does not support trade generation")

@router.get("/realistic_simulator/positions")
async def get_open_positions():
    """Get currently open positions from realistic simulator"""
    if "realistic_simulator" not in service_manager.services:
        raise HTTPException(status_code=404, detail="Realistic simulator service not found")

    service = service_manager.services["realistic_simulator"]

    # Check if simulator is running and has market_simulator
    if not hasattr(service, 'market_simulator') or service.market_simulator is None:
        return {
            "positions": [],
            "count": 0,
            "message": "Simulator not initialized",
            "timestamp": datetime.now().isoformat()
        }

    # Get open positions
    open_positions = service.market_simulator.open_positions
    positions_list = []

    for symbol, position in open_positions.items():
        positions_list.append({
            "symbol": symbol,
            "side": position.side.value,
            "entry_price": position.entry_price,
            "quantity": position.quantity,
            "entry_time": position.entry_time.isoformat() if hasattr(position.entry_time, 'isoformat') else str(position.entry_time),
            "strategy": position.strategy,
            "unrealized_pnl": position.unrealized_pnl,
            "stop_loss": position.stop_loss,
            "take_profit": position.take_profit,
            "position_value": position.position_value
        })

    return {
        "positions": positions_list,
        "count": len(positions_list),
        "timestamp": datetime.now().isoformat()
    }
