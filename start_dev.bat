@echo off
title OmniLogix ULPF Launcher
echo ============================================================
echo   OmniLogix Universal Log Pre-Processing Framework (ULPF)
echo   SIH 2026 Problem Statement: SIH26156 (NTRO)
echo ============================================================
echo.
echo Starting Backend API Server (Port 8000)...
start "OmniLogix Backend (FastAPI)" cmd /k "python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo Starting Frontend UI Server (Port 5173)...
start "OmniLogix Frontend (Vite)" cmd /k "cd frontend && npm run dev"

echo.
echo ============================================================
echo   Both services are now launching:
echo   - Web UI:     http://localhost:5173
echo   - Backend:    http://localhost:8000/docs
echo ============================================================
echo.
pause
