#!/bin/bash

# Trap Ctrl+C (SIGINT), SIGTERM, and exit events to stop both servers cleanly
cleanup() {
    echo -e "\n[INFO] Shutting down backend and frontend servers..."
    kill "$BACKEND_PID" 2>/dev/null
    kill "$FRONTEND_PID" 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

echo "============================================="
echo "   AI-Powered Meeting Assistant Runner       "
echo "============================================="

# 1. Verify system prerequisites
echo "[INFO] Verifying system dependencies..."

if ! command -v ffmpeg &> /dev/null; then
    echo "[ERROR] FFmpeg is not installed or not in PATH. Please install FFmpeg (required for audio normalization)."
    exit 1
fi
echo "[OK] FFmpeg is available."

if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js is not installed. Please install Node.js (required to run Vite React frontend)."
    exit 1
fi
echo "[OK] Node.js is available."

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed."
    exit 1
fi
echo "[OK] Python 3 is available."

# Verify directories and virtual environments
if [ ! -d "backend/.venv" ]; then
    echo "[ERROR] Backend virtual environment 'backend/.venv' not found."
    echo "        Please install dependencies first: cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python scripts/bootstrap_models.py"
    exit 1
fi

if [ ! -d "client/node_modules" ]; then
    echo "[INFO] Installing React frontend dependencies..."
    cd client && npm install && cd ..
fi

# 2. Launch concurrent servers
echo -e "\n[INFO] Launching backend server..."
cd backend
source .venv/bin/activate
uvicorn app.main:app --port 8000 --host 127.0.0.1 &
BACKEND_PID=$!
cd ..

echo "[INFO] Launching frontend client..."
cd client
npm run dev &
FRONTEND_PID=$!
cd ..

echo -e "\n[SUCCESS] Servers are up and running!"
echo "          - Frontend: http://localhost:5173"
echo "          - Backend API: http://localhost:8000"
echo "          Press Ctrl+C to terminate both servers."

# Keep script alive waiting for background PIDs
wait
