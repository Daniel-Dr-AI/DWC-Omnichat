#!/bin/bash
# Simple dev server manager for DWC Omnichat

# Kill all existing processes
echo "🔄 Stopping all existing servers..."
pkill -9 -f "npm run dev" 2>/dev/null
pkill -9 -f "node.*vite" 2>/dev/null
pkill -9 -f "uvicorn server:app" 2>/dev/null
sleep 2

echo "✅ All servers stopped"
echo ""

# Start backend
echo "🚀 Starting backend (port 8000)..."
cd /workspace
nohup .venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &
sleep 2

# Start frontend
echo "🚀 Starting frontend (port 5173)..."
cd /workspace/admin-frontend
nohup npm run dev > /tmp/frontend.log 2>&1 &
sleep 3

echo ""
echo "✅ Servers started!"
echo ""
echo "📍 Backend:  http://localhost:8000"
echo "📍 Frontend: http://localhost:5173/admin-app/"
echo ""
echo "📋 Logs:"
echo "   Backend:  tail -f /tmp/backend.log"
echo "   Frontend: tail -f /tmp/frontend.log"
echo ""

# Show running processes
echo "🔍 Running processes:"
ps aux | grep -E "(uvicorn|vite|npm run dev)" | grep -v grep | awk '{print "   PID " $2 ": " $11 " " $12 " " $13}'
