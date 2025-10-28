# Starting the Mobile App in DevContainer

## The Problem
Your DevContainer is at IP `172.17.0.2` (Docker internal IP), which your phone **cannot** reach directly.

## Solutions (Choose One)

### ✅ **Option 1: Use Tunnel Mode** (Recommended for DevContainer)

This creates a public URL that your phone can reach:

```bash
cd /workspace/dwc-admin-mobile
npx expo start --tunnel
```

**Pros**: Works from anywhere, no network configuration needed
**Cons**: Slower, requires internet connection

### ✅ **Option 2: Use LAN with Port Forwarding**

This uses your local network but requires port forwarding:

1. **First, forward port 8081** from DevContainer to host:
   - In VS Code, go to Ports panel
   - Forward port 8081
   - Or add to `.devcontainer/devcontainer.json`:
     ```json
     "forwardPorts": [8000, 5173, 8081]
     ```

2. **Start Expo**:
   ```bash
   cd /workspace/dwc-admin-mobile
   npx expo start --lan
   ```

3. **Scan QR code** with Expo Go on your phone

**Pros**: Faster, works offline
**Cons**: Requires port forwarding setup

### ✅ **Option 3: Use Your Host Machine's IP** (Easiest!)

If your ports are already forwarded (8000, 8081):

1. **Find your host machine's IP**:
   ```bash
   # Mac/Linux
   ifconfig | grep "inet " | grep -v 127.0.0.1

   # Windows
   ipconfig | findstr IPv4
   ```

2. **Start Expo normally**:
   ```bash
   cd /workspace/dwc-admin-mobile
   npx expo start
   ```

3. **Manually enter URL in Expo Go**:
   - Open Expo Go app
   - Tap "Enter URL manually"
   - Enter: `exp://YOUR_HOST_IP:8081`
   - Example: `exp://192.168.1.100:8081`

**Pros**: No tunnel needed, fast
**Cons**: Need to know host IP and ensure ports are forwarded

## Recommended Approach

**For first-time setup**, use **Option 3**:

1. Make sure your DevContainer has ports 8000 and 8081 forwarded
2. Find your host machine's IP address
3. Start expo: `npx expo start`
4. In Expo Go, manually enter: `exp://YOUR_HOST_IP:8081`

## Current Status

You ran:
```bash
npx expo start --tunnel
```

This should work but may be slow. **Wait about 30-60 seconds** for the tunnel to establish, then you'll see a QR code with a URL like:
```
exp://u.expo.dev/...
```

Scan that QR code with Expo Go!

## If Tunnel Is Too Slow

Press `Ctrl+C` and try Option 3 instead:

```bash
# Find your host IP first
ifconfig | grep "inet "

# Then start expo normally
cd /workspace/dwc-admin-mobile
npx expo start

# Manually enter in Expo Go: exp://YOUR_IP:8081
```

## Verifying It Works

Once connected, you should see:
1. Metro bundler building JavaScript bundle
2. App loading on your phone
3. Login screen appearing

Then login with:
- Email: `admin@example.com`
- Password: `admin123`

## Need Help?

Check full guide: `/workspace/docs/MOBILE_APP_GUIDE.md`
