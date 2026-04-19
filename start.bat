@echo off
REM Smart Drone Traffic Analyzer - Web App
echo ============================================
echo  Smart Drone Traffic Analyzer - Web App
echo ============================================
echo.

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

echo Starting FastAPI backend on http://localhost:8000 ...
if /I "%CONDA_DEFAULT_ENV%"=="drone-env" (
  start "Drone Backend" cmd /k "cd /d ""%SCRIPT_DIR%"" && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
) else (
  start "Drone Backend" cmd /k "cd /d ""%SCRIPT_DIR%"" && conda run -n drone-env --no-capture-output python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
)

echo Starting React frontend on http://localhost:3000 ...
cd /d "%SCRIPT_DIR%"
cd frontend
npm start
