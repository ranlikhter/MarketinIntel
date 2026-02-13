@echo off
echo Starting MarketIntel Backend API...
echo.
echo The API will be available at: http://localhost:8000
echo API Documentation at: http://localhost:8000/docs
echo.
echo Press CTRL+C to stop the server
echo.
cd backend
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
