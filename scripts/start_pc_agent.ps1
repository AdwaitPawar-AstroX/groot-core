$Host.UI.RawUI.WindowTitle = "Groot - PC AGENT"
Set-Location $PSScriptRoot\..
.\venv\Scripts\activate
Write-Host "Starting PC agent (auto-reconnects if server restarts)..." -ForegroundColor Cyan
python pc_agent\agent.py
