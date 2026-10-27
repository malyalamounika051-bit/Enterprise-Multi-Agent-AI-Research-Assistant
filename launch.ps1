# ==============================================================================
# Asterline AI Research Assistant — PowerShell Single-Command Launcher
# ==============================================================================

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "        Starting Asterline AI Research Assistant (Backend + Frontend)         " -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan

$RootPath = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Verify venv
$VenvPython = Join-Path $RootPath "backend\venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "[ERROR] Virtual environment not found at $VenvPython" -ForegroundColor Red
    Write-Host "Please initialize using: py -3.11 -m venv backend\venv" -ForegroundColor Yellow
    exit 1
}

# 2. Start FastAPI Backend
Write-Host "[1/2] Starting FastAPI Backend on http://127.0.0.1:8000 ..." -ForegroundColor Green
$BackendProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RootPath\backend'; & '.\venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload" -PassThru

# 3. Start Vite Frontend
Write-Host "[2/2] Starting Vite Frontend on http://localhost:5173 ..." -ForegroundColor Green
$FrontendProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RootPath\frontend'; npm run dev" -PassThru

Write-Host "`nAsterline AI Assistant successfully launched!" -ForegroundColor Cyan
Write-Host "- Frontend UI: http://localhost:5173" -ForegroundColor White
Write-Host "- Backend API: http://127.0.0.1:8000" -ForegroundColor White
Write-Host "- API Docs:    http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "==============================================================================" -ForegroundColor Cyan
