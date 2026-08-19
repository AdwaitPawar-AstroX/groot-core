$Host.UI.RawUI.WindowTitle = "Groot - SERVER"
Set-Location $PSScriptRoot\..
.\venv\Scripts\activate
Write-Host "Starting Groot server on port 8420..." -ForegroundColor Cyan
uvicorn server.app:app --host 0.0.0.0 --port 8420
