# Troubleshooting - DWC Admin Mobile App

## Common Issues and Solutions

### Issue: "Cannot find module 'metro-minify-terser'"

**Solution**:
```bash
cd /workspace/dwc-admin-mobile
npm install metro-minify-terser
```

### Issue: Package version warnings

**Error**:
```
The following packages should be updated for best compatibility...
  react-native-gesture-handler@2.29.0 - expected version: ~2.28.0
  react-native-screens@4.18.0 - expected version: ~4.16.0
```

**Solution**:
```bash
npx expo install --fix
```

Or manually install correct versions:
```bash
npx expo install react-native-gesture-handler@~2.28.0 react-native-screens@~4.16.0
```

### Issue: "Network request failed" when trying to login

**Causes**:
1. Backend server not running
2. Wrong API_URL configured
3. Firewall blocking connections

**Solutions**:

1. **Check backend is running**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **For physical devices, update API_URL** in `src/services/api.js`:
   ```javascript
   // DO NOT use localhost for physical devices!
   // Use your computer's local IP address
   export const API_URL = 'http://192.168.1.100:8000';  // Your IP
   export const WS_URL = 'ws://192.168.1.100:8000';
   ```

   Find your IP:
   ```bash
   # Mac/Linux
   ifconfig | grep "inet " | grep -v 127.0.0.1

   # Windows
   ipconfig | findstr IPv4
   ```

3. **Check firewall**:
   - Allow incoming connections on port 8000
   - Allow incoming connections on port 8081 (Metro bundler)

### Issue: "WebSocket disconnected"

**Behavior**: WebSocket connects but immediately disconnects

**Causes**:
1. Token expired
2. Backend WebSocket endpoint not accessible
3. Network switching (WiFi to cellular)

**Solutions**:

1. **Log out and log back in** to get fresh token

2. **Check WebSocket URL** in `src/services/api.js`:
   ```javascript
   // For physical devices, must use IP not localhost
   export const WS_URL = 'ws://YOUR_IP:8000';
   ```

3. **WebSocket auto-reconnects** - wait a few seconds

### Issue: Push notifications not working

**Symptom**: No notifications received when messages arrive

**Common Causes & Solutions**:

1. **Using simulator/emulator**:
   - ❌ Push notifications do NOT work on simulators
   - ✅ Must use physical device (iPhone or Android phone)

2. **Permissions not granted**:
   - Check notification permissions in phone settings
   - Uninstall app and reinstall to trigger permission prompt again

3. **No Expo project ID**:
   ```bash
   # Set up Expo account and project
   npx expo login
   npx eas init

   # Update app.json with project ID
   ```

4. **Token not registered**:
   - Check backend logs: `tail -f /tmp/backend.log | grep "push token"`
   - Should see: "✅ Registered push token for admin@example.com"

5. **Backend not sending**:
   - Check logs: `tail -f /tmp/backend.log | grep "push notification"`
   - Should see: "📤 Sending push notification"

### Issue: Can't scan QR code with Expo Go

**Solutions**:

1. **Make sure Expo Go is installed**:
   - iOS: Download from App Store
   - Android: Download from Play Store

2. **Phone must be on same WiFi network** as your computer

3. **Try tunnel mode**:
   ```bash
   npm start -- --tunnel
   ```

4. **Manually enter URL**:
   - Open Expo Go app
   - Tap "Enter URL manually"
   - Enter: `exp://YOUR_IP:8081`

### Issue: Metro bundler crashes or shows "Error loading"

**Solutions**:

1. **Clear Metro cache**:
   ```bash
   npm start -- --clear
   ```

2. **Reset dependencies**:
   ```bash
   rm -rf node_modules
   npm install
   ```

3. **Clear watchman cache** (Mac/Linux):
   ```bash
   watchman watch-del-all
   ```

### Issue: "Session expired" error

**Cause**: JWT token has expired

**Solution**: Log out and log back in to get a new token

### Issue: Messages not updating in real-time

**Possible causes**:

1. **WebSocket not connected**:
   - Check app console for WebSocket errors
   - Should see: "✅ WebSocket connected"

2. **Backend not broadcasting**:
   - Check backend logs
   - Verify `push_with_admin()` is being called

3. **Not listening to WebSocket messages**:
   - Check `useEffect` dependencies in components

**Solution**: Force refresh conversations by pulling down

### Issue: App crashes on startup

**Solutions**:

1. **Check for syntax errors** in your code

2. **Reinstall dependencies**:
   ```bash
   rm -rf node_modules
   npm install
   ```

3. **Check console for error details**:
   - Look at terminal where `npm start` is running
   - Look at Expo Go app console

4. **Try building fresh**:
   ```bash
   npx expo start -c
   ```

### Issue: Followups showing as conversations or vice versa

**Cause**: Incorrect detection of followup vs conversation

**Check**: In `ChatScreen.js` and `ConversationsScreen.js`, followups are detected by:
```javascript
const isFollowup = conversation.id !== undefined
```

Conversations have `user_id` and `channel`, followups have `id`.

### Issue: Can't connect to backend from Android emulator

**Android emulator special case**:

Android emulator uses `10.0.2.2` to refer to host machine's `localhost`:

```javascript
// In src/services/api.js for Android emulator
export const API_URL = 'http://10.0.2.2:8000';
export const WS_URL = 'ws://10.0.2.2:8000';
```

### Issue: Keyboard covers input field

**iOS specific**: The `KeyboardAvoidingView` should handle this, but if not:

```javascript
// In ChatScreen.js, adjust keyboardVerticalOffset
<KeyboardAvoidingView
  behavior={Platform.OS === 'ios' ? 'padding' : undefined}
  keyboardVerticalOffset={110}  // Increase this value
>
```

## Debugging Tips

### Enable verbose logging

Add console logs in key places:

**In api.js**:
```javascript
export const fetchWithAuth = async (endpoint, options = {}) => {
  console.log('📡 API Request:', endpoint, options);
  // ... rest of function
  console.log('✅ API Response:', data);
  return data;
};
```

**In websocket.js**:
```javascript
ws.onmessage = (event) => {
  console.log('📨 WS Raw:', event.data);
  const data = JSON.parse(event.data);
  console.log('📨 WS Parsed:', data);
  // ... rest
};
```

### Check backend logs

```bash
# Real-time backend logs
tail -f /tmp/backend.log

# Filter for specific events
tail -f /tmp/backend.log | grep -E "admin|push|notification"

# Check WebSocket connections
tail -f /tmp/backend.log | grep "admin-ws"
```

### Test API endpoints manually

```bash
# Test login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin123"

# Test conversations endpoint (replace TOKEN)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/admin/api/conversations?status=open

# Test push token registration
curl -X POST http://localhost:8000/admin/api/push-token \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"push_token":"ExponentPushToken[test]"}'
```

### Inspect React state

In component:
```javascript
useEffect(() => {
  console.log('Current state:', {
    conversations,
    messages,
    user
  });
}, [conversations, messages, user]);
```

### Test push notifications manually

Use Expo's push notification tool:
1. Go to https://expo.dev/notifications
2. Get your push token from app logs
3. Send a test notification

## Getting Help

1. **Check documentation**:
   - `/workspace/dwc-admin-mobile/README.md`
   - `/workspace/docs/MOBILE_APP_GUIDE.md`

2. **Check backend logs**:
   ```bash
   tail -f /tmp/backend.log
   ```

3. **Check app logs**:
   - Look at terminal where `npm start` is running

4. **Search Expo documentation**:
   - https://docs.expo.dev/

5. **Check Expo forums**:
   - https://forums.expo.dev/

## Reset Everything

If all else fails, start fresh:

```bash
# 1. Kill all processes
pkill -9 -f "npm"
pkill -9 -f "expo"
pkill -9 -f "metro"

# 2. Clean project
cd /workspace/dwc-admin-mobile
rm -rf node_modules
rm -rf .expo
rm package-lock.json

# 3. Reinstall
npm install

# 4. Clear Metro cache
npm start -- --clear
```

## Success Checklist

✅ Backend running: `curl http://localhost:8000/health`
✅ Dependencies installed: `ls node_modules`
✅ Correct API_URL configured for your setup
✅ Phone on same WiFi as computer (for physical devices)
✅ Notification permissions granted (for push)
✅ Expo Go installed (for testing)
✅ No firewall blocking ports 8000 and 8081

## Still Having Issues?

Check these files for correct configuration:

1. **API URLs**: `src/services/api.js` lines 12-13
2. **Push config**: `app.json` lines 49-52 (project ID)
3. **Navigation**: `App.js` - check import paths
4. **Auth**: `src/contexts/AuthContext.js` - check login logic

If you've checked everything and still have issues, review the complete setup guide in `/workspace/docs/MOBILE_APP_GUIDE.md`.
