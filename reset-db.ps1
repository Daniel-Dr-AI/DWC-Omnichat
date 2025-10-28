# =========================
# Reset SQLite DB (handoff.sqlite)
# =========================

$projectRoot = "$HOME\Desktop\DWC-Omnichat"
$dbPath = Join-Path $projectRoot "handoff.sqlite"

Write-Host "Resetting DB at $dbPath ..." -ForegroundColor Cyan

if (Test-Path $dbPath) {
    Remove-Item $dbPath -Force
    Write-Host "Deleted existing handoff.sqlite ✅" -ForegroundColor Yellow
} else {
    Write-Host "No existing DB found, skipping delete." -ForegroundColor DarkGray
}

# Re-run uvicorn once to trigger FastAPI startup (db_init)
Write-Host "Re-initializing DB via FastAPI startup..." -ForegroundColor Cyan
cd $projectRoot
.\.venv\Scripts\python.exe -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
