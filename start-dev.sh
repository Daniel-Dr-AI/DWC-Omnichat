#!/bin/bash
# =================================================================
# DWC Omnichat Development Server Startup Script
# =================================================================
# This script ensures clean startup of both backend and frontend
# servers, preventing duplicate processes.
#
# Usage: ./start-dev.sh [backend|frontend|both]
# =================================================================

set -e

PROJECT_ROOT="/workspace"
ACTION="${1:-both}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to kill processes by pattern safely
kill_processes() {
    local pattern=$1
    local process_name=$2

    log_info "Checking for existing $process_name processes..."

    # Find PIDs matching the pattern
    local pids=$(pgrep -f "$pattern" 2>/dev/null || true)

    if [ -z "$pids" ]; then
        log_info "No existing $process_name processes found"
        return 0
    fi

    log_warning "Found existing $process_name processes: $pids"
    log_info "Killing $process_name processes..."

    # Try graceful shutdown first
    echo "$pids" | xargs kill -TERM 2>/dev/null || true
    sleep 2

    # Force kill if still running
    local remaining=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [ -n "$remaining" ]; then
        log_warning "Force killing remaining processes..."
        echo "$remaining" | xargs kill -9 2>/dev/null || true
    fi

    log_success "Cleaned up $process_name processes"
}

# Function to start backend server
start_backend() {
    log_info "Starting FastAPI backend server..."

    cd "$PROJECT_ROOT"

    # Kill existing uvicorn processes
    kill_processes "uvicorn server:app" "uvicorn/backend"

    sleep 1

    # Start backend in background
    log_info "Launching uvicorn on port 8000..."
    nohup .venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &
    BACKEND_PID=$!

    sleep 2

    # Check if backend started successfully
    if kill -0 $BACKEND_PID 2>/dev/null; then
        log_success "Backend server started (PID: $BACKEND_PID)"
        log_info "Backend URL: http://localhost:8000"
    else
        log_error "Backend server failed to start. Check /tmp/backend.log for details."
        exit 1
    fi
}

# Function to start frontend server
start_frontend() {
    log_info "Starting Vite frontend server..."

    cd "$PROJECT_ROOT/admin-frontend"

    # Kill existing Vite/npm processes (simplified patterns)
    kill_processes "node.*vite" "Vite"
    kill_processes "npm run dev" "npm dev"

    sleep 1

    # Start frontend in background
    log_info "Launching Vite on port 5173..."
    nohup npm run dev > /tmp/frontend.log 2>&1 &
    FRONTEND_PID=$!

    sleep 3

    # Check if frontend started successfully
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        log_success "Frontend server started (PID: $FRONTEND_PID)"
        log_info "Frontend URL: http://localhost:5173/admin-app/"
    else
        log_error "Frontend server failed to start. Check /tmp/frontend.log for details."
        exit 1
    fi
}

# Function to show status
show_status() {
    echo ""
    log_info "=== Server Status ==="
    echo ""

    local backend_running=$(pgrep -f "uvicorn server:app" 2>/dev/null || true)
    local frontend_running=$(pgrep -f "vite.*admin-frontend" 2>/dev/null || true)

    if [ -n "$backend_running" ]; then
        log_success "Backend: Running (PID: $backend_running)"
        echo "         URL: http://localhost:8000"
    else
        log_error "Backend: Not running"
    fi

    if [ -n "$frontend_running" ]; then
        log_success "Frontend: Running (PID: $frontend_running)"
        echo "          URL: http://localhost:5173/admin-app/"
    else
        log_error "Frontend: Not running"
    fi

    echo ""
    log_info "Logs:"
    echo "  Backend:  tail -f /tmp/backend.log"
    echo "  Frontend: tail -f /tmp/frontend.log"
    echo ""
}

# Main execution
case "$ACTION" in
    backend)
        start_backend
        show_status
        ;;
    frontend)
        start_frontend
        show_status
        ;;
    both)
        start_backend
        start_frontend
        show_status
        ;;
    status)
        show_status
        ;;
    stop)
        log_info "Stopping all servers..."
        kill_processes "uvicorn server:app" "backend"
        kill_processes "vite.*admin-frontend" "Vite"
        kill_processes "npm run dev.*admin-frontend" "npm dev"
        log_success "All servers stopped"
        ;;
    *)
        log_error "Unknown action: $ACTION"
        echo ""
        echo "Usage: $0 [backend|frontend|both|status|stop]"
        echo ""
        echo "Actions:"
        echo "  backend   - Start only the FastAPI backend server"
        echo "  frontend  - Start only the Vite frontend server"
        echo "  both      - Start both servers (default)"
        echo "  status    - Show current server status"
        echo "  stop      - Stop all servers"
        echo ""
        exit 1
        ;;
esac

log_success "Done!"
