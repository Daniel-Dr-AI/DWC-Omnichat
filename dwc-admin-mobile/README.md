# DWC Admin Mobile App

A React Native mobile application for iOS and Android that connects to the DWC Omnichat admin dashboard, providing real-time chat management with push notifications.

## Features

✅ **Cross-platform**: Single codebase for iOS and Android
✅ **Real-time messaging**: WebSocket connection for instant updates
✅ **Push notifications**: Expo Push Notifications with sound alerts
✅ **JWT Authentication**: Secure login with token-based auth
✅ **Conversation management**: View open, escalated, and followup conversations
✅ **Live chat**: Send and receive messages in real-time
✅ **Offline support**: Graceful handling of network issues
✅ **Auto-reconnect**: WebSocket automatically reconnects on disconnect

## Prerequisites

- Node.js 18+ and npm
- Expo CLI: `npm install -g expo-cli`
- iOS: Xcode and iOS Simulator (Mac only)
- Android: Android Studio and Android SDK
- Physical device for push notification testing

## Installation

1. **Navigate to the mobile app directory**:
   ```bash
   cd dwc-admin-mobile
   ```

2. **Install dependencies** (if not already done):
   ```bash
   npm install
   ```

3. **Configure backend URL**:

   Edit `src/services/api.js` and update the URLs:
   ```javascript
   // For local development with physical device, use your computer's local IP
   export const API_URL = 'http://192.168.1.100:8000';  // Replace with your IP
   export const WS_URL = 'ws://192.168.1.100:8000';

   // For simulator/emulator
   export const API_URL = 'http://localhost:8000';
   export const WS_URL = 'ws://localhost:8000';
   ```

4. **Find your local IP address**:
   - **Mac/Linux**: `ifconfig | grep "inet " | grep -v 127.0.0.1`
   - **Windows**: `ipconfig | findstr IPv4`

## Running the App

### Start the Backend Server

Make sure your backend server is running first:
```bash
cd /workspace
./dev.sh
```

### Start the Mobile App

```bash
cd dwc-admin-mobile
npm start
```

This will open Expo DevTools in your browser.

### Running on iOS Simulator (Mac only)

```bash
npm run ios
```

### Running on Android Emulator

```bash
npm run android
```

### Running on Physical Device

1. Install the **Expo Go** app from App Store or Play Store
2. Scan the QR code shown in the terminal
3. The app will load on your device

**Note**: For physical devices, you MUST update the API_URL and WS_URL to use your computer's local IP address (not localhost).

## Push Notifications Setup

Push notifications require additional setup:

### 1. Create an Expo Account

```bash
npx expo login
```

### 2. Get Expo Project ID

```bash
npx eas init
```

This will create a project and give you a project ID.

### 3. Update app.json

Replace `your-project-id-here` in `app.json` with your actual project ID:
```json
{
  "expo": {
    "extra": {
      "eas": {
        "projectId": "your-actual-project-id"
      }
    }
  }
}
```

### 4. Build for Physical Device (Optional)

For full push notification functionality, build a development client:

```bash
# iOS
npx eas build --profile development --platform ios

# Android
npx eas build --profile development --platform android
```

### 5. Test Push Notifications

Push notifications only work on **physical devices**, not simulators/emulators.

## Project Structure

```
dwc-admin-mobile/
├── App.js                      # Main app entry point
├── app.json                    # Expo configuration
├── package.json                # Dependencies
├── src/
│   ├── contexts/
│   │   └── AuthContext.js      # Authentication state management
│   ├── screens/
│   │   ├── LoginScreen.js      # Login screen
│   │   ├── ConversationsScreen.js  # Conversation list (Open/Escalated/Followups)
│   │   └── ChatScreen.js       # Chat interface
│   ├── services/
│   │   ├── api.js              # HTTP API service
│   │   ├── websocket.js        # WebSocket service
│   │   └── notifications.js    # Push notification service
│   └── components/             # Reusable components
└── assets/                     # Images and assets
```

## How It Works

### Authentication Flow

1. User enters email and password
2. App sends credentials to `/api/v1/auth/login`
3. Backend returns JWT token
4. Token is stored in AsyncStorage
5. Token is used for all subsequent API requests
6. WebSocket connects using token as query parameter

### Real-time Messaging Flow

1. App connects to WebSocket at `/admin-ws?token={jwt}`
2. Backend sends snapshot of all conversations
3. User taps a conversation to open chat
4. Messages are fetched via `/admin/api/messages/{user_id}/{channel}`
5. New messages arrive via WebSocket in real-time
6. User types and sends message via `/admin/send`
7. Message is broadcast to user and other admins

### Push Notification Flow

1. On login, app requests notification permissions
2. App registers for Expo Push Token
3. Token is sent to backend via `/admin/api/push-token`
4. Backend stores token for this admin
5. When customer sends message to `/webchat`:
   - Message is saved to database
   - Message is broadcast via WebSocket
   - **Push notification is sent to all registered admin devices**
6. Admin receives notification with sound alert
7. Tapping notification opens the app

## API Endpoints Used

### Authentication
- `POST /api/v1/auth/login` - Login with email/password

### Conversations
- `GET /admin/api/conversations?status=open` - Get open conversations
- `GET /admin/api/conversations?status=escalated` - Get escalated conversations
- `GET /admin/api/followups` - Get followup requests

### Messages
- `GET /admin/api/messages?user_id={id}&channel={channel}` - Get conversation history
- `POST /admin/send` - Send message to customer

### Push Notifications
- `POST /admin/api/push-token` - Register Expo Push Token

### WebSocket
- `WS /admin-ws?token={jwt}` - Real-time admin connection

## Default Credentials

Use your admin credentials from the web dashboard:

- **Email**: `admin@example.com`
- **Password**: `admin123`

(Or whatever credentials you've set up in your system)

## Troubleshooting

### "Network request failed"

- Check that backend server is running (`./dev.sh`)
- Verify API_URL is correct (use local IP for physical devices)
- Check firewall settings
- Ensure device is on the same network as backend server

### "WebSocket disconnected"

- WebSocket will auto-reconnect, wait a few seconds
- Check backend logs for WebSocket errors
- Verify WS_URL is correct

### "Push notifications not working"

- Push notifications only work on **physical devices**
- Ensure you've granted notification permissions
- Check that Expo project ID is configured in app.json
- Verify backend has received the push token (check logs)

### "Session expired" error

- JWT tokens expire after a certain time
- Log out and log back in to get a new token

## Development Tips

### Hot Reloading

Expo supports hot reloading. Save any file and changes will appear instantly.

### Debugging

- Shake device to open developer menu
- Enable "Debug Remote JS" to use Chrome DevTools
- View console logs in terminal where `npm start` is running

### Backend Logs

Monitor backend logs to see push notification activity:
```bash
tail -f /tmp/backend.log
```

Look for messages like:
```
✅ Registered push token for admin@example.com
📤 Sending push notification to admin@example.com
✅ Push notification sent
```

## Production Deployment

### Build Standalone Apps

```bash
# iOS
npx eas build --platform ios

# Android
npx eas build --platform android
```

### App Store / Play Store

Follow Expo's guides for:
- [iOS App Store Submission](https://docs.expo.dev/submit/ios/)
- [Android Play Store Submission](https://docs.expo.dev/submit/android/)

## Additional Resources

- [Expo Documentation](https://docs.expo.dev/)
- [React Navigation](https://reactnavigation.org/)
- [Expo Notifications](https://docs.expo.dev/push-notifications/overview/)
- [Expo Push Notification Tool](https://expo.dev/notifications) - Test sending notifications

## License

Same as parent project

## Support

For issues or questions, check the main project documentation or create an issue in the repository.
