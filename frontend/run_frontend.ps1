$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ScriptDir
Write-Host "Starting Social Metrics Frontend..." -ForegroundColor Green
Write-Host "URL: http://localhost:3000" -ForegroundColor Cyan
npm run dev
