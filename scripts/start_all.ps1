# Starts all three Groot components in separate, clearly-titled windows,
# in the right order with enough delay for each to be ready before the
# next one needs it.
#
# Run this from the groot_v2 folder: .\scripts\start_all.ps1

$root = $PSScriptRoot

Write-Host "Starting Groot SERVER..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-File", "$root\start_server.ps1"
Start-Sleep -Seconds 4   # give the server a moment to bind the port

Write-Host "Starting Groot PC AGENT..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-File", "$root\start_pc_agent.ps1"
Start-Sleep -Seconds 2

Write-Host "Starting Groot VOICE CLIENT..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-File", "$root\start_voice_client.ps1"

Write-Host "`nAll three windows launched. Check each for its own status." -ForegroundColor Yellow
