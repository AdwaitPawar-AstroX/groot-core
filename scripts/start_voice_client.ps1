$Host.UI.RawUI.WindowTitle = "Groot - VOICE"
Set-Location $PSScriptRoot\..
.\venv\Scripts\activate
Write-Host "Starting voice client. Say the wake word to talk to Groot." -ForegroundColor Cyan
python -m voice_client.main
