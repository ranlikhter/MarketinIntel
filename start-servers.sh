#!/bin/bash

echo "========================================"
echo "Starting MarketIntel Platform"
echo "========================================"
echo ""

# Start Backend
echo "[1/2] Starting Backend API on port 8000..."
cd backend/api
python main.py &
BACKEND_PID=$!
cd ../..

sleep 3

# Start Frontend
echo "[2/2] Starting Frontend on port 3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

sleep 2

echo ""
echo "========================================"
echo "MarketIntel Platform Running"
echo "========================================"
echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Backend PID:  $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Wait for both processes
wait
