@echo off
echo ==============================================================================
echo        Starting Asterline AI Research Assistant (Backend + Frontend)
echo ==============================================================================

cd /d "%~dp0"

echo [1/3] Checking Python virtual environment...
if not exist "backend\venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at backend\venv! Please create it via:
    echo py -3.11 -m venv backend\venv
    pause
    exit /b 1
)

echo [2/3] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "Asterline Backend (FastAPI)" cmd /k "cd backend && venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [3/3] Starting Vite Frontend on http://localhost:5173 ...
start "Asterline Frontend (Vite)" cmd /k "cd frontend && npm run dev"

echo ==============================================================================
echo Application launched!
echo - Frontend: http://localhost:5173
echo - Backend API: http://127.0.0.1:8000
echo - Swagger Docs: http://127.0.0.1:8000/docs
echo ==============================================================================
