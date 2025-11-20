# PowerShell script to close JJ-Bot terminal windows
# Finds and closes cmd.exe windows by title

Write-Host "Searching for JJ-Bot windows to close..."

# Get all cmd.exe processes with window titles
$processes = Get-Process cmd -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -ne "" }

$closed = 0

foreach ($proc in $processes) {
    $title = $proc.MainWindowTitle

    # Check if title contains JJ-Bot
    if ($title -like "*JJ-Bot*") {
        Write-Host "  Closing: $title (PID: $($proc.Id))"
        try {
            Stop-Process -Id $proc.Id -Force -ErrorAction Stop
            $closed++
        } catch {
            Write-Host "    Failed to close PID $($proc.Id): $_"
        }
    }
}

if ($closed -eq 0) {
    Write-Host "  No JJ-Bot windows found"
} else {
    Write-Host "  Closed $closed window(s)"
}

exit 0
