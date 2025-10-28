# ==================================
# DWC Omnichat – Universal Launcher
# ==================================

param(
    [string]$Action = "run"
)

# Project root
$projectRoot = "$HOME\Desktop\DWC-Omnichat"

# Change to project folder
Set-Location $projectRoot

switch ($Action.ToLower()) {
    "reset" {
        Write-Host "Resetting DB and restarting server..." -ForegroundColor Cyan
        .\reset-db.ps1
    }
    "run" {
        Write-Host "Restarting server..." -ForegroundColor Cyan
        .\restart-server.ps1
    }
    default {
        Write-Host "Unknown action: $Action" -ForegroundColor Red
        Write-Host "Usage: dwc [run|reset]" -ForegroundColor Yellow
    }
}
