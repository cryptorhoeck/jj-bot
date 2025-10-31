"""
JJ-Bot Process Cleanup Script
Finds and kills any running JJ-Bot processes
"""

import psutil
import sys
import os

def kill_processes():
    """Find and kill all JJ-Bot related processes"""
    killed = []

    print("🔍 Searching for JJ-Bot processes...")

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if not cmdline:
                continue

            cmdline_str = ' '.join(str(arg) for arg in cmdline)

            # Check if this is a JJ-Bot process
            if any(keyword in cmdline_str for keyword in [
                'jj_bot_gui.py',
                'jj_bot_tray.py',
                'main.py',  # API server
                'sim_trader.py',
                'uvicorn'
            ]):
                # Don't kill ourselves
                if proc.pid == os.getpid():
                    continue

                print(f"   Found: PID {proc.pid} - {proc.info['name']}")
                print(f"          Command: {' '.join(cmdline[:3])}...")

                try:
                    proc.terminate()
                    killed.append(proc.pid)
                    print(f"   ✅ Killed PID {proc.pid}")
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    print(f"   ⚠️  Could not kill PID {proc.pid}: {e}")

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Also check for processes using ports 8000
    print("\n🔍 Checking for processes on port 8000...")
    for conn in psutil.net_connections():
        if conn.laddr.port == 8000 and conn.pid:
            try:
                proc = psutil.Process(conn.pid)
                if proc.pid not in killed and proc.pid != os.getpid():
                    print(f"   Found: PID {proc.pid} using port 8000")
                    proc.terminate()
                    killed.append(proc.pid)
                    print(f"   ✅ Killed PID {proc.pid}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    if killed:
        print(f"\n✅ Cleaned up {len(killed)} process(es)")
        print(f"   PIDs: {', '.join(str(pid) for pid in killed)}")
    else:
        print("\n✅ No JJ-Bot processes found running")

    return len(killed)

if __name__ == "__main__":
    print("=" * 60)
    print("JJ-Bot Process Cleanup")
    print("=" * 60)

    try:
        count = kill_processes()

        if count > 0:
            print("\n🎯 Ready to start JJ-Bot fresh!")
        else:
            print("\n🎯 All clear!")

        sys.exit(0)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
