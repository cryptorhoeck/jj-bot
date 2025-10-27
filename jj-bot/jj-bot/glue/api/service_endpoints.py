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
