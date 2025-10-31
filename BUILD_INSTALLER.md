# Building JJ-Bot Windows Installer

This guide explains how to create the professional MSI installer for JJ-Bot.

## 🎯 What You Get

A professional Windows installer that:
- ✅ Double-click to install (like any other software)
- ✅ System tray icon for control
- ✅ No console windows
- ✅ Auto-start with Windows
- ✅ Open Dashboard and API from system tray
- ✅ Clean uninstaller

---

## 📋 Prerequisites

### 1. Install Inno Setup (FREE)
Download and install from: https://jrsoftware.org/isdl.php

**OR** use the download link:
```
https://jrsoftware.org/download.php/is.exe
```

### 2. Make sure you have:
- Python 3.8+ installed
- Node.js 16+ installed
- Git installed

---

## 🛠️ Building the Installer

### Option 1: Using Inno Setup GUI (Easiest)

1. **Open Inno Setup Compiler**
2. **File → Open** → Select `installer.iss` from your jj-bot folder
3. **Build → Compile** (or press F9)
4. **Done!** Installer will be in `installer_output/JJ-Bot-Setup.exe`

### Option 2: Command Line

```cmd
cd "E:\JJ Gorilla\jj-bot"
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

---

## 📦 Using the Installer

### Installation

1. Double-click `JJ-Bot-Setup.exe`
2. Follow the installation wizard
3. Choose install location (default: `C:\Program Files\JJ-Bot`)
4. Select options:
   - ✅ Create desktop shortcut
   - ✅ Start with Windows (recommended)
5. Click "Install"
6. JJ-Bot will auto-start in your system tray!

### First Run

After installation, you'll see:
- **System Tray Icon** (green circle with "JJ") in your taskbar
- Right-click the icon to see menu:
  - Open Dashboard
  - Open API Docs
  - Start/Stop/Restart
  - Quit

### Daily Use

1. **JJ-Bot starts automatically** when Windows starts
2. **Right-click the tray icon** to:
   - Open Dashboard → Opens http://localhost:5173 in your browser
   - Open API Docs → Opens http://127.0.0.1:8000/docs
   - Stop → Stops all services
   - Restart → Restarts services

### Uninstallation

- Go to **Windows Settings → Apps**
- Find **JJ-Bot Trading System**
- Click **Uninstall**

---

## 🎨 Customization (Optional)

### Change the Icon

1. Create a 256x256 PNG icon
2. Convert to ICO format using: https://convertio.co/png-ico/
3. Save as `icon.ico` in the jj-bot folder
4. Rebuild the installer

### Change App Name

Edit `installer.iss`:
```iss
#define AppName "Your Custom Name"
```

---

## 🐛 Troubleshooting

### "Python not found" during installation

**Solution**: Install Python from https://python.org
- Make sure to check "Add Python to PATH" during installation

### "Node.js not found" during installation

**Solution**: Install Node.js from https://nodejs.org

### System tray icon doesn't appear

**Solution**:
1. Open Task Manager
2. End any `python.exe` or `pythonw.exe` processes
3. Run the installer again

### Services won't start

**Solution**:
1. Right-click tray icon → Quit
2. Check Windows Firewall isn't blocking Python or Node
3. Relaunch from Start Menu

---

## 📁 Installer Output

After building, you'll find:
```
installer_output/
└── JJ-Bot-Setup.exe  ← This is your installer!
```

**File size**: ~50MB (includes all dependencies)

---

## 🚀 Distribution

You can now:
- Share `JJ-Bot-Setup.exe` with others
- Upload to GitHub Releases
- Distribute via email or USB drive

**Users only need to**:
1. Have Python and Node.js installed
2. Double-click the installer
3. Done!

---

## 📊 What Gets Installed

```
C:\Program Files\JJ-Bot\
├── jj_bot_tray.py          ← System tray application
├── venv\                   ← Python virtual environment
├── glue\                   ← API server
├── modules\                ← Trading modules
├── services\               ← Background services
├── dashboard\              ← React dashboard
├── data\                   ← Trade data
├── logs\                   ← Log files
└── backups\                ← Database backups
```

---

## ✨ Features

### System Tray Menu

```
┌─────────────────────────────┐
│ JJ-Bot Trading System       │
│ Status: Running             │
├─────────────────────────────┤
│ Open Dashboard              │
│ Open API Docs               │
├─────────────────────────────┤
│ Start                       │
│ Stop                        │
│ Restart                     │
├─────────────────────────────┤
│ Quit                        │
└─────────────────────────────┘
```

### Auto-Start

- Added to Windows Startup folder
- Starts silently in background
- No console windows

### Clean Uninstall

- Removes all files
- Removes registry entries
- Removes startup entries
- Stops all services

---

## 🎯 Next Steps

After installation, users can:
1. Click the system tray icon
2. Select "Open Dashboard"
3. Start trading!

No terminal commands needed! 🎉
