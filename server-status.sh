#!/bin/bash
# Comprehensive server status check

echo "════════════════════════════════════════════════════════"
echo "  SERVER STATUS CHECK"
echo "════════════════════════════════════════════════════════"
echo ""

# Check backend
echo "🔍 BACKEND (Port 8000):"
if curl -s --max-time 2 http://localhost:8000/health >/dev/null 2>&1; then
    echo "   ✅ Responding"
    BACKEND_RESPONSE=$(curl -s http://localhost:8000/health)
    echo "   Response: $BACKEND_RESPONSE"
else
    echo "   ❌ Not responding"
fi

# Find what's listening on 8000
BACKEND_PID=$(ss -tlnp 2>/dev/null | grep :8000 | grep -oP 'pid=\K[0-9]+' | head -1)
if [ -n "$BACKEND_PID" ]; then
    echo "   Process on port 8000: PID $BACKEND_PID"
    ps -p $BACKEND_PID -o pid,ppid,cmd --no-headers 2>/dev/null | sed 's/^/   /'
else
    echo "   No process found on port 8000"
fi

echo ""

# Check frontend
echo "🔍 FRONTEND (Port 5173):"
if curl -s --max-time 2 http://localhost:5173/admin-app/ >/dev/null 2>&1; then
    echo "   ✅ Responding"
else
    echo "   ❌ Not responding"
fi

# Find what's listening on 5173
FRONTEND_PID=$(ss -tlnp 2>/dev/null | grep :5173 | grep -oP 'pid=\K[0-9]+' | head -1)
if [ -n "$FRONTEND_PID" ]; then
    echo "   Process on port 5173: PID $FRONTEND_PID"
    ps -p $FRONTEND_PID -o pid,ppid,cmd --no-headers 2>/dev/null | sed 's/^/   /'

    # Find parent npm process
    PPID=$(ps -p $FRONTEND_PID -o ppid --no-headers | tr -d ' ')
    if [ -n "$PPID" ] && [ "$PPID" != "1" ]; then
        echo "   Parent process: PID $PPID"
        ps -p $PPID -o pid,ppid,cmd --no-headers 2>/dev/null | sed 's/^/   /'
    fi
else
    echo "   No process found on port 5173"
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "  PROCESS COUNT"
echo "════════════════════════════════════════════════════════"
echo ""

# Count processes
UVICORN_COUNT=$(pgrep -f "uvicorn server:app" 2>/dev/null | wc -l)
VITE_COUNT=$(pgrep -f "node.*vite" 2>/dev/null | wc -l)
NPM_COUNT=$(pgrep -f "npm run dev" 2>/dev/null | wc -l)

echo "uvicorn processes: $UVICORN_COUNT"
echo "vite processes: $VITE_COUNT"
echo "npm processes: $NPM_COUNT"

if [ "$VITE_COUNT" -gt 1 ]; then
    echo "⚠️  Warning: Multiple Vite processes detected!"
fi

if [ "$UVICORN_COUNT" -gt 1 ]; then
    echo "⚠️  Warning: Multiple uvicorn processes detected!"
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "  LOGS"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Backend log:  tail -f /tmp/backend.log"
echo "Frontend log: tail -f /tmp/frontend.log"
echo ""
