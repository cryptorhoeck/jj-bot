"""
JJ-Bot System Tray Application
Clean GUI control for JJ-Bot trading system
"""

import os
import sys
import subprocess
import threading
import webbrowser
from pathlib import Path
import time

try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
except ImportError:
    print("Installing required packages...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pystray", "pillow"])
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw

# Get installation directory
INSTALL_DIR = Path(__file__).parent.absolute()
VENV_PYTHON = INSTALL_DIR / "venv" / "Scripts" / "python.exe"
API_SCRIPT = INSTALL_DIR / "glue" / "api" / "main.py"
DASHBOARD_DIR = INSTALL_DIR / "dashboard" / "jj-dashboard"

class JJBotApp:
    def __init__(self):
        self.api_process = None
        self.dashboard_process = None
        self.is_running = False
        self.icon = None

    def create_image(self):
        """Create system tray icon"""
        # Create a simple green circle icon
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), 'white')
        dc = ImageDraw.Draw(image)
        dc.ellipse((8, 8, 56, 56), fill='#10b981', outline='#059669')
        # Add JJ text
        dc.text((20, 24), "JJ", fill='white')
        return image

    def start_services(self, icon=None, item=None):
        """Start API and Dashboard services"""
        if self.is_running:
            return

        try:
            # Start API (hidden)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            self.api_process = subprocess.Popen(
                [str(VENV_PYTHON), str(API_SCRIPT)],
                cwd=str(INSTALL_DIR),
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # Wait for API to start
            time.sleep(3)

            # Start Dashboard (hidden)
            self.dashboard_process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=str(DASHBOARD_DIR),
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW,
                shell=True
            )

            self.is_running = True
            if self.icon:
                self.icon.notify("JJ-Bot started successfully!", "JJ-Bot")

        except Exception as e:
            if self.icon:
                self.icon.notify(f"Error starting JJ-Bot: {e}", "JJ-Bot Error")

    def stop_services(self, icon=None, item=None):
        """Stop all services"""
        if not self.is_running:
            return

        try:
            if self.api_process:
                self.api_process.terminate()
                self.api_process = None

            if self.dashboard_process:
                self.dashboard_process.terminate()
                self.dashboard_process = None

            # Kill any remaining processes
            subprocess.run(
                ["taskkill", "/F", "/IM", "python.exe", "/FI", f"WINDOWTITLE eq *main.py*"],
                capture_output=True
            )
            subprocess.run(
                ["taskkill", "/F", "/IM", "node.exe", "/FI", "WINDOWTITLE eq *vite*"],
                capture_output=True
            )

            self.is_running = False
            if self.icon:
                self.icon.notify("JJ-Bot stopped", "JJ-Bot")

        except Exception as e:
            if self.icon:
                self.icon.notify(f"Error stopping JJ-Bot: {e}", "JJ-Bot Error")

    def restart_services(self, icon=None, item=None):
        """Restart all services"""
        self.stop_services()
        time.sleep(2)
        self.start_services()

    def open_dashboard(self, icon=None, item=None):
        """Open dashboard in browser"""
        webbrowser.open("http://localhost:5173")

    def open_api_docs(self, icon=None, item=None):
        """Open API documentation in browser"""
        webbrowser.open("http://127.0.0.1:8000/docs")

    def quit_app(self, icon=None, item=None):
        """Quit the application"""
        self.stop_services()
        if self.icon:
            self.icon.stop()

    def get_status_text(self, item):
        """Get status text for menu"""
        return "Running" if self.is_running else "Stopped"

    def run(self):
        """Run the system tray application"""
        # Create menu
        menu = pystray.Menu(
            item('JJ-Bot Trading System', lambda: None, enabled=False),
            item(lambda text: f'Status: {self.get_status_text(text)}', lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            item('Open Dashboard', self.open_dashboard),
            item('Open API Docs', self.open_api_docs),
            pystray.Menu.SEPARATOR,
            item('Start', self.start_services, enabled=lambda item: not self.is_running),
            item('Stop', self.stop_services, enabled=lambda item: self.is_running),
            item('Restart', self.restart_services, enabled=lambda item: self.is_running),
            pystray.Menu.SEPARATOR,
            item('Quit', self.quit_app)
        )

        # Create icon
        self.icon = pystray.Icon(
            "JJ-Bot",
            self.create_image(),
            "JJ-Bot Trading System",
            menu
        )

        # Auto-start services
        threading.Thread(target=self.start_services, daemon=True).start()

        # Run icon
        self.icon.run()

if __name__ == "__main__":
    app = JJBotApp()
    app.run()
