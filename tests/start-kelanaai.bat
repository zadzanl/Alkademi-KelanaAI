@echo off
setlocal

rem KelanaAI local development launcher.
rem Double-click this file from Windows Explorer, or run it from a terminal.

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "BACKEND_PY=%ROOT%\backend\.venv\Scripts\python.exe"
set "FRONTEND_DIR=%ROOT%\frontend"
set "ENV_FILE=%FRONTEND_DIR%\.env.local"

if not exist "%BACKEND_PY%" (
  echo [ERROR] Missing backend virtual environment: %BACKEND_PY%
  echo Create it with: python -m venv backend/.venv
  pause
  exit /b 1
)

if not exist "%ROOT%\.env" (
  echo [ERROR] Missing backend environment file: %ROOT%\.env
  echo Create the root .env with DATABASE_URL before starting FastAPI.
  pause
  exit /b 1
)

if not exist "%ENV_FILE%" (
  echo [ERROR] Missing frontend environment file: %ENV_FILE%
  echo Create it with: Copy-Item frontend/.env.example frontend/.env.local
  echo Then set API_URL=http://127.0.0.1:8000
  pause
  exit /b 1
)

if not exist "%FRONTEND_DIR%\node_modules" (
  echo [ERROR] Frontend dependencies are not installed.
  echo Run: cd frontend ^&^& npm ci
  pause
  exit /b 1
)

echo Starting KelanaAI backend and frontend...
start "KelanaAI Backend - FastAPI" powershell.exe -NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%ROOT%'; & '%BACKEND_PY%' -m uvicorn backend.main:app --reload"
start "KelanaAI Frontend - Next.js" powershell.exe -NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%FRONTEND_DIR%'; npm run dev"

echo.
echo Backend:  http://127.0.0.1:8000/health
 echo Frontend: http://localhost:3000
 echo.
echo Two PowerShell windows were opened. Close those windows to stop the servers.
endlocal
