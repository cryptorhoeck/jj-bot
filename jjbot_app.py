"""
JJ-Bot Desktop Application
Launches JJ-Bot in a native desktop window (no browser)

This is the main launcher - starts all services and opens the app.
"""

import webview
import subprocess
import sys
import os
import time
import threading
import requests
from pathlib import Path

# Configuration
API_URL = "http://127.0.0.1:8000"
DASHBOARD_URL = "http://localhost:5173"
PROJECT_ROOT = Path(__file__).parent

# Process handles
api_process = None
dashboard_process = None


def wait_for_server(url, timeout=30):
    """Wait for a server to become available"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code < 500:
                return True
        except:
            pass
        time.sleep(0.5)
    return False


def build_dashboard():
    """Build the React dashboard"""
    dashboard_dir = PROJECT_ROOT / "dashboard" / "jj-dashboard"
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

    print("Building dashboard...")
    result = subprocess.run(
        [npm_cmd, "run", "build"],
        cwd=str(dashboard_dir),
        capture_output=True,
        shell=True
    )

    if result.returncode == 0:
        print("Dashboard built successfully!")
        return True
    else:
        print("Dashboard build failed, continuing with existing build...")
        return True  # Continue anyway, might have existing build


def start_api_server():
    """Start the FastAPI backend"""
    global api_process

    venv_python = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = PROJECT_ROOT / "venv" / "bin" / "python"

    api_dir = PROJECT_ROOT / "glue" / "api"

    api_process = subprocess.Popen(
        [str(venv_python), "main.py"],
        cwd=str(api_dir),
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    print("Starting API server...")
    if wait_for_server(f"{API_URL}/api/summary"):
        print("API server ready!")
        return True
    else:
        print("API server failed to start")
        return False


def start_dashboard():
    """Start the React dashboard dev server"""
    global dashboard_process

    dashboard_dir = PROJECT_ROOT / "dashboard" / "jj-dashboard"

    # Use npm to start dev server
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

    dashboard_process = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(dashboard_dir),
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=True
    )

    print("Starting dashboard...")
    if wait_for_server(DASHBOARD_URL):
        print("Dashboard ready!")
        return True
    else:
        print("Dashboard failed to start")
        return False


def cleanup():
    """Clean up processes on exit"""
    global api_process, dashboard_process

    print("Shutting down...")

    if dashboard_process:
        dashboard_process.terminate()
        try:
            dashboard_process.wait(timeout=5)
        except:
            dashboard_process.kill()

    if api_process:
        api_process.terminate()
        try:
            api_process.wait(timeout=5)
        except:
            api_process.kill()

    # Also clean up any orphaned processes on Windows
    if sys.platform == "win32":
        os.system("taskkill /F /IM node.exe >nul 2>&1")


def on_closing():
    """Called when window is closed"""
    cleanup()
    return True


def main():
    """Main entry point"""
    print("=" * 50)
    print("JJ-Bot Desktop Application")
    print("=" * 50)

    # Build dashboard first (like start_all.bat does)
    build_dashboard()

    # Start services in background
    if not start_api_server():
        print("Failed to start API server!")
        return

    if not start_dashboard():
        print("Failed to start dashboard!")
        cleanup()
        return

    print("\nLaunching JJ-Bot window...")

    # Create native window
    window = webview.create_window(
        title="JJ-Bot Trading System",
        url=DASHBOARD_URL,
        width=1400,
        height=900,
        resizable=True,
        min_size=(800, 600),
        confirm_close=False,
    )

    # Set up cleanup on close
    window.events.closing += on_closing

    # Start the GUI (blocks until window is closed)
    webview.start()

    # Cleanup after window closes
    cleanup()
    print("JJ-Bot closed.")


if __name__ == "__main__":
    main()
