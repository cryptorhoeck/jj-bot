# PowerShell script to forcefully close JJ-Bot terminal windows
# More aggressive approach with verbose output

Write-Host "=== Closing JJ-Bot Terminal Windows ===" -ForegroundColor Cyan

# Method 1: Find cmd.exe processes by MainWindowTitle
Write-Host "`n[Method 1] Searching for cmd.exe windows with JJ-Bot titles..." -ForegroundColor Yellow

$cmdProcesses = Get-Process cmd -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -ne "" }
$found = 0
$killed = 0

foreach ($proc in $cmdProcesses) {
    $title = $proc.MainWindowTitle
    Write-Host "  Found window: '$title' (PID: $($proc.Id))"

    if ($title -like "*JJ-Bot*") {
        Write-Host "    -> Killing PID $($proc.Id)..." -ForegroundColor Green
        try {
            Stop-Process -Id $proc.Id -Force -ErrorAction Stop
            $killed++
            $found++
        } catch {
            Write-Host "    -> Failed: $_" -ForegroundColor Red
        }
    }
}

Write-Host "`n[Method 1] Found $found JJ-Bot windows, killed $killed" -ForegroundColor Yellow

# Method 2: Use WMI to find cmd.exe with specific command lines
Write-Host "`n[Method 2] Searching for cmd.exe by command line..." -ForegroundColor Yellow

$wmiProcesses = Get-WmiObject Win32_Process -Filter "name='cmd.exe'" -ErrorAction SilentlyContinue
$found2 = 0
$killed2 = 0

foreach ($proc in $wmiProcesses) {
    $cmdLine = $proc.CommandLine
    if ($cmdLine -like "*JJ-Bot*") {
        Write-Host "  Found: PID $($proc.ProcessId)"
        Write-Host "    Command: $cmdLine"
        try {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
            Write-Host "    -> Killed" -ForegroundColor Green
            $killed2++
            $found2++
        } catch {
            Write-Host "    -> Failed: $_" -ForegroundColor Red
        }
    }
}

Write-Host "`n[Method 2] Found $found2 processes, killed $killed2" -ForegroundColor Yellow

# Summary
$totalKilled = $killed + $killed2
if ($totalKilled -eq 0) {
    Write-Host "`n[RESULT] No JJ-Bot windows found or all already closed" -ForegroundColor Gray
} else {
    Write-Host "`n[RESULT] Successfully closed $totalKilled window(s)" -ForegroundColor Green
}

Write-Host "=== Done ===" -ForegroundColor Cyan

exit 0
