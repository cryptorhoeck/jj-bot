import os, json, math, asyncio, datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import sqlite3
from pathlib import Path

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app with enterprise features
app = FastAPI(
    title="JJ Gorilla Professional Trading Platform",
    description="Enterprise-grade algorithmic trading platform with multi-strategy analysis",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security
security = HTTPBearer(auto_error=False)

# Import our modules
from . import engine

# Import enterprise modules
import sys
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from ops.security.auth_manager import auth_manager
from ops.optimization.performance_manager import performance_manager
from ops.automation.backup_scheduler import backup_scheduler

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    engine.init_db()
    
    # Optimize database on startup
    optimization_result = performance_manager.optimize_database()
    print(f"🗄️ Database optimized: {len(optimization_result.get('operations', []))} operations")
    
    # Start backup scheduler
    try:
        backup_scheduler.start_scheduler()
        print("📅 Enterprise backup scheduler started")
    except Exception as e:
        print(f"⚠️ Backup scheduler error: {e}")
    
    # Start performance monitoring
    asyncio.create_task(performance_manager.run_performance_monitor())
    print("📊 Performance monitoring started")
    
    print("🦍 JJ Gorilla Enterprise Platform started successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    # Stop scheduler
    backup_scheduler.stop_scheduler()
    print("📅 Enterprise backup scheduler stopped")

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    if credentials is None:
        return None  # Allow anonymous access to public endpoints
    
    # Try JWT token first
    token_payload = auth_manager.verify_token(credentials.credentials)
    if token_payload:
        username = token_payload.get("sub")
        user = auth_manager.users_db.get(username)
        if user and user.get("active", True):
            return {"type": "user", "data": user}
    
    # Try API key
    api_key_data = auth_manager.verify_api_key(credentials.credentials)
    if api_key_data:
        return {"type": "api_key", "data": api_key_data}
    
    return None

# Permission checking dependency
def require_permission(permission: str):
    """Require specific permission"""
    async def permission_check(current_user: Optional[Dict] = Depends(get_current_user)):
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        if not auth_manager.has_permission(current_user["data"], permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        
        return current_user
    
    return permission_check

# Admin permission dependency
require_admin = require_permission("admin")
require_read = require_permission("read")
require_write = require_permission("write")

# Helper functions
def safe_float(x):
    try:
        f = float(x)
        if math.isfinite(f):
            return f
        return None
    except Exception:
        return None

def safe_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in rec.items():
        if isinstance(v, float):
            out[k] = safe_float(v)
        elif isinstance(v, dict):
            out[k] = safe_record(v)
        else:
            out[k] = v
    return out

# ---- AUTHENTICATION ENDPOINTS ----
@app.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: Dict[str, str]):
    """User login"""
    username = credentials.get("username")
    password = credentials.get("password")
    
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password required"
        )
    
    user = auth_manager.authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Create access token
    access_token = auth_manager.create_access_token(data={"sub": username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "permissions": user["permissions"]
        }
    }

@app.post("/auth/api-key")
async def create_api_key(request: Request, key_data: Dict[str, Any], _: Dict = Depends(require_admin)):
    """Create API key (admin only)"""
    name = key_data.get("name")
    permissions = key_data.get("permissions", ["read"])
    expires_in_days = key_data.get("expires_in_days", 365)
    
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key name required"
        )
    
    result = auth_manager.create_api_key(name, permissions, expires_in_days)
    return result

# ---- ENTERPRISE ENDPOINTS ----

# Enhanced system status with authentication
@app.get("/api/system/enterprise-status")
async def get_enterprise_status(_: Dict = Depends(require_read)):
    """Get comprehensive enterprise system status"""
    try:
        # Get all subsystem status
        backup_stats = performance_manager.cache.get("backup_stats") or {}
        scheduler_status = backup_scheduler.get_job_status()
        performance_summary = performance_manager.get_performance_summary(24)
        security_stats = auth_manager.get_security_stats()
        
        # Cloud status
        from ops.cloud.cloud_backup_manager import cloud_backup_manager
        cloud_stats = cloud_backup_manager.get_cloud_stats()
        
        return safe_record({
            "timestamp": datetime.datetime.now().isoformat(),
            "version": "2.0.0-enterprise",
            "status": "operational",
            "subsystems": {
                "backup_scheduler": {
                    "running": scheduler_status["scheduler_running"],
                    "jobs": scheduler_status["total_jobs"]
                },
                "performance_monitor": {
                    "enabled": True,
                    "metrics_collected": len(performance_manager.performance_metrics)
                },
                "security": security_stats,
                "cloud_backup": cloud_stats,
                "cache": {
                    "entries": len(performance_manager.cache),
                    "hit_rate": performance_manager._calculate_cache_hit_rate()
                }
            },
            "performance": performance_summary
        })
        
    except Exception as e:
        return {"error": str(e)}

# Enhanced backup endpoints with cloud integration
@app.post("/api/enterprise/backup/create")
async def create_enterprise_backup(
    backup_data: Dict[str, Any], 
    _: Dict = Depends(require_permission("backup"))
):
    """Create enterprise backup with cloud sync"""
    try:
        from ops.backup.enterprise_backup_manager import backup_manager
        from ops.cloud.cloud_backup_manager import cloud_backup_manager
        
        backup_type = backup_data.get('type', 'full')
        description = backup_data.get('description', 'Enterprise backup')
        sync_to_cloud = backup_data.get('sync_to_cloud', False)
        
        # Create local backup
        result = backup_manager.create_backup(backup_type, description)
        
        # Upload to cloud if requested and configured
        if sync_to_cloud and cloud_backup_manager.config["enabled"]:
            backup_path = backup_manager.backup_root / result["name"]
            if backup_path.exists():
                cloud_result = cloud_backup_manager.upload_backup_to_cloud(backup_path, result)
                result["cloud_backup"] = cloud_result
        
        return {"success": True, "backup": safe_record(result)}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# Performance optimization endpoints
@app.post("/api/enterprise/optimize/database")
async def optimize_database(_: Dict = Depends(require_admin)):
    """Optimize database performance"""
    try:
        result = performance_manager.optimize_database()
        return {"success": True, "optimization": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/enterprise/optimize/cache/clear")
async def clear_cache(pattern: str = None, _: Dict = Depends(require_admin)):
    """Clear performance cache"""
    try:
        cleared = performance_manager.clear_cache(pattern)
        return {"success": True, "cleared_entries": cleared}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Cloud backup endpoints
@app.get("/api/enterprise/cloud/backups")
async def list_cloud_backups(_: Dict = Depends(require_read)):
    """List cloud backups"""
    try:
        from ops.cloud.cloud_backup_manager import cloud_backup_manager
        backups = cloud_backup_manager.list_cloud_backups()
        return {"success": True, "backups": backups}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/enterprise/cloud/cleanup")
async def cleanup_cloud_backups(
    cleanup_data: Dict[str, Any] = None,
    _: Dict = Depends(require_admin)
):
    """Clean up old cloud backups"""
    try:
        from ops.cloud.cloud_backup_manager import cloud_backup_manager
        retention_days = cleanup_data.get("retention_days") if cleanup_data else None
        result = cloud_backup_manager.cleanup_old_cloud_backups(retention_days)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

# Scheduler management endpoints
@app.get("/api/enterprise/scheduler/status")
async def get_scheduler_status(_: Dict = Depends(require_read)):
    """Get backup scheduler status"""
    try:
        status = backup_scheduler.get_job_status()
        return {"success": True, "scheduler": status}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/enterprise/scheduler/start")
async def start_scheduler(_: Dict = Depends(require_admin)):
    """Start backup scheduler"""
    try:
        backup_scheduler.start_scheduler()
        return {"success": True, "message": "Scheduler started"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/enterprise/scheduler/stop")
async def stop_scheduler(_: Dict = Depends(require_admin)):
    """Stop backup scheduler"""
    try:
        backup_scheduler.stop_scheduler()
        return {"success": True, "message": "Scheduler stopped"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ---- EXISTING ENDPOINTS WITH CACHING ----

@app.get("/api/trades/summary")
@limiter.limit("30/minute")
async def trades_summary(request: Request, _: Dict = Depends(require_read)):
    """Get trades summary with caching"""
    cached = performance_manager.get_cached("trades_summary")
    if cached:
        return cached
    
    result = safe_record(engine.get_summary())
    performance_manager.set_cached("trades_summary", result, 60)  # Cache for 1 minute
    return result

@app.get("/api/trades/log")
@limiter.limit("60/minute")
async def get_trades_log(request: Request, _: Dict = Depends(require_read)):
    """Get trades log with caching"""
    cached = performance_manager.get_cached("trades_log")
    if cached:
        return cached
    
    trades = engine.get_trades()
    result = [safe_record(trade) for trade in trades]
    performance_manager.set_cached("trades_log", result, 30)  # Cache for 30 seconds
    return result

# Dashboard static files
dashboard_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "dashboard", "jj-dashboard", "dist")
if os.path.exists(dashboard_path):
    app.mount("/dashboard", StaticFiles(directory=dashboard_path, html=True), name="dashboard")

@app.get("/")
def root():
    return RedirectResponse(url="/dashboard/")

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat(), "version": "2.0.0-enterprise"}

# Keep all existing endpoints but add authentication and caching where appropriate
# [Previous endpoints would be included here with appropriate auth decorators]
