# Mobile Development Quick Start

## 🚀 One-Command Startup

```bash
./start-mobile-dev.sh
```

This automated script will:
1. ✅ Kill any existing backend/tunnel/Expo processes
2. ✅ Start your LOCAL backend server (port 8000)
3. ✅ Create a public tunnel to your local backend (via localtunnel)
4. ✅ **Automatically update** `src/services/api.js` with the new tunnel URL
5. ✅ Start Expo with tunnel mode
6. ✅ Display QR code for your phone

**Total time**: ~30-60 seconds

---

## 📱 Connecting Your Phone

Once the script completes:

1. **Scan the QR code** that appears in the terminal with your Expo Go app
2. Wait for app to load (first load takes ~1-2 minutes)
3. **Login** with:
   - Email: `admin@dwc.com`
   - Password: `admin123`

---

## 🔄 What Happens Automatically

### Backend Tunnel URL Auto-Update

Every time you run `./start-mobile-dev.sh`, the script:

1. Creates a new localtunnel URL (e.g., `https://wise-knives-act.loca.lt`)
2. **Automatically updates** your mobile app configuration:
   ```javascript
   // src/services/api.js (auto-updated!)
   export const API_URL = 'https://your-new-tunnel.loca.lt';
   export const WS_URL = 'wss://your-new-tunnel.loca.lt';
   ```
3. Shows you the tunnel URL in the output

**No manual editing needed!** 🎉

---

## 💻 Development Workflow

### Making Backend Changes

1. Edit `server.py` or other backend files
2. Uvicorn auto-reloads (watch the terminal)
3. Changes are immediately available via the tunnel
4. Your phone app reflects changes instantly

### Making Mobile App Changes

1. Edit files in `dwc-admin-mobile/src/`
2. Expo hot-reloads automatically
3. See changes on your phone within seconds

### No Need to Restart

Both backend and frontend have hot-reload enabled!

---

## 🛑 Stopping All Servers

**Option 1**: Press `Ctrl+C` in the terminal running the script

**Option 2**: Run this command:
```bash
pkill -f 'uvicorn|expo|lt --port'
```

---

## 📝 Checking Logs

```bash
# Backend server logs
tail -f /tmp/backend.log

# Tunnel logs
tail -f /tmp/localtunnel.log

# Backend health check
curl $(grep "your url is:" /tmp/localtunnel.log | awk '{print $4}')/health
```

---

## 🔧 Troubleshooting

### Tunnel URL Not Updating

**Symptom**: Mobile app still uses old tunnel URL

**Solution**: The script creates a backup. Check if sed failed:
```bash
# Restore from backup if needed
cp /workspace/dwc-admin-mobile/src/services/api.js.backup /workspace/dwc-admin-mobile/src/services/api.js

# Manually update the URLs
nano /workspace/dwc-admin-mobile/src/services/api.js
```

### Backend Not Starting

**Symptom**: Script says "Backend failed to start"

**Solution**:
```bash
# Check what's using port 8000
lsof -ti:8000 || ss -tlnp | grep 8000

# Kill it
pkill -f "uvicorn server:app"

# Check for Python errors
tail -20 /tmp/backend.log
```

### Expo Tunnel Taking Too Long

**Symptom**: Waiting 5+ minutes for QR code

**Solution**: Kill and restart just Expo:
```bash
pkill -f "expo start"
cd /workspace/dwc-admin-mobile
npx expo start --tunnel
```

### Localtunnel Gives "503 Service Unavailable"

**Symptom**: Tunnel URL loads but shows 503 error

**Solution**:
1. Backend might not be running - check `curl http://localhost:8000/health`
2. Restart the script: `./start-mobile-dev.sh`

---

## 🎯 Pro Tips

### 1. Keep Terminal Visible

Run the script in a terminal window you can see. It shows:
- Tunnel URL (highlighted in green)
- Expo QR code
- Real-time Metro bundler output

### 2. Use Multiple Terminals

```bash
# Terminal 1: Run the startup script
./start-mobile-dev.sh

# Terminal 2: Watch backend logs
tail -f /tmp/backend.log

# Terminal 3: Make code changes
code .
```

### 3. Quick Restart

To restart everything:
```bash
Ctrl+C  # Stop the script
./start-mobile-dev.sh  # Start again
```

Tunnel URL will update automatically!

### 4. Check Current Tunnel URL Anytime

```bash
cat /tmp/localtunnel.log | grep "your url is:"
```

---

## 🔐 Security Note

**Localtunnel URLs are public** but temporary:
- ✅ Anyone with the URL can access your dev backend
- ✅ URLs change every restart
- ✅ Perfect for development, not for production

For production, use your Render deployment: `https://dwc-omnichat.onrender.com`

---

## 📚 Related Documentation

- **SETUP.md** - Full development environment setup
- **LOCAL_DEV_GUIDE.md** - Detailed development workflow
- **MOBILE_APP_SUMMARY.md** - Mobile app architecture
- **CLAUDE.md** - Complete project reference

---

## ❓ Common Questions

**Q: Do I need to run this every time I restart my devcontainer?**
A: Yes, but it's just one command: `./start-mobile-dev.sh`

**Q: Can I use my production backend instead?**
A: Yes! Edit `src/services/api.js` to use `https://dwc-omnichat.onrender.com`

**Q: Will my changes push to Render automatically?**
A: No! This script connects your phone to your LOCAL backend. Your changes stay local until you `git push`.

**Q: Can multiple people use the same tunnel?**
A: Yes! Share the tunnel URL with teammates for testing.

**Q: Does this work without internet?**
A: No, localtunnel requires internet. For offline dev, use LAN mode (see LOCAL_DEV_GUIDE.md).
