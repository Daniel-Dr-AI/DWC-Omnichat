# DWC Admin Mobile App - Complete Guide

## Overview

The DWC Admin Mobile App is a React Native application built with Expo that allows administrators to manage customer conversations on-the-go with real-time updates and push notifications.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Mobile App (Expo/React Native)           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Login Screen │  │ Conversations│  │ Chat Screen  │      │
│  │  (JWT Auth)  │→ │   (Tabs)     │→ │  (Messages)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         ↓                  ↓                   ↓             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Services Layer                              │  │
│  │  • API Service (HTTP)                                 │  │
│  │  • WebSocket Service (Real-time)                      │  │
│  │  • Notification Service (Push)                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           ↓
                    (WiFi/Cellular)
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                  Backend Server (FastAPI)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Auth API    │  │  Admin APIs  │  │  WebSocket   │      │
│  │  /api/v1/    │  │  /admin/api/ │  │  /admin-ws   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           SQLite Database                             │  │
│  │  • conversations  • messages  • users                 │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           ↓
                  (Expo Push Service)
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              Push Notification Delivery                      │
│  • iOS (APNs) → iPhone/iPad                                 │
│  • Android (FCM) → Android Devices                          │
└─────────────────────────────────────────────────────────────┘
```

## Features Breakdown

### 1. Authentication
- **JWT-based login**
- Tokens stored securely in AsyncStorage
- Auto-login on app restart if token is valid
- Token included in all API requests and WebSocket connection

### 2. Conversation List
- **Three tabs**: Open, Escalated, Followups
- **Pull-to-refresh** to reload conversations
- **Real-time updates** via WebSocket
- Shows user ID, channel, assigned staff, message count
- **Followups** show contact information (email, phone, message)

### 3. Chat Interface
- **Real-time messaging** via WebSocket
- Send and receive messages instantly
- **Different UI for followups** (contact form submissions)
- Message bubbles with timestamps
- Auto-scroll to latest message
- Typing indicators (can be added)

### 4. Push Notifications
- **Automatic registration** on login
- **Sound alerts** when new message arrives
- **Notification payload** includes conversation details
- **Tap notification** to open app (can navigate to specific chat)
- Works even when app is in background or closed

## Installation Steps

### Step 1: Prerequisites

Install required software:
```bash
# Install Node.js (if not already installed)
# Download from: https://nodejs.org/

# Install Expo CLI globally
npm install -g expo-cli

# For iOS development (Mac only)
# Install Xcode from App Store

# For Android development
# Install Android Studio from: https://developer.android.com/studio
```

### Step 2: Project Setup

```bash
# Navigate to mobile app directory
cd /workspace/dwc-admin-mobile

# Install dependencies (may already be installed)
npm install
```

### Step 3: Configure Backend URL

**Important**: Update the API URLs based on your setup.

Edit `src/services/api.js`:

**For Simulator/Emulator (localhost works)**:
```javascript
export const API_URL = 'http://localhost:8000';
export const WS_URL = 'ws://localhost:8000';
```

**For Physical Device (REQUIRED)**:
```javascript
// Replace 192.168.1.100 with YOUR computer's IP address
export const API_URL = 'http://192.168.1.100:8000';
export const WS_URL = 'ws://192.168.1.100:8000';
```

**Find your IP address**:
```bash
# Mac/Linux
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig | findstr IPv4
```

### Step 4: Start Backend Server

Ensure your backend is running:
```bash
cd /workspace
./dev.sh
```

Verify backend is accessible:
```bash
curl http://localhost:8000/health
# Should return: {"status":"running",...}
```

### Step 5: Start Mobile App

```bash
cd /workspace/dwc-admin-mobile
npm start
```

This opens Expo DevTools in your browser.

### Step 6: Run on Device/Simulator

**Option A: iOS Simulator (Mac only)**
```bash
npm run ios
```

**Option B: Android Emulator**
```bash
npm run android
```

**Option C: Physical Device** (Recommended for push notifications)
1. Install **Expo Go** app from App Store / Play Store
2. Scan QR code from terminal/browser
3. App loads on your device

## Push Notification Setup

### Quick Setup (For Development)

1. **Create Expo account** (if you don't have one):
   ```bash
   npx expo register
   npx expo login
   ```

2. **Initialize EAS (Expo Application Services)**:
   ```bash
   cd /workspace/dwc-admin-mobile
   npx eas init
   ```

3. **Get your project ID** from the output or run:
   ```bash
   npx eas project:info
   ```

4. **Update app.json** with your project ID:
   ```json
   {
     "expo": {
       "extra": {
         "eas": {
           "projectId": "paste-your-project-id-here"
         }
       }
     }
   }
   ```

5. **Restart the app** to register for push notifications

### Testing Push Notifications

**Method 1: Test from Mobile App**
1. Login to the app on a physical device
2. Open another device/browser and go to: http://localhost:8000/test-chat-widget.html
3. Send a message from the chat widget
4. You should receive a push notification on your mobile device!

**Method 2: Test Manually**

Use Expo's push notification tool:
1. Go to https://expo.dev/notifications
2. Get your Expo Push Token from the app (it's logged when you login)
3. Paste the token and send a test notification

**Method 3: Test via API**

```bash
# Get your Expo push token from app logs, then:
curl -X POST https://exp.host/--/api/v2/push/send \
  -H "Content-Type: application/json" \
  -d '{
    "to": "ExponentPushToken[YOUR_TOKEN_HERE]",
    "title": "Test Notification",
    "body": "Hello from DWC Admin!",
    "sound": "default"
  }'
```

## Backend Changes Summary

The following changes were made to `/workspace/server.py`:

1. **Added push token storage**:
   ```python
   admin_push_tokens = {}  # Store admin Expo push tokens
   ```

2. **Added POST endpoint** to register push tokens:
   ```python
   @app.post("/admin/api/push-token")
   def register_push_token(request: Request):
       # Stores Expo push token for authenticated admin
   ```

3. **Added function** to send push notifications:
   ```python
   async def send_push_notification(expo_token, title, body, data):
       # Sends notification via Expo Push Service
   ```

4. **Added function** to notify all admins:
   ```python
   async def notify_admins_new_message(user_id, channel, message_text):
       # Sends push to all registered admin devices
   ```

5. **Modified webchat endpoint** to trigger notifications:
   ```python
   @app.post("/webchat")
   async def webchat_post(msg):
       # ... existing code ...
       await notify_admins_new_message(msg.user_id, channel, msg.text)
   ```

## Usage Guide

### Logging In

1. Open the app
2. Enter admin credentials:
   - Email: `admin@example.com`
   - Password: `admin123`
3. Tap "Login"

### Viewing Conversations

1. After login, you see the Conversations screen
2. **Three tabs available**:
   - **Open**: Active customer conversations
   - **Escalated**: Conversations needing attention
   - **Followups**: Contact form submissions

3. **Pull down** to refresh the list

### Responding to Messages

1. **Tap any conversation** to open the chat
2. **View message history** (scrolls to latest)
3. **Type your response** in the input box
4. **Tap Send**
5. Message is sent instantly via WebSocket
6. Customer receives it in real-time

### Handling Followups

Followups are **contact form submissions**, not live chats:

1. Tap a followup to view details
2. See customer's:
   - Name
   - Email
   - Phone
   - Message
3. Contact them via email or phone
4. **Note**: No chat interface for followups

### Receiving Notifications

When a customer sends a message:

1. **App open**: Message appears instantly + notification banner
2. **App in background**: Push notification with sound
3. **App closed**: Push notification with sound
4. **Tap notification**: Opens app (can navigate to conversation)

## File Structure Explained

```
dwc-admin-mobile/
│
├── App.js                          # Main app component
│   └── Wraps app with AuthProvider and NavigationContainer
│
├── app.json                        # Expo configuration
│   └── Contains app name, version, permissions, plugins
│
├── package.json                    # npm dependencies
│
└── src/
    │
    ├── contexts/
    │   └── AuthContext.js          # Authentication state
    │       ├── login()             # Login with email/password
    │       ├── logout()            # Clear tokens and disconnect
    │       └── isAuthenticated     # Check if user is logged in
    │
    ├── screens/
    │   ├── LoginScreen.js          # Login UI
    │   │   └── Email/password form
    │   │
    │   ├── ConversationsScreen.js  # Conversation list
    │   │   ├── Tab bar (Open/Escalated/Followups)
    │   │   ├── Fetches conversations from API
    │   │   ├── Listens to WebSocket for updates
    │   │   └── Pull-to-refresh
    │   │
    │   └── ChatScreen.js           # Chat interface
    │       ├── Displays messages
    │       ├── Send message input
    │       ├── Real-time WebSocket updates
    │       └── Special UI for followups
    │
    └── services/
        ├── api.js                  # HTTP API service
        │   ├── login()             # POST /api/v1/auth/login
        │   ├── fetchOpenConversations()
        │   ├── fetchEscalatedConversations()
        │   ├── fetchFollowups()
        │   ├── fetchMessages()
        │   ├── sendMessage()       # POST /admin/send
        │   └── registerPushToken() # POST /admin/api/push-token
        │
        ├── websocket.js            # WebSocket service
        │   ├── connect()           # Connect to /admin-ws
        │   ├── disconnect()
        │   ├── send()              # Send message via WS
        │   ├── addListener()       # Subscribe to messages
        │   └── Auto-reconnect logic
        │
        └── notifications.js        # Push notification service
            ├── registerForPushNotificationsAsync()
            │   ├── Request permissions
            │   ├── Get Expo push token
            │   └── Register with backend
            │
            └── setupNotificationListeners()
                ├── onNotificationReceived
                └── onNotificationTapped
```

## Common Issues & Solutions

### Issue: "Network request failed"

**Cause**: Backend not running or wrong URL

**Solutions**:
1. Check backend is running: `curl http://localhost:8000/health`
2. Verify API_URL in `src/services/api.js`
3. For physical devices, use local IP not `localhost`
4. Check firewall isn't blocking port 8000

### Issue: "Session expired"

**Cause**: JWT token expired

**Solution**: Log out and log back in

### Issue: "WebSocket disconnected"

**Cause**: Network issue or backend restart

**Solution**: WebSocket will auto-reconnect in a few seconds

### Issue: "Push notifications not arriving"

**Causes & Solutions**:
1. **Using simulator**: Notifications only work on **physical devices**
2. **Permissions denied**: Restart app and grant permissions
3. **No project ID**: Configure EAS project ID in app.json
4. **Token not registered**: Check backend logs for "Registered push token"
5. **Backend not sending**: Check logs for "Sending push notification"

### Issue: "Cannot connect on physical device"

**Solution**:
1. Ensure device is on **same WiFi network** as your computer
2. Use your computer's **local IP** not `localhost`
3. Check firewall allows connections on port 8000

### Issue: "Expo Go shows error loading"

**Solutions**:
1. Restart Expo dev server: `npm start`
2. Clear cache: `expo start -c`
3. Reinstall dependencies: `rm -rf node_modules && npm install`

## Advanced Configuration

### Custom Notification Sound

1. Add sound file to `assets/notification.wav`
2. Update `app.json`:
   ```json
   "plugins": [
     ["expo-notifications", {
       "sounds": ["./assets/notification.wav"]
     }]
   ]
   ```
3. Update `src/services/notifications.js`:
   ```javascript
   sound: 'notification.wav'
   ```

### Background Notification Handling

To handle notifications when app is in background:

```javascript
// In App.js or a service
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});
```

### Navigate to Conversation from Notification

Update `setupNotificationListeners` in App.js:

```javascript
setupNotificationListeners(
  null,
  (response) => {
    const data = response.notification.request.content.data;
    if (data.user_id && data.channel) {
      // Navigate to chat screen
      navigation.navigate('Chat', {
        conversation: {
          user_id: data.user_id,
          channel: data.channel
        }
      });
    }
  }
);
```

## Production Deployment

### 1. Build Standalone App

```bash
# Create builds for App Store / Play Store
npx eas build --platform ios
npx eas build --platform android
```

### 2. Update Production Backend URL

Before building, update `src/services/api.js`:
```javascript
export const API_URL = 'https://your-production-api.com';
export const WS_URL = 'wss://your-production-api.com';
```

### 3. Submit to Stores

Follow Expo guides:
- [iOS Submission](https://docs.expo.dev/submit/ios/)
- [Android Submission](https://docs.expo.dev/submit/android/)

## Monitoring & Debugging

### View App Logs

```bash
# While app is running
# Logs appear in the terminal where you ran `npm start`
```

### View Backend Logs

```bash
tail -f /tmp/backend.log | grep -E "push|notification|admin"
```

### Debug WebSocket

Add logging in `src/services/websocket.js`:
```javascript
ws.onmessage = (event) => {
  console.log('📨 WS Message:', event.data);
  // ... rest of handler
};
```

### Test Push Notification Flow

1. **Check token registration**:
   ```bash
   tail -f /tmp/backend.log | grep "Registered push token"
   ```

2. **Send test message** from chat widget

3. **Check notification sent**:
   ```bash
   tail -f /tmp/backend.log | grep "Sending push notification"
   ```

## Security Considerations

1. **JWT Tokens**: Stored securely in AsyncStorage
2. **HTTPS**: Use HTTPS in production (wss:// for WebSocket)
3. **Token Expiration**: Tokens expire after configured time
4. **Push Tokens**: Only accessible to authenticated admins
5. **WebSocket Auth**: Token required for connection

## Performance Optimization

1. **FlatList**: Used for efficient list rendering
2. **Memoization**: Can add React.memo() to components
3. **Image Caching**: Expo handles automatically
4. **WebSocket**: Single connection for all updates
5. **Lazy Loading**: Load messages on demand

## Future Enhancements

Possible additions:
- [ ] Typing indicators
- [ ] Read receipts
- [ ] File/image attachments
- [ ] Voice messages
- [ ] Dark mode support
- [ ] Tablet optimizations
- [ ] Offline message queue
- [ ] Rich text formatting
- [ ] User profiles with avatars
- [ ] Conversation search
- [ ] Message reactions
- [ ] Canned responses

## Resources

- **Expo Docs**: https://docs.expo.dev/
- **React Navigation**: https://reactnavigation.org/
- **Push Notifications**: https://docs.expo.dev/push-notifications/
- **EAS Build**: https://docs.expo.dev/build/introduction/
- **Expo Forums**: https://forums.expo.dev/

## Support

For help:
1. Check this guide
2. Review main README: `/workspace/dwc-admin-mobile/README.md`
3. Check Expo documentation
4. Check backend logs
5. Create issue in repository

---

**Happy mobile admin chatting! 📱💬**
