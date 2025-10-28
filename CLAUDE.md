# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DWC-Omnichat is a multi-tenant omnichannel chat platform that enables real-time communication between website visitors and support staff through webchat, SMS (Twilio), and admin dashboard interfaces. The system features:

- FastAPI backend with WebSocket support for real-time messaging
- React + Vite admin dashboard with JWT authentication
- SQLite database (local development and Render production)
- Multi-tenant architecture with role-based access control (RBAC)
- Integration capabilities with Twilio, Facebook Messenger

## Architecture

### Backend Structure

The backend is currently **monolithic** (single `server.py` file, ~1271 lines) but follows a clear separation:

- **Authentication**: `auth.py` - JWT-based auth with Bcrypt, multi-user support, RBAC
- **Main API**: `server.py` - All REST endpoints, WebSocket handlers, database operations
- **Analytics**: `analytics.py` - Conversation metrics and KPI tracking
- **Database**: SQLite with manual schema management (migration scripts in `migrate_*.py`)

Key architectural patterns:
- WebSocket connection pooling via `WSManager` class for visitor and admin connections
- Token-based WebSocket authentication for admin connections
- Path-based database configuration (Render's `/data` vs local `./`)
- CORS middleware configured for multiple origins (production + local dev)

### Frontend Structure

React SPA (Single Page Application) located in `admin-frontend/`:

```
admin-frontend/
├── src/
│   ├── main.jsx              # Entry point
│   ├── App.jsx               # React Router v7 setup
│   ├── config.js             # Backend URL configuration
│   ├── fetchWithAuth.js      # Axios wrapper with JWT interceptor
│   └── components/
│       ├── admin/            # Admin dashboard components
│       │   ├── AdminDashboard.jsx   # Main layout + tab management
│       │   ├── ConversationList.jsx # WebSocket-connected conversation list
│       │   ├── ChatBox.jsx          # Message display + send interface
│       │   └── Tabs.jsx             # Tab navigation
│       └── auth/             # Auth components
│           ├── Login.jsx
│           ├── RequireAuth.jsx      # Protected route wrapper
│           └── LogoutButton.jsx
├── vite.config.js           # Vite config with base: '/admin-app/'
└── dist/                    # Built files (served by FastAPI)
```

**Critical**: The frontend is served at `/admin-app` path (not root) via FastAPI's `StaticFiles` mount.

### Database Schema

SQLite database with 8 core tables:
- `tenants` - Multi-tenancy support
- `users` - Staff accounts with roles (admin/staff)
- `conversations` - Chat conversations with channel info
- `messages` - Individual chat messages
- `followups` - User-submitted followup requests
- `history` - Historical data migration
- `events` - Audit log for all actions
- `conversation_metrics` - Analytics data

**Important**: Database path logic differs between environments:
- Render: `/data/handoff.sqlite` (persistent disk)
- Local: `./handoff.sqlite` (project root)

## Initial Setup

### Quick Start (After Devcontainer Rebuild)

Run the automated setup script:

```bash
./setup-dev-environment.sh
```

This script will:
1. ✅ Create Python virtual environment (.venv)
2. ✅ Install all Python dependencies from requirements.txt
3. ✅ Install frontend dependencies (admin-frontend, mobile app)
4. ✅ Optionally install Serena AI assistant
5. ✅ Optionally install SQLite3 CLI tools
6. ✅ Check database initialization
7. ✅ Optionally build frontend
8. ✅ Create .env template if missing
9. ✅ Configure git if needed

**Interactive prompts** allow you to skip optional installations.

### Manual Setup (If Needed)

If you prefer manual setup or the script fails:

```bash
# 1. Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Frontend dependencies
npm install                      # Root (Tailwind)
cd admin-frontend && npm install # Admin dashboard
cd ../dwc-admin-mobile && npm install  # Mobile app (if exists)

# 3. Environment variables
cp .env.example .env  # Then edit .env with your values
# Generate JWT_SECRET: python -c 'import secrets; print(secrets.token_urlsafe(32))'

# 4. Build frontend (optional for dev)
cd admin-frontend && npm run build
```

### Devcontainer Persistence

**What persists across rebuilds:**
- ✅ Your code and git history
- ✅ Configuration files (.context7, .serena/, .env)
- ✅ Database (handoff.sqlite)
- ✅ Node modules and .venv (if using Docker volumes)

**What gets reset:**
- ❌ System-level packages (apt-get installs)
- ❌ Global npm packages (unless in package.json)
- ❌ Shell configurations (unless in Dockerfile)

**Solution**: The setup script handles all reinstallation automatically!

### Dockerfile Customization

To permanently add tools to your devcontainer, edit `.devcontainer/Dockerfile`:

```dockerfile
# Add Python packages
RUN pip install serena-ai pytest black ruff

# Add system packages
RUN apt-get update && apt-get install -y \
  sqlite3 \
  postgresql-client \
  && apt-get clean

# Add npm global packages
RUN npm install -g typescript ts-node
```

Then rebuild the devcontainer to apply changes.

## Common Development Commands

### Backend (FastAPI)

```bash
# Start backend server (development with hot reload)
.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000 --reload

# Alternative: Using start script
./dev.sh

# Python virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\Activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Database operations (manual migrations)
python migrate_schema.py           # Main schema
python migrate_schema_analytics.py # Analytics schema
python migrate_followups_viewed.py # Followup tracking
```

### Frontend (React + Vite)

```bash
# Start frontend dev server (from project root)
cd admin-frontend && npm run dev

# Build for production
cd admin-frontend && npm run build

# Install dependencies
cd admin-frontend && npm install

# Frontend runs on http://localhost:5173/admin-app/
# Vite proxy handles API calls to backend at :8000
```

### Combined Development

```bash
# Terminal 1: Backend
.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd admin-frontend && npm run dev
```

### Testing Chat Widget

Open `test-chat-widget.html` in a browser to test the visitor-facing chat interface. This file contains a standalone widget that connects to the backend via WebSocket.

## API Structure

### Authentication Endpoints

All auth routes are prefixed with `/api/v1/auth` (handled by `auth_router` from `auth.py`):

- `POST /api/v1/auth/login` - Username/password → JWT token (72-hour expiry)
- `GET /api/v1/auth/me` - Get current user info (requires JWT)

### Admin Endpoints

Legacy admin API (not versioned):

- `GET /admin/api/convos` - Get all conversations for logged-in staff
- `POST /admin/api/send` - Send message from admin to visitor
- `GET /admin/api/followups` - Get followup requests
- `POST /admin/api/mark-followup-viewed` - Mark followup as viewed
- `GET /admin/api/history` - Get conversation history
- `PATCH /admin/api/conversations/{id}` - Update conversation
- `GET /health` - Health check endpoint

### Visitor Endpoints

- `POST /webchat` - Send message from visitor (creates conversation if needed)
- `POST /followup` - Submit followup request form
- `POST /handoff/close` - Close conversation

### WebSocket Endpoints

- `WS /ws/{user_id}` - Visitor WebSocket connection (no auth required)
- `WS /admin-ws?token={jwt}` - Admin WebSocket connection (JWT required via query param)

**WebSocket Authentication**: Admin connections validate JWT via `get_websocket_token()` dependency. Visitor connections use `user_id` for identification only.

## Database Operations

### Connecting to Database

```python
# Standard pattern used throughout codebase
import sqlite3
from pathlib import Path
import os

# Use Render's persistent disk if available
if os.path.exists("/data"):
    DB_PATH = "/data/handoff.sqlite"
else:
    DB_PATH = str(Path(__file__).parent / "handoff.sqlite")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
# ... operations ...
conn.commit()
conn.close()
```

### Database Initialization

On startup, `db_init()` function creates all tables and `seed_admin_user()` creates default admin:
- Email: `admin@dwc.com`
- Password: `admin123`
- Tenant ID: 1 (default tenant)

### Schema Changes

**No migration system currently in place**. Schema changes require:
1. Creating a `migrate_*.py` script with ALTER TABLE statements
2. Running script manually on production
3. Updating `db_init()` to include changes for fresh installations

See `migrate_schema.py`, `migrate_schema_analytics.py` as examples.

## Environment Variables

Required environment variables (`.env` file):

```bash
# Security
JWT_SECRET=your-secret-key-here

# Twilio (optional)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_NUMBER=

# Facebook (optional)
FB_PAGE_ACCESS_TOKEN=
FB_VERIFY_TOKEN=

# Configuration
FRONTEND_ORIGIN=https://dwc-omnichat.onrender.com  # or http://localhost:5173 for dev
PUBLIC_BASE_URL=https://dwc-omnichat.onrender.com
AUTO_CLOSE_MINUTES=30
ESCALATE_AFTER_SECONDS=300
```

**Note**: If `FRONTEND_ORIGIN` is not set, CORS defaults to wildcard `["*"]` (insecure for production).

## Deployment (Render)

The project deploys to Render.com using `render.yaml` configuration:

### Build Process

```bash
# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Build frontend
cd admin-frontend
npm install
npm run build  # Outputs to admin-frontend/dist/

# Install Python dependencies
cd ..
pip install -r requirements.txt
```

### Start Command

```bash
uvicorn server:app --host 0.0.0.0 --port $PORT
```

### Critical Configuration

- **Frontend Base Path**: Vite config sets `base: '/admin-app/'` to match FastAPI mount point
- **Static Files**: FastAPI serves `admin-frontend/dist` at `/admin-app` route
- **Database Path**: Uses `/data/handoff.sqlite` on Render (persistent disk)

## WebSocket Architecture

### Connection Management

The `WSManager` class maintains two connection pools:

```python
class WSManager:
    def __init__(self):
        self.visitor_connections: Dict[str, WebSocket] = {}      # user_id -> WebSocket
        self.admin_connections: list[dict] = []                  # List of admin connection info
```

### Message Flow

**Visitor → Admin**:
1. Visitor sends via WebSocket or REST API (`/webchat`)
2. Message stored in database
3. Broadcast to all connected admins via `admin_connections`

**Admin → Visitor**:
1. Admin sends via REST API (`/admin/api/send`)
2. Message stored in database
3. Sent to specific visitor via `visitor_connections[user_id]`

### Connection States

- Visitors auto-reconnect on disconnect
- Admins authenticate via JWT token in WebSocket URL query param
- Stale connections cleaned up on `WebSocketDisconnect` exception

## Security Considerations

### Authentication

- JWT tokens with HS256 algorithm
- 72-hour token expiry (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` in `auth.py`)
- Bcrypt password hashing with auto-generated salt
- Role-based access control (admin/staff roles)

### CORS Configuration

CORS is configured to allow:
- Production domain (`FRONTEND_ORIGIN`)
- Local development (`localhost:5173`, `127.0.0.1:5173`)
- File protocol (`null`) for local testing
- Fallback ports (`:5174`)

### WebSocket Security

- Admin WebSocket requires JWT token validation before accepting connection
- Visitor WebSocket uses user_id for routing (no authentication required by design)
- Token validation uses same `SECRET_KEY` and `ALGORITHM` as REST API

## Common Issues and Solutions

### Admin Dashboard Not Loading

**Symptom**: Blank page or 404 errors for assets

**Solution**: Ensure `vite.config.js` has `base: '/admin-app/'` and frontend is built with `npm run build`

### Database Path Issues

**Symptom**: "Table doesn't exist" errors or fresh database on restart

**Solution**: Check DB_PATH logic - Render uses `/data/`, local uses project root. Ensure persistent disk is configured in Render.

### WebSocket Connection Failures

**Symptom**: Admin dashboard shows "Disconnected" status

**Solutions**:
- Check JWT token validity (72-hour expiry)
- Verify `SECRET_KEY` matches between backend instances
- Ensure WebSocket URL uses correct protocol (`ws://` for local, `wss://` for production)
- Check CORS configuration includes WebSocket origin

### CORS Errors

**Symptom**: "Access-Control-Allow-Origin" errors in browser console

**Solution**: Set `FRONTEND_ORIGIN` environment variable to match frontend URL. Check that origin is included in `allowed_origins` list.

## Code Patterns

### Adding a New API Endpoint

```python
# In server.py

@app.get("/your-endpoint")
async def your_handler(
    current_user: dict = Depends(require_role(["admin", "staff"]))  # Auth required
):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        # Your database operations
        c.execute("SELECT * FROM table")
        results = c.fetchall()
        return {"data": results}
    finally:
        conn.close()
```

### Adding WebSocket Broadcast

```python
# To broadcast to all admins
for admin in ws_manager.admin_connections:
    try:
        await admin["websocket"].send_json({"type": "message", "data": payload})
    except Exception as e:
        logging.error(f"Failed to send to admin: {e}")

# To send to specific visitor
if user_id in ws_manager.visitor_connections:
    try:
        await ws_manager.visitor_connections[user_id].send_json(payload)
    except Exception as e:
        logging.error(f"Failed to send to visitor {user_id}: {e}")
```

### Database Transaction Pattern

```python
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
try:
    c.execute("INSERT INTO table (...) VALUES (?)", (value,))
    conn.commit()
    return {"success": True}
except Exception as e:
    conn.rollback()
    logging.error(f"Database error: {e}")
    raise HTTPException(status_code=500, detail=str(e))
finally:
    conn.close()
```

## Refactoring Plans

See `REFACTORING_PLAN.md` for comprehensive plans to modularize the backend into a proper FastAPI structure with:
- Separate modules for routes, models, schemas, CRUD operations
- Alembic migrations instead of manual schema scripts
- Docker containerization
- Proper testing infrastructure

**Current Priority**: Fix admin dashboard issues before major refactoring.

## AI Coding Assistants

This project uses both Serena and Context 7 to enhance AI-assisted development.

### Context 7 (`.context7`)

**Auto-selected**: ✅ **YES** - Works automatically with all AI assistants

Context 7 is a passive reference file that AI coding assistants automatically read when working on your project.

**Configuration**: `.context7`
- Project overview and architecture summary
- Key files and their purposes
- Development commands and workflows
- API structure and endpoints
- Database schema overview
- Deployment information
- Important code patterns
- Multi-tenant architecture details

**When it helps**:
- Understanding project structure
- Following established patterns
- Using correct commands
- Respecting architectural decisions
- Maintaining consistency

**No action required** - AI assistants automatically reference this file.

### Serena (`.serena/`)

**Auto-selected**: ⚠️ **Depends on your AI tool**

Serena is an active tool with language server integration for advanced code operations.

**Configuration**: `.serena/project.yml`
- Project language: Python (backend) + TypeScript/React (frontend)
- Memory store: `.serena/memories/` (for project-specific context)
- Cache: `.serena/cache/`

**When it helps**:
- Finding symbol definitions and references
- Navigating large codebases
- Refactoring operations (rename, extract)
- Understanding code structure
- Type-aware code navigation

**Availability**:
- If using Serena's CLI: Run `serena` in your terminal
- If using Claude Code with MCP: May require explicit tool invocation
- If using Cursor/other IDEs: Check if Serena integration is enabled

### Usage Recommendations

**For general coding questions**: Context 7 is automatically used - no action needed.

**For complex refactoring**: Explicitly mention if you want Serena's language server features:
- ❌ "Rename this function" (might use basic find/replace)
- ✅ "Use Serena to rename this function across all references"

**For architecture questions**: Context 7 provides immediate context:
- "How do I add a new API endpoint?" - Context 7 shows patterns
- "Where is WebSocket authentication handled?" - Context 7 points to files

**For code navigation**: Both tools complement each other:
- Context 7: High-level "what and where"
- Serena: Precise "show me all references"

### Best Practice

**Start with natural questions** - the right tool will be selected:
- "How do I deploy this?" → Context 7 (deployment info)
- "Show me where this function is called" → Serena (symbol references)
- "What's the database schema?" → Context 7 (schema overview)
- "Refactor this class safely" → Serena (type-aware refactoring)

If you want a specific tool, just mention it: "Check the Context 7 file" or "Use Serena to find all references".


## Additional Resources

- **LOCAL_DEV_GUIDE.md** - Step-by-step local development setup
- **IMPLEMENTATION.md** - SaaS roadmap and feature phases
- **REFACTORING_PLAN.md** - Detailed refactoring strategy
- **MOBILE_APP_SUMMARY.md** - Mobile app integration plans

## Testing

Currently **no automated test suite**. Manual testing workflow:

1. Start backend server
2. Start frontend dev server
3. Open admin dashboard at `http://localhost:5173/admin-app/login`
4. Login with admin credentials
5. Open `test-chat-widget.html` in separate browser tab
6. Send messages and verify real-time delivery

For API testing, use FastAPI's built-in docs at `http://localhost:8000/docs`.
