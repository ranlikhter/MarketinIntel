@echo off
echo ========================================
echo Starting MarketIntel Platform
echo ========================================
echo.

REM Start Backend
echo [1/2] Starting Backend API on port 8000...
start "MarketIntel Backend" cmd /k "cd backend\api && python main.py"
timeout /t 3 /nobreak >nul

REM Start Frontend
echo [2/2] Starting Frontend on port 3000...
start "MarketIntel Frontend" cmd /k "cd frontend && npm run dev"
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo MarketIntel Platform Starting...
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo.
echo Press any key to open the platform...
pause >nul

start http://localhost:3000
