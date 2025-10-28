# DWC Admin Mobile App - Architecture Documentation

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CUSTOMER SIDE                                 │
│                                                                       │
│  ┌───────────────┐      ┌───────────────┐      ┌───────────────┐  │
│  │   WordPress   │      │  Test Widget  │      │   SMS/Email   │  │
│  │  Chat Widget  │      │  (HTML/JS)    │      │   Channels    │  │
│  └───────┬───────┘      └───────┬───────┘      └───────┬───────┘  │
│          │                       │                       │           │
│          └───────────────────────┴───────────────────────┘           │
│                                  │                                   │
│                          HTTP POST/WebSocket                         │
└──────────────────────────────────┼───────────────────────────────────┘
                                   │
                                   ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         BACKEND SERVER                               │
│                        (FastAPI + SQLite)                            │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    API ENDPOINTS                             │   │
│  │                                                              │   │
│  │  Authentication:                                             │   │
│  │  • POST /api/v1/auth/login        (JWT tokens)             │   │
│  │                                                              │   │
│  │  Customer Messages:                                          │   │
│  │  • POST /webchat                   (Receive customer msg)   │   │
│  │  • POST /sms                       (Twilio webhook)         │   │
│  │  • POST /followup                  (Contact forms)          │   │
│  │                                                              │   │
│  │  Admin API:                                                  │   │
│  │  • GET  /admin/api/conversations   (List conversations)     │   │
│  │  • GET  /admin/api/messages        (Get message history)    │   │
│  │  • GET  /admin/api/followups       (Get contact forms)      │   │
│  │  • POST /admin/send                (Send admin message)     │   │
│  │  • POST /admin/api/push-token     ⭐ (Register push token)  │   │
│  │                                                              │   │
│  │  WebSocket:                                                  │   │
│  │  • WS   /admin-ws?token={jwt}      (Admin real-time)       │   │
│  │  • WS   /ws/{user_id}              (Customer real-time)     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    BUSINESS LOGIC                            │   │
│  │                                                              │   │
│  │  • ensure_conversation()     - Create/update conversation   │   │
│  │  • add_message()             - Save message to DB           │   │
│  │  • push_with_admin()         - Broadcast to admin WS        │   │
│  │  • notify_admins_new_message() ⭐ - Send push notifications │   │
│  │  • send_push_notification()  ⭐ - Call Expo Push API       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    DATABASE (SQLite)                         │   │
│  │                                                              │   │
│  │  • conversations    - Active chats (user_id, channel, etc)  │   │
│  │  • messages         - Chat history (user, staff, system)    │   │
│  │  • followups        - Contact forms (name, email, phone)    │   │
│  │  • history          - Archived conversations                │   │
│  │  • users            - Admin/staff credentials               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │               PUSH TOKEN STORAGE (in-memory)                 │   │
│  │                                                              │   │
│  │  admin_push_tokens = {                                       │   │
│  │    "admin@example.com": "ExponentPushToken[xxxxxx]",       │   │
│  │    "staff@example.com": "ExponentPushToken[xxxxxx]",       │   │
│  │  }                                                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
    WebSocket           HTTP API         Push Notifications
        │                   │                   │
        ↓                   ↓                   ↓
┌─────────────────────────────────────────────────────────────────────┐
│                       ADMIN INTERFACES                               │
│                                                                       │
│  ┌─────────────────────────┐    ┌─────────────────────────┐        │
│  │   WEB DASHBOARD          │    │   MOBILE APP            │        │
│  │   (React/Vite)           │    │   (React Native/Expo)   │        │
│  │                          │    │                         │        │
│  │  • Login screen          │    │  • Login screen         │        │
│  │  • Conversation tabs     │    │  • Conversation tabs    │        │
│  │  • Chat interface        │    │  • Chat interface       │        │
│  │  • Bulk actions          │    │  • Push notifications ⭐│        │
│  │  • Export history        │    │  • Sound alerts ⭐       │        │
│  │  • Real-time updates     │    │  • Real-time updates    │        │
│  └─────────────────────────┘    └─────────────────────────┘        │
│                                                                       │
│                      http://localhost:5173                           │
│                      http://localhost:8000                           │
└─────────────────────────────────────────────────────────────────────┘
                                   ↑
                                   │
                          ⭐ Push Notification Flow
                                   │
┌─────────────────────────────────────────────────────────────────────┐
│                   EXPO PUSH NOTIFICATION SERVICE                     │
│                   (https://exp.host/--/api/v2/push/send)            │
│                                                                       │
│  1. Backend sends notification to Expo API                          │
│  2. Expo routes to APNs (iOS) or FCM (Android)                      │
│  3. Notification delivered to device                                │
│  4. Sound alert plays                                                │
│  5. Banner appears on screen                                         │
└─────────────────────────────────────────────────────────────────────┘
```

## Message Flow Diagram

### Scenario: Customer Sends Message

```
┌──────────┐
│ Customer │
└────┬─────┘
     │
     │ 1. Types message in chat widget
     ↓
┌────────────────┐
│ POST /webchat  │
│ {              │
│   user_id,     │
│   channel,     │
│   text         │
│ }              │
└────┬───────────┘
     │
     │ 2. Backend processes
     ↓
┌─────────────────────────────────────────┐
│ ensure_conversation(user_id, channel)   │
│ add_message(user_id, channel, text)     │
└────┬────────────────────────────────────┘
     │
     │ 3. Broadcast to admin dashboards
     ├──────────────────┬──────────────────┐
     │                  │                  │
     ↓                  ↓                  ↓
┌──────────┐    ┌─────────────┐    ┌────────────┐
│ Admin WS │    │ Mobile WS   │    │ Expo Push  │
│ (Web)    │    │ (App)       │    │ Service    │
└──────────┘    └─────────────┘    └────┬───────┘
                                          │
                                          │ 4. Deliver notification
                                          ↓
                                   ┌──────────────┐
                                   │ Admin Phone  │
                                   │              │
                                   │  🔊 Sound!   │
                                   │  📬 Banner   │
                                   └──────────────┘
```

### Scenario: Admin Replies from Mobile

```
┌──────────────┐
│ Admin Mobile │
└────┬─────────┘
     │
     │ 1. Types reply in app
     ↓
┌────────────────┐
│ POST /admin/   │
│      send      │
│ {              │
│   user_id,     │
│   channel,     │
│   text         │
│ }              │
└────┬───────────┘
     │
     │ 2. Backend saves & broadcasts
     ↓
┌─────────────────────────────────┐
│ add_message(user_id, channel,   │
│             "staff", text)      │
└────┬────────────────────────────┘
     │
     │ 3. Broadcast to customer & other admins
     ├──────────────────┬──────────────────┐
     │                  │                  │
     ↓                  ↓                  ↓
┌──────────┐    ┌─────────────┐    ┌────────────┐
│ Customer │    │ Admin Web   │    │ Other      │
│ WS       │    │ Dashboard   │    │ Admin      │
└──────────┘    └─────────────┘    │ Mobile     │
                                    └────────────┘
```

## Mobile App Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   MOBILE APP STRUCTURE                       │
│                   (React Native + Expo)                      │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │                   App.js                            │    │
│  │  • NavigationContainer                              │    │
│  │  • AuthProvider wrapper                             │    │
│  │  • Notification listeners setup                     │    │
│  └───────────────────┬────────────────────────────────┘    │
│                      │                                       │
│                      ↓                                       │
│  ┌────────────────────────────────────────────────────┐    │
│  │          NAVIGATION (React Navigation)              │    │
│  │                                                      │    │
│  │  Stack Navigator:                                    │    │
│  │  ┌──────────────┐  ┌──────────────┐                │    │
│  │  │ LoginScreen  │→ │Conversations │→ ChatScreen    │    │
│  │  │              │  │ (3 Tabs)     │                 │    │
│  │  └──────────────┘  └──────────────┘                │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │            CONTEXTS (State Management)              │    │
│  │                                                      │    │
│  │  AuthContext:                                        │    │
│  │  • user (current user state)                        │    │
│  │  • login(email, password)                           │    │
│  │  • logout()                                         │    │
│  │  • isAuthenticated                                  │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │               SERVICES LAYER                        │    │
│  │                                                      │    │
│  │  ┌────────────────────────────────────────┐        │    │
│  │  │ api.js (HTTP Service)                  │        │    │
│  │  │  • login()                              │        │    │
│  │  │  • fetchOpenConversations()            │        │    │
│  │  │  • fetchEscalatedConversations()       │        │    │
│  │  │  • fetchFollowups()                    │        │    │
│  │  │  • fetchMessages()                     │        │    │
│  │  │  • sendMessage()                       │        │    │
│  │  │  • registerPushToken()                 │        │    │
│  │  │  • fetchWithAuth() - helper            │        │    │
│  │  └────────────────────────────────────────┘        │    │
│  │                                                      │    │
│  │  ┌────────────────────────────────────────┐        │    │
│  │  │ websocket.js (WebSocket Service)       │        │    │
│  │  │  • connect()                            │        │    │
│  │  │  • disconnect()                         │        │    │
│  │  │  • send(data)                           │        │    │
│  │  │  • addListener(callback)                │        │    │
│  │  │  • Auto-reconnect logic                 │        │    │
│  │  │  • Exponential backoff                  │        │    │
│  │  └────────────────────────────────────────┘        │    │
│  │                                                      │    │
│  │  ┌────────────────────────────────────────┐        │    │
│  │  │ notifications.js (Push Service)        │        │    │
│  │  │  • registerForPushNotificationsAsync() │        │    │
│  │  │    - Request permissions                │        │    │
│  │  │    - Get Expo Push Token               │        │    │
│  │  │    - Register with backend             │        │    │
│  │  │  • setupNotificationListeners()        │        │    │
│  │  │    - onNotificationReceived            │        │    │
│  │  │    - onNotificationTapped              │        │    │
│  │  │  • scheduleLocalNotification()         │        │    │
│  │  └────────────────────────────────────────┘        │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │              DEVICE INTEGRATION                     │    │
│  │                                                      │    │
│  │  • AsyncStorage (Token storage)                     │    │
│  │  • Expo Notifications (Push system)                 │    │
│  │  • Native WebSocket (Real-time)                     │    │
│  │  • Device Info (Physical device check)              │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### Authentication Flow

```
┌──────────────┐
│ User enters  │
│ credentials  │
└──────┬───────┘
       │
       ↓
┌──────────────────────────────┐
│ AuthContext.login()          │
│  ↓                            │
│ api.login(email, password)   │
│  ↓                            │
│ POST /api/v1/auth/login      │
└──────┬───────────────────────┘
       │
       ↓
┌──────────────────────────────┐
│ Backend validates & returns: │
│ {                             │
│   access_token: "jwt...",    │
│   token_type: "bearer"       │
│ }                             │
└──────┬───────────────────────┘
       │
       ↓
┌──────────────────────────────┐
│ Store in AsyncStorage:       │
│  - access_token              │
│  - token_type                │
└──────┬───────────────────────┘
       │
       ├─────────────┬─────────────┐
       │             │             │
       ↓             ↓             ↓
┌─────────┐  ┌──────────┐  ┌────────────┐
│ Connect │  │ Register │  │ Set user   │
│ WebSocket│  │ Push     │  │ state      │
│          │  │ Token    │  │            │
└─────────┘  └──────────┘  └────────────┘
```

### Message Flow (Real-time)

```
┌──────────────┐
│ Component    │
│ mounts       │
└──────┬───────┘
       │
       ↓
┌──────────────────────────────┐
│ useEffect(() => {            │
│   loadMessages()             │
│   websocket.addListener()    │
│ })                            │
└──────┬───────────────────────┘
       │
       ├─────────────┬
       │             │
       ↓             ↓
┌─────────────┐  ┌────────────────┐
│ HTTP GET    │  │ WebSocket      │
│ /messages   │  │ Listener       │
│             │  │                │
│ (History)   │  │ (New messages) │
└─────────────┘  └────────────────┘
       │             │
       └─────┬───────┘
             │
             ↓
     ┌───────────────┐
     │ Update state  │
     │ messages[]    │
     └───────────────┘
             │
             ↓
     ┌───────────────┐
     │ Re-render     │
     │ FlatList      │
     └───────────────┘
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   SECURITY LAYERS                        │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  Layer 1: Transport Security                    │    │
│  │  • HTTPS (Production)                           │    │
│  │  • WSS (WebSocket Secure in Production)        │    │
│  └────────────────────────────────────────────────┘    │
│                         ↓                                │
│  ┌────────────────────────────────────────────────┐    │
│  │  Layer 2: Authentication                        │    │
│  │  • JWT tokens with expiration                   │    │
│  │  • Token stored in AsyncStorage (encrypted)     │    │
│  │  • Token included in Authorization header       │    │
│  └────────────────────────────────────────────────┘    │
│                         ↓                                │
│  ┌────────────────────────────────────────────────┐    │
│  │  Layer 3: Authorization                         │    │
│  │  • Role-based access (admin, staff)            │    │
│  │  • require_role() dependency in endpoints      │    │
│  │  • WebSocket auth via token query param       │    │
│  └────────────────────────────────────────────────┘    │
│                         ↓                                │
│  ┌────────────────────────────────────────────────┐    │
│  │  Layer 4: Data Validation                       │    │
│  │  • Pydantic schemas on backend                 │    │
│  │  • Input validation on frontend                │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Scalability Considerations

### Current Architecture (Single Server)
- ✅ Good for: Small to medium deployments
- ✅ Handles: 100s of concurrent users
- ⚠️ Single point of failure

### Future Scaling Options

```
┌─────────────────────────────────────────────────────────┐
│                  SCALABLE ARCHITECTURE                   │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  Load Balancer (nginx, AWS ELB)                │    │
│  └────────────┬────────────────┬──────────────────┘    │
│               │                │                        │
│       ┌───────┴──────┐  ┌─────┴──────┐                │
│       │ Backend #1   │  │ Backend #2 │  ...           │
│       └───────┬──────┘  └─────┬──────┘                │
│               └────────┬───────┘                        │
│                        │                                │
│           ┌────────────┴─────────────┐                 │
│           │                          │                 │
│   ┌───────┴──────┐        ┌─────────┴────────┐       │
│   │ PostgreSQL   │        │ Redis            │       │
│   │ (Replicated) │        │ (Pub/Sub, Cache) │       │
│   └──────────────┘        └──────────────────┘       │
└─────────────────────────────────────────────────────────┘
```

Changes needed:
1. Replace SQLite with PostgreSQL
2. Add Redis for:
   - Pub/Sub (WebSocket scaling)
   - Push token storage
   - Session management
3. Stateless backend servers
4. Load balancer for distribution

## Performance Characteristics

### Mobile App
- **Cold start**: ~2-3 seconds
- **Login**: ~500ms
- **Load conversations**: ~300-500ms
- **Send message**: ~100-200ms (WebSocket)
- **Push notification**: ~1-5 seconds from send to receive

### Backend
- **Message processing**: <50ms
- **WebSocket broadcast**: <10ms
- **Push notification API call**: 100-500ms
- **Database queries**: <10ms (SQLite)

### Network
- **HTTP requests**: Depends on latency
- **WebSocket**: Near-instant (10-50ms)
- **Push delivery**: 1-5 seconds

## Monitoring & Observability

### Current Logging

**Backend**:
```python
print(f"✅ Registered push token for {user_id}")
print(f"📤 Sending push notification to {admin_id}")
print(f"✅ Push notification sent")
```

**Mobile App**:
```javascript
console.log('✅ WebSocket connected');
console.log('📨 WS Message:', data);
console.log('Expo Push Token:', token);
```

### Recommended Additions

1. **Error tracking**: Sentry
2. **Analytics**: Mixpanel, Amplitude
3. **Performance**: New Relic, DataDog
4. **Logs**: CloudWatch, LogRocket

## Deployment Architecture

### Development
```
Developer Machine
├── Backend (localhost:8000)
├── Web Dashboard (localhost:5173)
└── Mobile App (Expo Dev Server)
    └── Physical Device (via Expo Go)
```

### Production
```
Cloud Provider (AWS, DigitalOcean, etc)
├── Backend Server
│   ├── FastAPI app
│   ├── Database
│   └── SSL certificate
├── Static file hosting (Web Dashboard)
└── Mobile Apps
    ├── iOS App Store
    └── Google Play Store
```

## Technology Choices Rationale

| Technology | Why Chosen | Alternatives |
|------------|-----------|--------------|
| React Native | Cross-platform, large ecosystem | Flutter, Native |
| Expo | Simplifies dev, built-in push | Bare React Native |
| FastAPI | Async, WebSocket support, fast | Express, Django |
| SQLite | Simple, no setup, enough for MVP | PostgreSQL, MySQL |
| JWT | Stateless, standard | Session cookies |
| WebSocket | Real-time, bi-directional | Server-Sent Events, Polling |
| Expo Push | Easy integration, free tier | Firebase, OneSignal |

---

**This architecture provides**:
✅ Real-time communication
✅ Push notifications
✅ Scalable design
✅ Security best practices
✅ Good performance
✅ Easy deployment
