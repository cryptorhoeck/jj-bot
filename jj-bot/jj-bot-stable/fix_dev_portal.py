#!/usr/bin/env python3
import os
import sys

def add_system_endpoints():
    main_py_path = "glue/api/main.py"
    backup_path = "glue/api/main.py.backup"
    
    if not os.path.exists(main_py_path):
        print(f"❌ {main_py_path} not found!")
        return False
    
    # Create backup
    print(f"📁 Creating backup: {backup_path}")
    with open(main_py_path, 'r') as f:
        content = f.read()
    
    with open(backup_path, 'w') as f:
        f.write(content)
    
    # Check if already exists
    if '/api/system/processes' in content:
        print("✅ System endpoints already exist!")
        return True
    
    # Add endpoints at the end of the file
    system_code = '''

# System monitoring endpoints added by fix script
import psutil
import subprocess
from datetime import datetime

@app.get("/api/system/processes")
async def get_system_processes():
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                pinfo['memory_mb'] = round(proc.memory_info().rss / 1024 / 1024, 2)
                processes.append(pinfo)
            except:
                pass
        return {"processes": processes[:30], "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"error": str(e), "processes": []}

@app.get("/api/system/performance") 
async def get_system_performance():
    try:
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu": {"percent": round(cpu, 2)},
            "memory": {
                "total": round(memory.total / 1024**3, 2),
                "used": round(memory.used / 1024**3, 2),
                "percent": round(memory.percent, 2)
            },
            "disk": {
                "total": round(disk.total / 1024**3, 2),
                "used": round(disk.used / 1024**3, 2),
                "percent": round((disk.used / disk.total) * 100, 2)
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/logs/live")
async def get_live_logs(lines: int = 200):
    try:
        logs = []
        log_files = ["ops/logs/glue.log", "ops/logs/api.log"]
        
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    result = subprocess.run(["tail", "-n", str(lines//2), log_file], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        for line in result.stdout.strip().split('\\n'):
                            if line.strip():
                                logs.append({
                                    "source": os.path.basename(log_file),
                                    "message": line.strip(),
                                    "timestamp": datetime.now().isoformat()
                                })
                except:
                    pass
        
        if not logs:
            logs = [{"source": "system", "message": "No logs available", "timestamp": datetime.now().isoformat()}]
            
        return {"logs": logs[:lines], "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"error": str(e), "logs": []}
'''
    
    # Append to file
    with open(main_py_path, 'a') as f:
        f.write(system_code)
    
    print("✅ System endpoints added!")
    return True

def main():
    print("🔧 Adding missing system endpoints to dev portal...")
    
    # Install psutil if needed
    try:
        import psutil
        print("✅ psutil already available")
    except ImportError:
        print("📦 Installing psutil...")
        os.system("pip install psutil")
    
    if add_system_endpoints():
        print("\n🎉 Dev portal fixed! Now restart the API:")
        print("   jj reset")
        print("\nThe missing endpoints are now available:")
        print("   • /api/system/processes")
        print("   • /api/system/performance") 
        print("   • /api/logs/live")
    
if __name__ == "__main__":
    main()
