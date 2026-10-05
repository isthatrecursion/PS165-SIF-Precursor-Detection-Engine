@echo off
title SIH165 — SIF Precursor Detection Engine
color 0A

echo.
echo  ============================================================
echo    SIH165 — SIF Precursor Detection Engine
echo    Starting backend + frontend servers...
echo  ============================================================
echo.

:: Check if the project-local Python runtime exists
if not exist ".python\python.exe" (
    echo  [ERROR] Project Python runtime not found. Run setup first.
    pause
    exit /b 1
)

:: Check if frontend node_modules exists
if not exist "frontend\node_modules" (
    echo  [ERROR] Frontend node_modules not found. Run: cd frontend ^&^& npm install
    pause
    exit /b 1
)

echo  [1/2] Starting FastAPI backend on http://localhost:8000 ...
start "SIH165 Backend" cmd /k "cd /d %~dp0backend && ..\.python\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Short wait for backend to initialize
timeout /t 4 /nobreak >nul

echo  [2/2] Starting Vite frontend on http://localhost:5173 ...
start "SIH165 Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

timeout /t 5 /nobreak >nul

echo.
echo  ============================================================
echo    Both servers started!
echo.
echo    Frontend  ->  http://localhost:5173
echo    Backend   ->  http://localhost:8000
echo    API Docs  ->  http://localhost:8000/docs
echo  ============================================================
echo.
echo  Opening browser...
start http://localhost:5173

echo  Press any key to close this launcher window.
echo  (The server windows will keep running.)
pause >nul
