#!/bin/bash
# DWC Omnichat Mobile Development Startup Script
# Starts backend, tunnels it, updates mobile app config, and starts Expo

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}DWC Omnichat Mobile Development${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Kill any existing processes
echo -e "${YELLOW}Cleaning up existing processes...${NC}"
pkill -f "uvicorn server:app" 2>/dev/null || true
pkill -f "expo start" 2>/dev/null || true
pkill -f "lt --port" 2>/dev/null || true
sleep 2
echo -e "${GREEN}✅ Cleanup complete${NC}"
echo ""

# Step 1: Start Backend Server
echo -e "${BLUE}Step 1: Starting backend server...${NC}"
cd /workspace
source .venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"
echo "Waiting for backend to start..."

# Wait up to 15 seconds for backend to be ready
for i in {1..15}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend running on port 8000${NC}"
        break
    fi
    sleep 1
    if [ $i -eq 15 ]; then
        echo -e "${RED}❌ Backend failed to start after 15 seconds${NC}"
        echo "Check logs: tail -f /tmp/backend.log"
        exit 1
    fi
done
echo ""

# Step 2: Start Backend Tunnel
echo -e "${BLUE}Step 2: Starting backend tunnel (localtunnel)...${NC}"
lt --port 8000 > /tmp/localtunnel.log 2>&1 &
TUNNEL_PID=$!
echo "Tunnel PID: $TUNNEL_PID"
sleep 5

# Get tunnel URL
TUNNEL_URL=$(grep "your url is:" /tmp/localtunnel.log | awk '{print $4}')

if [ -z "$TUNNEL_URL" ]; then
    echo -e "${RED}❌ Failed to get tunnel URL${NC}"
    cat /tmp/localtunnel.log
    exit 1
fi

echo -e "${GREEN}✅ Backend tunnel URL: ${TUNNEL_URL}${NC}"
echo ""

# Step 3: Update Mobile App Configuration
echo -e "${BLUE}Step 3: Updating mobile app API configuration...${NC}"

API_FILE="/workspace/dwc-admin-mobile/src/services/api.js"

# Create backup
cp "$API_FILE" "$API_FILE.backup"

# Update the API URLs using sed
sed -i "s|export const API_URL = '.*';.*|export const API_URL = '${TUNNEL_URL}';  // LOCAL BACKEND via localtunnel (auto-updated)|g" "$API_FILE"
sed -i "s|export const WS_URL = '.*';.*|export const WS_URL = '${TUNNEL_URL/https/wss}';      // LOCAL BACKEND via localtunnel (auto-updated)|g" "$API_FILE"

echo -e "${GREEN}✅ Mobile app configured to use: ${TUNNEL_URL}${NC}"
echo ""

# Step 4: Display summary before starting Expo
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ BACKEND SETUP COMPLETE!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}📱 Connection Information:${NC}"
echo ""
echo -e "  ${GREEN}Backend Tunnel URL:${NC} ${TUNNEL_URL}"
echo -e "  ${GREEN}Backend Health:${NC} ${TUNNEL_URL}/health"
echo ""
echo -e "${BLUE}🎯 Next Steps:${NC}"
echo ""
echo "  1. Wait for Expo QR code to appear below"
echo "  2. Open Expo Go app on your phone"
echo "  3. Scan the QR code"
echo "  4. Login with:"
echo "     - Email: admin@dwc.com"
echo "     - Password: admin123"
echo ""
echo -e "${YELLOW}⚠️  Important:${NC}"
echo "  - Backend changes reload automatically (uvicorn --reload)"
echo "  - Frontend changes hot-reload via Expo"
echo "  - Tunnel URL is valid until you restart this script"
echo ""
echo -e "${BLUE}📝 Logs:${NC}"
echo "  - Backend: tail -f /tmp/backend.log"
echo "  - Tunnel: tail -f /tmp/localtunnel.log"
echo ""
echo -e "${BLUE}🛑 To stop all servers:${NC}"
echo "  - Press Ctrl+C, then run: pkill -f 'uvicorn|expo|lt --port'"
echo ""

# Step 5: Start Expo (in foreground so QR code is visible)
echo -e "${BLUE}Step 4: Starting Expo with tunnel...${NC}"
echo -e "${YELLOW}This will take 30-60 seconds to establish tunnel...${NC}"
echo ""
cd /workspace/dwc-admin-mobile
npx expo start --tunnel
