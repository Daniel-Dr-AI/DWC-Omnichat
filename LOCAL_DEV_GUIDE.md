# 🚀 Local Development Guide - DWC Omnichat

## ✅ Current Status

Both servers are running and ready for testing!

### Backend Server (FastAPI)
- **URL:** http://localhost:8000
- **Status:** ✅ Running
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

### Frontend Server (React + Vite)
- **URL:** http://localhost:5173/admin-app/
- **Login Page:** http://localhost:5173/admin-app/login
- **Status:** ✅ Running

### Test Chat Widget
- **File:** `test-chat-widget.html`
- **How to open:** Open the file directly in your browser, or:
  ```bash
  # Option 1: Open directly in browser
  open test-chat-widget.html  # macOS
  xdg-open test-chat-widget.html  # Linux
  start test-chat-widget.html  # Windows

  # Option 2: Use Python's simple HTTP server
  python3 -m http.server 3000
  # Then visit: http://localhost:3000/test-chat-widget.html
  ```

---

## 🧪 Testing Workflow

### Step 1: Open Admin Dashboard
1. Open your browser and go to: **http://localhost:5173/admin-app/login**
2. Login with:
   - **Email:** admin@dwc.com
   - **Password:** admin123
3. You should see the admin dashboard with conversation tabs

**Troubleshooting if dashboard doesn't load:**
- Make sure you're using the full URL with `/admin-app/` path
- Check browser console (F12) for errors
- Verify the frontend server is running in terminal
- Try clearing browser cache and reloading

### Step 2: Open Chat Widget Test Page
1. Open `test-chat-widget.html` in a **different browser tab or window**
2. You should see:
   - ✅ WebSocket Status: Connected
   - ✅ API Status: Connected
   - A chat widget in the bottom-right corner

### Step 3: Test Real-Time Communication
1. In the **chat widget**, type a message and click "Send"
2. In the **admin dashboard**, you should immediately see:
   - The new conversation appear in the list
   - The message displayed
   - Typing indicators when the visitor is typing

3. From the **admin dashboard**, reply to the conversation
4. The reply should appear in the **chat widget** instantly

---

## 🎨 Customizing the WordPress Chat Widget

The `test-chat-widget.html` file contains a production-ready chat widget that you can integrate into WordPress:

### For WordPress Integration:

1. **Copy the HTML/CSS/JS** from `test-chat-widget.html`

2. **Update the URLs** to point to your production server:
   ```javascript
   const API_URL = 'https://dwc-omnichat.onrender.com';
   const WS_URL = 'wss://dwc-omnichat.onrender.com/ws/' + visitorId;
   ```

3. **Add to WordPress:**

   **Method A: Theme Template**
   - Add to your theme's `footer.php` before `</body>`:
   ```php
   <?php if (is_page('contact') || is_singular('post')) { ?>
       <!-- Include chat widget code here -->
   <?php } ?>
   ```

   **Method B: Custom HTML Block**
   - In WordPress editor, add a "Custom HTML" block
   - Paste the entire widget code

   **Method C: Plugin (Recommended)**
   - Install "Code Snippets" or "Insert Headers and Footers" plugin
   - Add widget code to footer

### Customization Options:

```javascript
// Change widget position
#chatWidget {
    bottom: 20px;   // Distance from bottom
    right: 20px;    // Distance from right (change to 'left' for left side)
}

// Change colors
.chat-header {
    background: linear-gradient(135deg, #YOUR_COLOR_1 0%, #YOUR_COLOR_2 100%);
}

// Change size
#chatWidget {
    width: 380px;   // Widget width
    height: 600px;  // Widget height when open
}

// Auto-open on page load
// Add to the end of the script:
setTimeout(() => {
    document.getElementById('chatWidget').classList.remove('minimized');
    document.getElementById('chatContent').style.display = 'flex';
}, 1000);  // Opens after 1 second
```

---

## 🔧 Development Commands

### Start Servers (if not running)

**Backend:**
```bash
# From project root
.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
# From project root
cd admin-frontend && npm run dev
```

### Stop Servers
- Press `Ctrl+C` in each terminal window

### View Logs
```bash
# Backend logs are shown in the terminal where uvicorn is running
# Frontend logs are shown in the terminal where npm run dev is running
```

### Test API Endpoints

```bash
# Check health
curl http://localhost:8000/health

# Check API info
curl http://localhost:8000/

# Send test message
curl -X POST http://localhost:8000/webchat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user-123", "channel": "webchat", "text": "Hello from curl!"}'

# Login and get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@dwc.com&password=admin123"
```

---

## 🐛 Troubleshooting

### Admin Dashboard Not Loading

**Issue:** Blank page or "Cannot GET /admin-app/login"
- **Solution:** Make sure you're accessing http://localhost:5173/admin-app/login (not http://localhost:8000)

**Issue:** 404 errors in browser console
- **Solution:**
  ```bash
  cd admin-frontend
  npm install
  npm run build
  npm run dev
  ```

**Issue:** "WebSocket connection failed"
- **Solution:** Check that backend server is running on port 8000
- Verify CORS is configured correctly in `.env`

### Chat Widget Issues

**Issue:** WebSocket shows "Disconnected"
- **Solution:** Check that backend server is running
- Look for errors in browser console (F12 → Console tab)
- Check backend logs for WebSocket connection attempts

**Issue:** Messages not appearing in admin dashboard
- **Solution:**
  - Refresh the admin dashboard
  - Check that WebSocket is connected (look for green status)
  - Check backend logs for any errors

**Issue:** "Failed to send message"
- **Solution:**
  - Verify API URL is correct
  - Check CORS settings in `.env`
  - Look at Network tab in browser console (F12)

### Database Issues

**Issue:** "Login failed" even with correct credentials
- **Solution:** Delete and recreate database
  ```bash
  rm handoff.sqlite
  # Restart backend server - it will recreate the DB and seed admin user
  ```

**Issue:** "Table doesn't exist" errors
- **Solution:** The backend automatically creates tables on startup
  - Restart the backend server
  - Check logs for "DB initialized"

---

## 📁 Project Structure

```
DWC-Omnichat/
├── server.py                    # FastAPI backend
├── auth.py                      # Authentication logic
├── .env                         # Environment variables
├── test-chat-widget.html        # Chat widget test page
├── admin-frontend/              # React admin dashboard
│   ├── src/
│   │   ├── components/
│   │   │   ├── admin/           # Admin components
│   │   │   │   ├── AdminDashboard.jsx
│   │   │   │   └── Login.jsx
│   │   │   └── auth/            # Auth components
│   │   ├── App.jsx              # Main React app
│   │   └── config.js            # API configuration
│   ├── dist/                    # Built files (gitignored in dev)
│   └── package.json
├── handoff.sqlite               # SQLite database (auto-created)
└── requirements.txt             # Python dependencies
```

---

## 🚢 Deploying to Production

When you're ready to deploy changes to Render:

```bash
# 1. Build the frontend
cd admin-frontend
npm run build

# 2. Commit changes
git add .
git commit -m "Your commit message"

# 3. Push to GitHub (Render auto-deploys)
git push origin main
```

Render will automatically:
1. Pull the latest code
2. Install Python dependencies
3. Build the React frontend
4. Start the server

---

## 💡 Tips

1. **Hot Reload:** Both servers support hot reload - just save your files and changes appear automatically

2. **Browser Console:** Keep F12 open while testing to see WebSocket messages and errors

3. **Multiple Chat Windows:** You can open `test-chat-widget.html` in multiple browser tabs to simulate multiple visitors

4. **Network Tab:** Use browser's Network tab (F12 → Network) to inspect API calls and WebSocket frames

5. **Database Inspection:** Use DB Browser for SQLite to view database contents:
   ```bash
   # Install DB Browser for SQLite
   # Then open handoff.sqlite
   ```

---

## 🎯 Next Steps

1. ✅ Test the chat widget and admin dashboard working together
2. ✅ Customize the chat widget appearance
3. ✅ Add the widget to your WordPress site
4. ✅ Test with real users
5. ✅ Configure Twilio for SMS/WhatsApp (optional)

---

## 📞 Admin Dashboard Features

Once logged in, you can:
- ✅ View all active conversations in real-time
- ✅ Send messages to visitors
- ✅ See typing indicators
- ✅ View conversation history
- ✅ See followup requests
- ✅ Manage escalated conversations

---

## 🔐 Security Notes

**For Development:**
- Default admin password: `admin123`
- CORS is configured for localhost

**For Production:**
- Change admin password immediately
- Update CORS settings in `.env`
- Use HTTPS/WSS for secure connections
- Set strong JWT_SECRET in environment variables

---

Need help? Check the logs in both terminal windows for error messages!
