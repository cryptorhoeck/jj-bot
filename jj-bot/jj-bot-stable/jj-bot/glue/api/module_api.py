"""
Module API Endpoints - Separate from main API
This keeps module code isolated from working system
"""

from fastapi import APIRouter
from typing import Dict, Any
import sys
import os

# Add modules path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'modules'))

# Import the polished system
from polished_system import PolishedTradingSystem

# Create router for module endpoints
router = APIRouter(prefix="/api/modules")

# Global system instance (created on first request)
trading_system = None

@router.get("/status")
async def get_module_status() -> Dict[str, Any]:
    """Get status of trading modules"""
    if trading_system and trading_system.start_time:
        return {
            "running": True,
            "uptime": str(trading_system.start_time),
            "stats": trading_system.stats
        }
    return {"running": False}

@router.get("/prices")
async def get_module_prices() -> Dict[str, Any]:
    """Get prices from module system"""
    if trading_system and trading_system.feed:
        prices = trading_system.feed.get_all_prices()
        summary = trading_system.feed.get_market_summary()
        movers = trading_system.feed.get_top_movers(5)
        
        return {
            "prices": prices,
            "summary": summary,
            "movers": movers
        }
    return {"error": "Module system not running"}

@router.get("/signals")
async def get_trading_signals() -> Dict[str, Any]:
    """Get current trading signals"""
    if trading_system and trading_system.strategy:
        return {
            "current": trading_system.strategy.get_current_signals(),
            "history": trading_system.strategy.get_signal_history(10)
        }
    return {"current": {}, "history": []}

@router.get("/portfolio")
async def get_portfolio() -> Dict[str, Any]:
    """Get portfolio status from risk manager"""
    if trading_system and trading_system.risk:
        return trading_system.risk.get_statistics()
    return {}

@router.post("/start")
async def start_modules() -> Dict[str, Any]:
    """Start the module system"""
    global trading_system
    
    try:
        if not trading_system:
            trading_system = PolishedTradingSystem()
        
        if not trading_system.start_time:
            trading_system.start()
            return {"status": "started", "message": "Module system started"}
        else:
            return {"status": "already_running", "message": "System already running"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/stop")
async def stop_modules() -> Dict[str, Any]:
    """Stop the module system"""
    global trading_system
    
    if trading_system:
        trading_system.stop()
        trading_system = None
        return {"status": "stopped", "message": "Module system stopped"}
    
    return {"status": "not_running", "message": "System was not running"}
