@echo off
REM JJ-Bot Pro - Stop all services

REM Kill Python API processes
taskkill /F /IM pythonw.exe 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *main.py*" 2>nul

REM Kill Node.js dashboard processes
taskkill /F /IM node.exe /FI "WINDOWTITLE eq *jj-dashboard*" 2>nul

echo JJ-Bot stopped
