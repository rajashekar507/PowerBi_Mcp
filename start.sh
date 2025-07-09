#!/bin/bash

echo "Starting AI Power BI Dashboard Generator..."
echo

echo "[1/3] Activating Python environment..."
source venv/bin/activate

echo "[2/3] Starting Backend Server..."
python main.py &
BACKEND_PID=$!

echo "[3/3] Starting Frontend..."
sleep 3
cd frontend
npm start &
FRONTEND_PID=$!

echo
echo "✅ Both services are starting..."
echo "🌐 Frontend will be available at: http://localhost:3000"
echo "📚 API Documentation at: http://127.0.0.1:8001/docs"
echo
echo "Press Ctrl+C to stop both services..."

# Wait for user interrupt
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait