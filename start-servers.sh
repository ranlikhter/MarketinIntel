#!/bin/bash

echo "========================================"
echo "Starting MarketIntel Platform"
echo "========================================"
echo ""

# ── Backend API ──────────────────────────────────────────────────────────────
echo "[1/4] Starting Backend API on port 8000..."
cd backend/api
python main.py &
BACKEND_PID=$!
cd ../..

sleep 3

# ── Frontend ─────────────────────────────────────────────────────────────────
echo "[2/4] Starting Frontend on port 3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

sleep 2

# ── Celery Worker ─────────────────────────────────────────────────────────────
echo "[3/4] Starting Celery worker..."
cd backend
celery -A celery_app worker \
    --loglevel=info \
    --queues=scraping,analytics,notifications,alerts,integrations,maintenance \
    --concurrency=4 \
    --hostname=worker@%h &
WORKER_PID=$!
cd ..

sleep 2

# ── Celery Beat (scheduler) ───────────────────────────────────────────────────
echo "[4/4] Starting Celery Beat scheduler..."
cd backend
celery -A celery_app beat \
    --loglevel=info \
    --scheduler celery.beat.PersistentScheduler \
    --schedule /tmp/marketintel-celerybeat-schedule &
BEAT_PID=$!
cd ..

sleep 1

echo ""
echo "========================================"
echo "MarketIntel Platform Running"
echo "========================================"
echo ""
echo "Backend:   http://localhost:8000"
echo "Frontend:  http://localhost:3000"
echo "API Docs:  http://localhost:8000/docs"
echo ""
echo "Backend PID:  $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "Worker PID:   $WORKER_PID"
echo "Beat PID:     $BEAT_PID"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Graceful shutdown on Ctrl+C
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID $FRONTEND_PID $WORKER_PID $BEAT_PID 2>/dev/null
    exit 0
}
trap cleanup INT TERM

wait
