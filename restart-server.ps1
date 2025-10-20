# =========================
# Restart FastAPI (uvicorn)
# =========================

$projectRoot = "$HOME\Desktop\DWC-Omnichat"

Write-Host "Restarting FastAPI server..." -ForegroundColor Cyan

cd $projectRoot

# Kill any uvicorn processes if running
Get-Process -Name "python" -ErrorAction SilentlyContinue | `
    Where-Object { $_.Path -like "*uvicorn*" -or $_.Path -like "*python*" } | `
    Stop-Process -Force

Start-Sleep -Seconds 2

# Start fresh uvicorn
.\.venv\Scripts\python.exe -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
