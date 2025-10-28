#!/bin/bash
# DWC Omnichat Mobile Development Startup Script (with ngrok)
# Uses ngrok for reliable backend tunneling

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}DWC Omnichat Mobile Development (ngrok)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Kill any existing processes
echo -e "${YELLOW}Cleaning up existing processes...${NC}"
pkill -f "uvicorn server:app" 2>/dev/null || true
pkill -f "expo start" 2>/dev/null || true
pkill -f "ngrok http" 2>/dev/null || true
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

# Step 2: Start ngrok tunnel
echo -e "${BLUE}Step 2: Starting ngrok tunnel...${NC}"
/workspace/ngrok http 8000 --log=stdout > /tmp/ngrok.log 2>&1 &
TUNNEL_PID=$!
echo "Ngrok PID: $TUNNEL_PID"
echo "Waiting for ngrok to establish tunnel..."
sleep 8

# Extract ngrok URL from log (ngrok v3 format)
TUNNEL_URL=$(grep -o "url=https://[a-z0-9-]*\.ngrok-free\.app" /tmp/ngrok.log | head -1 | sed 's/url=//')

if [ -z "$TUNNEL_URL" ]; then
    # Try alternative format
    TUNNEL_URL=$(grep -o "https://[a-z0-9-]*\.ngrok-free\.app" /tmp/ngrok.log | head -1)
fi

if [ -z "$TUNNEL_URL" ]; then
    # Try .io format (older)
    TUNNEL_URL=$(grep -o "https://[a-z0-9-]*\.ngrok\.io" /tmp/ngrok.log | head -1)
fi

if [ -z "$TUNNEL_URL" ]; then
    echo -e "${RED}❌ Failed to get ngrok URL${NC}"
    echo "Ngrok log:"
    cat /tmp/ngrok.log
    exit 1
fi

echo -e "${GREEN}✅ Ngrok tunnel URL: ${TUNNEL_URL}${NC}"
echo ""

# Step 3: Update Mobile App Configuration
echo -e "${BLUE}Step 3: Updating mobile app API configuration...${NC}"

API_FILE="/workspace/dwc-admin-mobile/src/services/api.js"

# Create backup
cp "$API_FILE" "$API_FILE.backup"

# Update the API URLs using sed
sed -i "s|export const API_URL = '.*';.*|export const API_URL = '${TUNNEL_URL}';  // LOCAL BACKEND via ngrok (auto-updated)|g" "$API_FILE"
sed -i "s|export const WS_URL = '.*';.*|export const WS_URL = '${TUNNEL_URL/https/wss}';      // LOCAL BACKEND via ngrok (auto-updated)|g" "$API_FILE"

echo -e "${GREEN}✅ Mobile app configured to use: ${TUNNEL_URL}${NC}"
echo ""

# Step 4: Display summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ BACKEND SETUP COMPLETE!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}📱 Connection Information:${NC}"
echo ""
echo -e "  ${GREEN}Backend Tunnel URL:${NC} ${TUNNEL_URL}"
echo -e "  ${GREEN}Backend Health:${NC} ${TUNNEL_URL}/health"
echo -e "  ${GREEN}Ngrok Dashboard:${NC} http://localhost:4040"
echo ""
echo -e "${BLUE}📝 Background Processes:${NC}"
echo "  - Backend PID: $BACKEND_PID (logs: /tmp/backend.log)"
echo "  - Ngrok PID: $TUNNEL_PID (logs: /tmp/ngrok.log)"
echo ""
echo -e "${BLUE}🎯 Next Steps:${NC}"
echo ""
echo "  1. Wait for Expo QR code to appear below (30-60 seconds)"
echo "  2. Open Expo Go app on your phone"
echo "  3. Scan the QR code"
echo "  4. Login with:"
echo "     - Email: admin@dwc.com"
echo "     - Password: admin123"
echo ""
echo -e "${YELLOW}⚠️  Important:${NC}"
echo "  - Backend & ngrok are running in background"
echo "  - Expo is running in FOREGROUND (you'll see output below)"
echo "  - Press Ctrl+C to stop Expo (backend will keep running)"
echo "  - Ngrok web interface: http://localhost:4040"
echo ""
echo -e "${BLUE}🛑 To stop all servers:${NC}"
echo "  - Run: pkill -f 'uvicorn|expo|ngrok'"
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Starting Expo...${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 5: Start Expo in FOREGROUND (no &)
cd /workspace/dwc-admin-mobile
npx expo start --tunnel
