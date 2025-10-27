"""
API Integration for Data Feed Module
This connects the module to your dashboard (optional)
"""

from fastapi import APIRouter
from typing import Dict, Any

# This will be imported by your main API if you choose to integrate
router = APIRouter(prefix="/api/modules/data")

# Module instance (created when imported)
feed_module = None

@router.get("/status")
async def get_module_status() -> Dict[str, Any]:
    """Get data feed module status"""
    if feed_module:
        return feed_module.get_status()
    return {"error": "Module not initialized"}

@router.get("/health")
async def get_module_health() -> Dict[str, Any]:
    """Get module health check"""
    if feed_module:
        return feed_module.health_check()
    return {"error": "Module not initialized"}

@router.get("/prices")
async def get_all_prices() -> Dict[str, Any]:
    """Get all current prices"""
    if feed_module:
        return feed_module.get_all_prices()
    return {"error": "Module not initialized"}

@router.get("/price/{symbol}")
async def get_price(symbol: str) -> Dict[str, Any]:
    """Get price for specific symbol"""
    if feed_module:
        price = feed_module.get_price(symbol)
        if price:
            return {"symbol": symbol, "price": price}
        return {"error": "Symbol not found"}
    return {"error": "Module not initialized"}

@router.post("/start")
async def start_module() -> Dict[str, Any]:
    """Start the data feed module"""
    global feed_module
    if not feed_module:
        from modules.data_feed import DataFeedModule
        feed_module = DataFeedModule()
    
    if feed_module.start():
        return {"status": "started"}
    return {"error": "Failed to start module"}

@router.post("/stop")
async def stop_module() -> Dict[str, Any]:
    """Stop the data feed module"""
    if feed_module:
        if feed_module.stop():
            return {"status": "stopped"}
        return {"error": "Failed to stop module"}
    return {"error": "Module not initialized"}
