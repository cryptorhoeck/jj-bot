from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
import subprocess
import requests
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
import psutil
import asyncio
from typing import Optional
import mimetypes

app = FastAPI(title="JJ-Bot Developer Portal", description="Development tools for JJ-Bot")

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuration
TRADING_API_URL = "http://127.0.0.1:8000"
PROJECT_ROOT = Path.home() / "jj-bot"
BACKUP_SCRIPT = PROJECT_ROOT / "backup_manager.sh"
ARCHIVE_DIR = Path("archive")
ARCHIVE_DIR.mkdir(exist_ok=True)

# Helper functions
def check_trading_api():
    """Check if trading API is running"""
    try:
        response = requests.get(f"{TRADING_API_URL}/health", timeout=3)
        return {"status": "running", "healthy": response.status_code == 200}
    except:
        return {"status": "stopped", "healthy": False}

def run_command(command, cwd=None):
    """Safely execute system commands"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            cwd=cwd or PROJECT_ROOT,
            timeout=30
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out", "returncode": -1}
    except Exception as e:
        return {"success": False, "error": str(e), "returncode": -1}

def get_system_stats():
    """Get system resource usage"""
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": psutil.virtual_memory()._asdict(),
        "disk": psutil.disk_usage('/')._asdict(),
        "timestamp": datetime.now().isoformat()
    }

def get_file_info(file_path):
    """Get detailed file information"""
    try:
        stat = file_path.stat()
        return {
            "name": file_path.name,
            "path": str(file_path.relative_to(PROJECT_ROOT)),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_dir": file_path.is_dir(),
            "extension": file_path.suffix.lower(),
            "mime_type": mimetypes.guess_type(str(file_path))[0] or "text/plain"
        }
    except Exception:
        return None

# Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard"""
    api_status = check_trading_api()
    system_stats = get_system_stats()
    
    # Get recent backups
    recent_backups = []
    if BACKUP_SCRIPT.exists():
        cmd_result = run_command(f"{BACKUP_SCRIPT} list")
        if cmd_result["success"]:
            recent_backups = cmd_result["output"].split('\n')[-10:]
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "api_status": api_status,
        "system_stats": system_stats,
        "recent_backups": recent_backups,
        "page": "dashboard"
    })

@app.get("/backups", response_class=HTMLResponse)
async def backups_page(request: Request):
    """Full backup management page"""
    return templates.TemplateResponse("backups.html", {
        "request": request,
        "page": "backups"
    })

@app.get("/files", response_class=HTMLResponse) 
async def files_page(request: Request, path: str = ""):
    """File browser page"""
    return templates.TemplateResponse("files.html", {
        "request": request,
        "current_path": path,
        "page": "files"
    })

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    """Real-time log viewer page"""
    return templates.TemplateResponse("logs.html", {
        "request": request,
        "page": "logs"
    })

@app.get("/tools", response_class=HTMLResponse)
async def tools_page(request: Request):
    """Development tools page"""
    return templates.TemplateResponse("tools.html", {
        "request": request,
        "page": "tools"
    })

@app.get("/archive", response_class=HTMLResponse)
async def archive_page(request: Request):
    """Archive storage page"""
    return templates.TemplateResponse("archive.html", {
        "request": request,
        "page": "archive"
    })

# API endpoints
@app.get("/api/status")
async def get_status():
    """Get system and trading API status"""
    return {
        "trading_api": check_trading_api(),
        "system": get_system_stats(),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/backup/create")
async def create_backup(reason: str = Form(...)):
    """Create a new backup"""
    if not BACKUP_SCRIPT.exists():
        raise HTTPException(status_code=404, detail="Backup script not found")
    
    result = run_command(f"{BACKUP_SCRIPT} snapshot '{reason}'")
    return {
        "success": result["success"],
        "message": result["output"] if result["success"] else result["error"]
    }

@app.get("/api/backups/list")
async def list_backups():
    """List all backups with detailed information"""
    if not BACKUP_SCRIPT.exists():
        raise HTTPException(status_code=404, detail="Backup script not found")
    
    backups = []
    snapshots_dir = PROJECT_ROOT / "backups" / "snapshots"
    
    if snapshots_dir.exists():
        for snapshot in snapshots_dir.iterdir():
            if snapshot.is_dir():
                info_file = snapshot / "SNAPSHOT_INFO.txt"
                info = {"name": snapshot.name, "path": str(snapshot)}
                
                if info_file.exists():
                    try:
                        with open(info_file) as f:
                            content = f.read()
                            lines = content.split('\n')
                            for line in lines:
                                if line.startswith('Created:'):
                                    info['created'] = line.split('Created:', 1)[1].strip()
                                elif line.startswith('Reason:'):
                                    info['reason'] = line.split('Reason:', 1)[1].strip()
                    except:
                        pass
                
                stat = snapshot.stat()
                info['size'] = sum(f.stat().st_size for f in snapshot.rglob('*') if f.is_file())
                info['modified'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                backups.append(info)
    
    return {"backups": sorted(backups, key=lambda x: x.get('modified', ''), reverse=True)}

@app.post("/api/backup/restore")
async def restore_backup(snapshot_name: str = Form(...)):
    """Restore from backup"""
    if not BACKUP_SCRIPT.exists():
        raise HTTPException(status_code=404, detail="Backup script not found")
    
    result = run_command(f"{BACKUP_SCRIPT} restore_snapshot '{snapshot_name}'")
    return {
        "success": result["success"],
        "message": result["output"] if result["success"] else result["error"]
    }

@app.post("/api/service/restart")
async def restart_trading_api():
    """Restart the trading API"""
    jj_script = PROJECT_ROOT / "jj"
    if not jj_script.exists():
        raise HTTPException(status_code=404, detail="JJ script not found")
    
    stop_result = run_command("./jj stop")
    start_result = run_command("./jj reset")
    
    return {
        "success": start_result["success"],
        "stop_output": stop_result["output"],
        "start_output": start_result["output"]
    }

@app.get("/api/files/browse")
async def browse_files(path: str = ""):
    """Browse project files"""
    try:
        target_path = PROJECT_ROOT / path if path else PROJECT_ROOT
        
        if not target_path.exists() or not target_path.is_dir():
            raise HTTPException(status_code=404, detail="Directory not found")
        
        # Get parent directory info
        parent = None
        if path and path != ".":
            parent_path = str(Path(path).parent) if Path(path).parent != Path(".") else ""
            parent = {"name": "..", "path": parent_path, "type": "parent"}
        
        files = []
        directories = []
        
        for item in sorted(target_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if item.name.startswith('.'):
                continue
            
            file_info = get_file_info(item)
            if file_info:
                if item.is_dir():
                    file_info["type"] = "directory"
                    directories.append(file_info)
                else:
                    file_info["type"] = "file"
                    files.append(file_info)
        
        return {
            "current_path": path,
            "parent": parent,
            "directories": directories,
            "files": files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/read")
async def read_file(path: str):
    """Read file content"""
    try:
        file_path = PROJECT_ROOT / path
        
        if not file_path.exists() or file_path.is_dir():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check file size (limit to 1MB for web display)
        if file_path.stat().st_size > 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large for web display")
        
        # Try to read as text
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {
                "content": content,
                "type": "text",
                "encoding": "utf-8"
            }
        except UnicodeDecodeError:
            return {
                "content": "[Binary file - cannot display]",
                "type": "binary",
                "encoding": "binary"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/files/save")
async def save_file(path: str = Form(...), content: str = Form(...)):
    """Save file content"""
    try:
        file_path = PROJECT_ROOT / path
        
        # Create backup before saving
        if file_path.exists():
            backup_result = run_command(f"{BACKUP_SCRIPT} backup '{file_path}' 'web_editor_save'")
            if not backup_result["success"]:
                raise HTTPException(status_code=500, detail="Failed to create backup")
        
        # Save file
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {"success": True, "message": "File saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs/stream")
async def stream_logs():
    """Stream real-time logs"""
    async def log_generator():
        try:
            # Get recent logs first
            result = run_command("./jj logs | tail -50")
            if result["success"]:
                for line in result["output"].split('\n'):
                    if line.strip():
                        yield f"data: {json.dumps({'line': line, 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Then follow new logs (simplified for demo)
            while True:
                await asyncio.sleep(2)
                yield f"data: {json.dumps({'line': 'Log streaming active...', 'timestamp': datetime.now().isoformat()})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(log_generator(), media_type="text/plain")

@app.get("/api/logs/recent")
async def get_recent_logs():
    """Get recent log entries"""
    try:
        result = run_command("./jj logs | tail -100")
        if result["success"]:
            lines = [line for line in result["output"].split('\n') if line.strip()]
            return {"logs": lines}
        else:
            return {"logs": ["No logs available"], "error": result["error"]}
    except Exception as e:
        return {"logs": ["Error getting logs"], "error": str(e)}

@app.get("/api/archive/list")
async def list_archive():
    """List archived files"""
    try:
        files = []
        for item in ARCHIVE_DIR.iterdir():
            if item.is_file():
                stat = item.stat()
                files.append({
                    "name": item.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": item.suffix.lower()
                })
        
        return {"files": sorted(files, key=lambda x: x["modified"], reverse=True)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/archive/upload")
async def upload_to_archive(file: UploadFile = File(...)):
    """Upload file to archive"""
    try:
        # Save uploaded file
        file_path = ARCHIVE_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {"success": True, "message": f"File {file.filename} uploaded to archive"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/archive/download/{filename}")
async def download_from_archive(filename: str):
    """Download file from archive"""
    file_path = ARCHIVE_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found in archive")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

@app.delete("/api/archive/delete/{filename}")
async def delete_from_archive(filename: str):
    """Delete file from archive"""
    try:
        file_path = ARCHIVE_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found in archive")
        
        file_path.unlink()
        return {"success": True, "message": f"File {filename} deleted from archive"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
#!/usr/bin/env python3
"""
JJ-Bot Developer Portal - Complete Phase 2 Implementation
Isolated development tools on port 8001
"""

import os
import json
import shutil
import sqlite3
import subprocess
import psutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import aiofiles
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="JJ-Bot Developer Portal")

# Setup templates and static files
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# === PHASE 1 ROUTES (EXISTING) ===

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main dashboard"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/backups", response_class=HTMLResponse)
async def backups_page(request: Request):
    """Backup management page"""
    return templates.TemplateResponse("backups.html", {"request": request})

@app.get("/files", response_class=HTMLResponse)
async def files_page(request: Request):
    """File browser page"""
    return templates.TemplateResponse("files.html", {"request": request})

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    """Log viewer page"""
    return templates.TemplateResponse("logs.html", {"request": request})

@app.get("/tools", response_class=HTMLResponse)
async def tools_page(request: Request):
    """Development tools page"""
    return templates.TemplateResponse("tools.html", {"request": request})

@app.get("/api/status")
async def get_status():
    """Get system and API status"""
    try:
        # Check if trading API is running
        api_running = False
        api_healthy = False
        
        try:
            # Check if process is running
            result = subprocess.run(
                "pgrep -f 'uvicorn glue.api.main:app'",
                shell=True,
                capture_output=True
            )
            api_running = result.returncode == 0
            
            # Check health endpoint
            if api_running:
                import requests
                try:
                    response = requests.get("http://127.0.0.1:8000/health", timeout=3)
                    api_healthy = response.status_code == 200
                except:
                    api_healthy = False
        except Exception as e:
            logger.error(f"Error checking API status: {e}")
        
        # Get system stats
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "trading_api": {
                "status": "running" if api_running else "stopped",
                "healthy": api_healthy
            },
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                },
                "timestamp": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in get_status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backup/create")
async def create_backup():
    """Create a new backup of the trading system"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = Path(os.path.expanduser(f"~/jj-bot/backups/backup_{timestamp}"))
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Define what to backup
        items_to_backup = [
            "glue/api",
            "dashboard/jj-dashboard/src",
            "config.json",
            "jj",
            "requirements.txt"
        ]
        
        base_path = Path(os.path.expanduser("~/jj-bot"))
        
        for item in items_to_backup:
            source = base_path / item
            if source.exists():
                dest = backup_dir / item
                if source.is_dir():
                    shutil.copytree(source, dest)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
        
        return {
            "message": "Backup created successfully",
            "location": str(backup_dir),
            "timestamp": timestamp
        }
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/service/restart")
async def restart_service(service: str = "api"):
    """Restart a service"""
    try:
        if service == "api":
            # Stop the API
            subprocess.run("pkill -f 'uvicorn glue.api.main:app'", shell=True)
            await asyncio.sleep(1)
            
            # Start the API
            subprocess.Popen(
                "cd ~/jj-bot && source .venv/bin/activate && nohup uvicorn glue.api.main:app --host 0.0.0.0 --port 8000 > logs/glue.log 2>&1 &",
                shell=True
            )
            await asyncio.sleep(2)
            
            return {"message": "API restarted successfully"}
        else:
            raise ValueError(f"Unknown service: {service}")
    except Exception as e:
        logger.error(f"Error restarting service: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === PHASE 2 ROUTES (NEW) ===

# File Browser Module
@app.get("/api/files/browse")
async def browse_files(path: str = ""):
    """Browse project files with safety checks"""
    try:
        base_path = Path(os.path.expanduser("~/jj-bot"))
        target_path = base_path / path if path else base_path
        
        # Security: Prevent directory traversal
        if not str(target_path.resolve()).startswith(str(base_path.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Path not found")
        
        items = []
        for item in target_path.iterdir():
            # Skip hidden files and __pycache__
            if item.name.startswith('.') or item.name == '__pycache__':
                continue
                
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else 0,
                "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                "path": str(item.relative_to(base_path))
            })
        
        return {
            "current_path": path,
            "items": sorted(items, key=lambda x: (x["type"] != "directory", x["name"]))
        }
    except Exception as e:
        logger.error(f"Error browsing files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/content")
async def get_file_content(path: str):
    """Get content of a text file"""
    try:
        base_path = Path(os.path.expanduser("~/jj-bot"))
        file_path = base_path / path
        
        # Security check
        if not str(file_path.resolve()).startswith(str(base_path.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check if file is text
        text_extensions = {'.py', '.js', '.jsx', '.json', '.txt', '.md', '.html', '.css', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.conf', '.sh', '.bash'}
        
        if file_path.suffix.lower() in text_extensions:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
            return {"content": content, "type": "text"}
        else:
            return {"content": None, "type": "binary", "message": "Binary file - use download"}
            
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/download")
async def download_file(path: str):
    """Download a file from the project"""
    try:
        base_path = Path(os.path.expanduser("~/jj-bot"))
        file_path = base_path / path
        
        # Security check
        if not str(file_path.resolve()).startswith(str(base_path.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            media_type="application/octet-stream"
        )
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...), path: str = Form("")):
    """Upload a file to the archive directory"""
    try:
        archive_dir = Path(os.path.expanduser("~/jj-bot/dev-portal/archive"))
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped subdirectory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        upload_dir = archive_dir / timestamp
        upload_dir.mkdir(exist_ok=True)
        
        file_path = upload_dir / file.filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        return {
            "message": "File uploaded successfully",
            "path": str(file_path.relative_to(Path(os.path.expanduser("~/jj-bot")))),
            "size": len(content)
        }
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Real-time Log Viewer
@app.get("/api/logs/stream")
async def stream_logs(file: str = "glue.log", lines: int = 100):
    """Stream log file contents"""
    try:
        log_path = Path(os.path.expanduser(f"~/jj-bot/logs/{file}"))
        
        if not log_path.exists():
            return {"lines": [], "message": "Log file not found"}
        
        # Read last N lines
        async with aiofiles.open(log_path, 'r') as f:
            content = await f.read()
            all_lines = content.splitlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return {
            "file": file,
            "lines": recent_lines,
            "total_lines": len(all_lines)
        }
    except Exception as e:
        logger.error(f"Error streaming logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for real-time log streaming"""
    await websocket.accept()
    log_path = Path(os.path.expanduser("~/jj-bot/logs/glue.log"))
    
    try:
        # Check if file exists
        if not log_path.exists():
            await websocket.send_text("Log file not found")
            await websocket.close()
            return
            
        # Use tail -f equivalent
        process = await asyncio.create_subprocess_exec(
            'tail', '-f', str(log_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        while True:
            line = await process.stdout.readline()
            if line:
                await websocket.send_text(line.decode('utf-8'))
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        if 'process' in locals():
            process.terminate()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

# Configuration Editor
@app.get("/api/config/get")
async def get_config():
    """Get current configuration"""
    try:
        config_path = Path(os.path.expanduser("~/jj-bot/config.json"))
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            # Default config
            config = {
                "MAX_POSITION_SIZE": 0,
                "MAX_DAILY_LOSS": 1000.0,
                "MAX_TRADES_PER_DAY": 20,
                "COOLDOWN_SECONDS": 60,
                "CIRCUIT_BREAKER_DROP": 0.10,
                "SYMBOLS": ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
            }
        
        return config
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/save")
async def save_config(config: Dict):
    """Save configuration with validation"""
    try:
        config_path = Path(os.path.expanduser("~/jj-bot/config.json"))
        
        # Backup current config
        if config_path.exists():
            backup_path = config_path.with_suffix(f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            shutil.copy2(config_path, backup_path)
        
        # Validate config
        required_keys = ["MAX_POSITION_SIZE", "MAX_DAILY_LOSS", "MAX_TRADES_PER_DAY"]
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required config key: {key}")
        
        # Save new config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return {"message": "Configuration saved successfully", "backup": str(backup_path.name) if 'backup_path' in locals() else None}
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Database Inspector
@app.get("/api/database/tables")
async def get_database_tables():
    """List all tables in the database"""
    try:
        db_path = Path(os.path.expanduser("~/jj-bot/jj_trades.db"))
        
        if not db_path.exists():
            return {"tables": [], "message": "Database not found"}
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return {"tables": tables}
    except Exception as e:
        logger.error(f"Error getting database tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/database/query")
async def query_database(sql: str = None, table: str = "trades", limit: int = 100):
    """Execute a read-only query on the database"""
    try:
        db_path = Path(os.path.expanduser("~/jj-bot/jj_trades.db"))
        
        if not db_path.exists():
            return {"error": "Database not found"}
        
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row  # Enable column names
        cursor = conn.cursor()
        
        # Default query if none provided
        if not sql:
            sql = f"SELECT * FROM {table} ORDER BY id DESC LIMIT {limit}"
        
        # Safety: Only allow SELECT statements
        if not sql.strip().upper().startswith("SELECT"):
            raise HTTPException(status_code=403, detail="Only SELECT queries allowed")
        
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        # Convert to list of dicts
        result = [dict(row) for row in rows]
        
        conn.close()
        return {
            "query": sql,
            "rows": result,
            "count": len(result)
        }
    except Exception as e:
        logger.error(f"Error querying database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Process Monitor
@app.get("/api/processes")
async def get_processes():
    """Get status of all JJ-Bot related processes"""
    try:
        processes = []
        
        # Check for running processes
        checks = [
            ("Trading API", "uvicorn glue.api.main:app"),
            ("Trade Simulator", "sim_trader.py"),
            ("Dev Portal", "uvicorn app:app --port 8001"),
        ]
        
        for name, pattern in checks:
            try:
                result = subprocess.run(
                    f"pgrep -af '{pattern}'",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    pids = result.stdout.strip().split('\n')
                    processes.append({
                        "name": name,
                        "status": "running",
                        "pids": [line.split()[0] for line in pids if line],
                        "pattern": pattern
                    })
                else:
                    processes.append({
                        "name": name,
                        "status": "stopped",
                        "pids": [],
                        "pattern": pattern
                    })
            except Exception:
                processes.append({
                    "name": name,
                    "status": "unknown",
                    "pids": [],
                    "pattern": pattern
                })
        
        return {"processes": processes}
    except Exception as e:
        logger.error(f"Error getting processes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
