Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Social Metrics Report Generator" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Start backend
Write-Host "[1/2] Starting Python backend..." -ForegroundColor Yellow
$BackendJob = Start-Job -ScriptBlock {
    Set-Location -LiteralPath $using:RootDir\backend
    python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
}

Start-Sleep -Seconds 3

# Check backend
$BackendCheck = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -ErrorAction SilentlyContinue
if ($BackendCheck.status -eq "ok") {
    Write-Host "  ✓ Backend running on http://127.0.0.1:8000" -ForegroundColor Green
} else {
    Write-Host "  ✗ Backend failed to start" -ForegroundColor Red
}

# Start frontend
Write-Host "[2/2] Starting Next.js frontend..." -ForegroundColor Yellow
$FrontendJob = Start-Job -ScriptBlock {
    Set-Location -LiteralPath $using:RootDir\frontend
    npm run dev
}

Start-Sleep -Seconds 8

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Application ready!" -ForegroundColor Green
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "  Backend:  http://127.0.0.1:8000" -ForegroundColor White
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Yellow

try {
    # Keep script running
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
finally {
    Write-Host "Stopping services..." -ForegroundColor Yellow
    Stop-Job $BackendJob -ErrorAction SilentlyContinue
    Stop-Job $FrontendJob -ErrorAction SilentlyContinue
    Remove-Job $BackendJob -ErrorAction SilentlyContinue
    Remove-Job $FrontendJob -ErrorAction SilentlyContinue
    Write-Host "Done." -ForegroundColor Green
}
