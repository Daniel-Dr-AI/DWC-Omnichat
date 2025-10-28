# DWC Admin Mobile - Quick Start Guide

## 🚀 Get Running in 5 Minutes

### Prerequisites
- Node.js installed
- Backend server running
- (Optional) Expo Go app on your phone

### Step 1: Install Dependencies (30 seconds)
```bash
cd /workspace/dwc-admin-mobile
npm install
```

### Step 2: Configure Backend URL (30 seconds)

**If using simulator/emulator**:
Already configured! Skip this step.

**If using physical device**:

1. Find your computer's IP address:
   ```bash
   # Mac/Linux
   ifconfig | grep "inet " | grep -v 127.0.0.1

   # Windows
   ipconfig | findstr IPv4
   ```

2. Edit `src/services/api.js`:
   ```javascript
   // Replace these lines (around line 12-13)
   export const API_URL = 'http://YOUR_IP_HERE:8000';  // e.g., 192.168.1.100
   export const WS_URL = 'ws://YOUR_IP_HERE:8000';
   ```

### Step 3: Start Backend (if not already running)
```bash
cd /workspace
./dev.sh
```

Verify it's running:
```bash
curl http://localhost:8000/health
```

### Step 4: Start Mobile App (30 seconds)
```bash
cd /workspace/dwc-admin-mobile
npm start
```

### Step 5: Run the App

**Option A: Simulator (Quick Test)**
```bash
# iOS (Mac only)
npm run ios

# Android
npm run android
```

**Option B: Physical Device (For Push Notifications)**
1. Install **Expo Go** from App Store / Play Store
2. Scan the QR code in your terminal
3. App loads!

### Step 6: Login
- Email: `admin@example.com`
- Password: `admin123`

### Step 7: Test Push Notifications (Optional)

1. **On another device**, open:
   ```
   http://YOUR_IP:8000/test-chat-widget.html
   ```

2. Send a message

3. **Your phone** should receive a push notification with sound!

---

## 📱 What You Get

✅ iOS and Android app
✅ Real-time messaging
✅ Push notifications with sound
✅ View Open/Escalated/Followups
✅ Send and receive messages instantly

---

## 🔧 Troubleshooting

### "Network request failed"
- ✅ Check backend is running: `curl http://localhost:8000/health`
- ✅ For physical device, use your IP not `localhost`
- ✅ Check firewall allows port 8000

### "WebSocket disconnected"
- ✅ Wait a few seconds, it auto-reconnects

### "Push notifications not working"
- ✅ Must use **physical device** (not simulator)
- ✅ Grant notification permissions when prompted
- ✅ Check backend logs: `tail -f /tmp/backend.log | grep push`

---

## 📚 Full Documentation

For detailed info, see:
- **Setup & Usage**: `/workspace/dwc-admin-mobile/README.md`
- **Complete Guide**: `/workspace/docs/MOBILE_APP_GUIDE.md`
- **Summary**: `/workspace/MOBILE_APP_SUMMARY.md`

---

## 🎉 You're Done!

Your mobile admin app is running!

**Next**: Send a test message from the chat widget and receive a push notification on your phone! 📲
