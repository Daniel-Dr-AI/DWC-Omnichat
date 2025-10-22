# DWC-Omnichat Refactoring Plan

**Document Version:** 1.0
**Date:** 2025-01-22
**Status:** Draft

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Architecture Analysis](#current-architecture-analysis)
3. [Best Practices Comparison](#best-practices-comparison)
4. [Critical Issues](#critical-issues)
5. [Refactoring Phases](#refactoring-phases)
6. [Implementation Details](#implementation-details)
7. [Migration Strategy](#migration-strategy)
8. [Testing Strategy](#testing-strategy)
9. [Deployment Plan](#deployment-plan)

---

## Executive Summary

### Current State
The DWC-Omnichat application is a functional FastAPI + React chat platform with WebSocket support, JWT authentication, and multi-tenant architecture. However, it suffers from architectural issues that will impede scalability, maintainability, and team collaboration.

### Key Problems
- **Monolithic backend**: 814-line `server.py` with no separation of concerns
- **Missing admin dashboard assets**: Vite base path not configured for `/admin-app` mount
- **No migrations system**: Database schema changes are manual and error-prone
- **Committed build artifacts**: `dist/` in version control (anti-pattern)
- **No modular structure**: All code in root directory

### Goals
1. **Immediate**: Fix admin dashboard 404 issue (1 day)
2. **Short-term**: Modularize backend into proper FastAPI structure (1 week)
3. **Medium-term**: Add Docker, migrations, testing (2 weeks)
4. **Long-term**: Implement CI/CD, monitoring, and advanced features (ongoing)

---

## Current Architecture Analysis

### Project Structure (As-Is)

```
DWC-Omnichat/
├── Backend (Python/FastAPI) - Root Level
│   ├── server.py                 # 814 lines - MONOLITHIC ⚠️
│   ├── auth.py                   # 159 lines - Auth module
│   ├── analytics.py              # Analytics functionality
│   ├── migrate_schema.py         # Schema definitions (not called) ⚠️
│   ├── migrate_schema_analytics.py
│   └── requirements.txt
│
├── Frontend (React/Vite)
│   └── admin-frontend/
│       ├── src/
│       │   ├── main.jsx
│       │   ├── App.jsx
│       │   ├── config.js
│       │   ├── fetchWithAuth.js
│       │   └── components/
│       │       ├── admin/       # Flat structure ⚠️
│       │       └── auth/
│       ├── dist/                # Built files (committed) ⚠️
│       ├── package.json
│       ├── vite.config.js       # ⚠️ MISSING BASE PATH
│       └── tailwind.config.js
│
├── Database
│   ├── handoff.sqlite           # Local development
│   └── /data/handoff.sqlite     # Render production
│
├── Deployment
│   ├── render.yaml
│   ├── .env
│   └── Dockerfile               # ❌ MISSING
│
├── Scripts (PowerShell)
│   ├── dwc.ps1
│   ├── reset-db.ps1
│   └── restart-server.ps1
│
└── Static Assets
    ├── chatbot.js               # Visitor widget
    ├── chatbot.min.js
    ├── test-chatbot-local.html
    └── test_websocket.html
```

### File Analysis

#### 1. server.py (814 lines)

**Purpose**: Main FastAPI application with all endpoints, WebSocket handlers, and business logic.

**Key Components**:
```python
# Database
def db_init()                          # Creates 7 tables
def seed_admin_user()                  # Seeds default admin

# WebSocket
class WSManager                        # Connection pool manager
async def get_websocket_token()        # JWT validation for WS
@app.websocket("/ws/{user_id}")        # Visitor WebSocket
@app.websocket("/admin-ws")            # Admin WebSocket (authenticated)

# API Endpoints (26 total)
@app.get("/")                          # API info
@app.get("/health")                    # Health check
@app.get("/admin")                     # Legacy admin template
@app.post("/api/v1/auth/login")        # Via auth_router
@app.get("/admin/api/convos")          # Get conversations
@app.post("/admin/api/send")           # Send admin message
@app.post("/webchat")                  # Visitor message
@app.post("/sms")                      # Twilio webhook
@app.post("/followup")                 # Followup form
@app.post("/handoff/close")            # Close conversation
# ... 16 more endpoints

# Background Tasks
async def escalation_loop()            # Escalate old conversations

# Startup
@app.on_event("startup")
async def startup_tasks()
```

**Issues**:
- ❌ Violates Single Responsibility Principle
- ❌ No separation between routes, business logic, and data access
- ❌ Difficult to test individual components
- ❌ DB_PATH defined twice (lines 27-30, 127-130)
- ❌ Mixed concerns: Twilio, WebSocket, REST API, templates
- ❌ No API versioning structure
- ❌ Hard to onboard new developers

#### 2. auth.py (159 lines)

**Purpose**: Authentication and authorization module.

**Key Components**:
```python
# Pydantic Models
class Token(BaseModel)
class TokenData(BaseModel)
class UserOut(BaseModel)

# Security Functions
def create_access_token()              # JWT generation (HS256, 72h expiry)
def verify_password()                  # Bcrypt verification
def get_user_by_email()                # User lookup with error handling
def get_current_user()                 # JWT validation dependency
def require_role(roles)                # RBAC dependency factory
def log_event()                        # Audit logging

# API Router
router = APIRouter(prefix="/api/v1/auth")

@router.post("/login")                 # Username/password → JWT
@router.get("/me")                     # Get current user info
```

**Recently Improved** ✅:
- Added comprehensive error handling
- Uses `get_db_path()` for environment-aware database path
- Proper logging with structured messages
- Module-level password context (more efficient)

**Missing Features** ❌:
- No refresh token support
- No password reset flow
- No email verification
- No OAuth2/social login
- No rate limiting on login endpoint
- No account lockout after failed attempts

#### 3. admin-frontend/ (React + Vite + Tailwind)

**Purpose**: Admin dashboard for managing conversations.

**Component Structure**:
```
src/
├── main.jsx                          # Entry point (ReactDOM.render)
├── App.jsx                           # Router setup (React Router v6)
├── config.js                         # Backend URL configuration
├── fetchWithAuth.js                  # Axios wrapper with JWT interceptor
│
├── components/
│   ├── admin/
│   │   ├── AdminDashboard.jsx       # Main layout + tab management
│   │   ├── ConversationList.jsx     # Conv list + WebSocket connection
│   │   ├── ConversationList1.jsx    # ⚠️ Duplicate/unused?
│   │   ├── ChatBox.jsx              # Message display + send interface
│   │   └── Tabs.jsx                 # Tab navigation component
│   │
│   └── auth/
│       ├── RequireAuth.jsx          # Protected route wrapper
│       └── LogoutButton.jsx         # Logout with localStorage clear
│
└── index.css                         # Tailwind imports
```

**Critical Issue** 🔴:
```javascript
// vite.config.js (CURRENT - BROKEN)
export default defineConfig({
  plugins: [react()],
  // ❌ NO BASE PATH - causes assets to load from root instead of /admin-app
})

// Generated index.html references:
<script type="module" crossorigin src="/assets/index-ChHSWmDw.js"></script>
// Should be: /admin-app/assets/index-ChHSWmDw.js

// Result:
// ✅ https://dwc-omnichat.onrender.com/admin-app/ → 200 OK (index.html)
// ❌ https://dwc-omnichat.onrender.com/assets/index-ChHSWmDw.js → 404 Not Found
```

**Other Issues**:
- ❌ `dist/` committed to Git (232KB of compiled JS)
- ❌ Flat component structure (no `pages/`, `hooks/`, `stores/`)
- ❌ No state management (useState scattered everywhere)
- ❌ Inline styles mixed with Tailwind classes
- ❌ No loading states or error boundaries
- ❌ No TypeScript (type safety)

#### 4. Database Schema

**Tables Created** (in `db_init()`):

```sql
-- Multi-tenancy
CREATE TABLE tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Users & Authentication
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'staff',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

-- Audit Logging
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    tenant_id INTEGER,
    type TEXT NOT NULL,
    payload TEXT,
    ts TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

-- Chat Conversations
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    channel TEXT,
    assigned_staff TEXT,
    open INTEGER,
    updated_at TEXT,
    patience_sent INTEGER DEFAULT 0,
    final_sent INTEGER DEFAULT 0
);

-- Chat Messages
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    channel TEXT,
    sender TEXT,
    text TEXT,
    ts TEXT
);

-- Followup Requests
CREATE TABLE followups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    channel TEXT,
    name TEXT,
    contact TEXT,
    message TEXT,
    ts TEXT
);

-- Historical Data Migration
CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    channel TEXT,
    name TEXT,
    contact TEXT,
    message TEXT,
    ts TEXT,
    migrated_at TEXT
);
```

**Issues**:
- ❌ No indexes (performance bottleneck)
- ❌ No foreign key enforcement (SQLite pragma not set)
- ❌ Mixed TEXT/INTEGER IDs (conversations.user_id is TEXT, users.id is INTEGER)
- ❌ No created_by/updated_by fields (audit trail)
- ❌ TEXT columns have no length limits (potential abuse)
- ❌ No composite indexes for common queries
- ❌ No database migrations (Alembic)
- ❌ Timestamps as TEXT instead of DATETIME

**Recommended Indexes**:
```sql
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_conversations_user_channel ON conversations(user_id, channel);
CREATE INDEX idx_conversations_open ON conversations(open);
CREATE INDEX idx_messages_user_channel ON messages(user_id, channel);
CREATE INDEX idx_events_user_tenant ON events(user_id, tenant_id);
CREATE INDEX idx_events_ts ON events(ts);
```

---

## Best Practices Comparison

### FastAPI Official Full-Stack Template

**Source**: https://github.com/fastapi/full-stack-fastapi-template

**Structure**:
```
project/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # Application factory
│   │   │
│   │   ├── api/
│   │   │   ├── dependencies.py  # Shared dependencies (auth, db)
│   │   │   └── v1/              # API version 1
│   │   │       ├── __init__.py
│   │   │       ├── auth.py
│   │   │       ├── users.py
│   │   │       ├── items.py
│   │   │       └── ...
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py        # Settings (Pydantic BaseSettings)
│   │   │   ├── security.py      # Password hashing, JWT
│   │   │   └── db.py            # Database session management
│   │   │
│   │   ├── models/              # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   └── item.py
│   │   │
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   └── item.py
│   │   │
│   │   ├── crud/                # Database operations
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── user.py
│   │   │   └── item.py
│   │   │
│   │   └── tests/               # Unit and integration tests
│   │       ├── __init__.py
│   │       ├── conftest.py
│   │       └── test_*.py
│   │
│   ├── alembic/                 # Database migrations
│   │   ├── versions/
│   │   └── env.py
│   │
│   ├── scripts/
│   │   ├── prestart.sh          # Run before app starts
│   │   └── test.sh              # Run tests
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── pages/               # Route pages
│   │   ├── components/          # Reusable UI components
│   │   ├── hooks/               # Custom React hooks
│   │   ├── services/            # API clients (axios)
│   │   ├── stores/              # State management (Zustand/Redux)
│   │   └── utils/               # Helper functions
│   │
│   ├── public/
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── Dockerfile                   # Multi-stage build
├── docker-compose.yml           # Local development stack
├── .env.example                 # Environment variable template
├── .gitignore
└── README.md
```

**Key Differences from DWC-Omnichat**:

| Feature | DWC-Omnichat | FastAPI Template |
|---------|--------------|------------------|
| **Backend structure** | Monolithic `server.py` | Modular `app/` package |
| **API versioning** | None | `api/v1/`, `api/v2/` |
| **Database operations** | Inline SQL in routes | Separate `crud/` layer |
| **Migrations** | Manual schema scripts | Alembic migrations |
| **Configuration** | `.env` + hardcoded | `core/config.py` (Pydantic) |
| **Testing** | None | `tests/` with pytest |
| **Docker** | None | Multi-stage Dockerfile |
| **Frontend state** | Local useState | Centralized stores |
| **Build artifacts** | Committed to Git | In `.gitignore` |

---

## Critical Issues

### 🔴 Priority 1: Immediate (Blocking Users)

#### Issue #1: Admin Dashboard Assets 404
**Problem**: Vite base path not configured, causing asset loading failures.

**Impact**:
- Admin dashboard loads blank white page
- Console errors: `Failed to load resource: 404`
- All `/assets/*.js` and `/assets/*.css` requests fail

**Root Cause**:
```javascript
// vite.config.js
export default defineConfig({
  plugins: [react()],
  // ❌ Missing: base: '/admin-app/'
})
```

**Fix**:
```javascript
// vite.config.js
export default defineConfig({
  plugins: [react()],
  base: '/admin-app/',  // ✅ Assets will load from /admin-app/assets/
})
```

**Effort**: 5 minutes
**Risk**: Low (only affects asset paths)
**Rollback**: Revert commit

---

### ⚠️ Priority 2: High (Architecture)

#### Issue #2: Monolithic server.py
**Problem**: All code in single 814-line file.

**Impact**:
- Difficult to navigate and understand
- Merge conflicts when multiple developers work
- Can't test individual components
- Slow IDE performance
- Tight coupling between concerns

**Solution**: Refactor into modular structure (see Phase 2)

**Effort**: 1 week
**Risk**: Medium (extensive changes)

---

#### Issue #3: No Database Migrations
**Problem**: Schema changes made by editing `db_init()` directly.

**Impact**:
- Can't roll back schema changes
- Production databases get out of sync
- No history of schema evolution
- Deployment requires manual SQL

**Solution**: Implement Alembic migrations

**Effort**: 2 days
**Risk**: Medium (requires data migration)

---

#### Issue #4: Build Artifacts in Git
**Problem**: `admin-frontend/dist/` (232KB) committed to version control.

**Impact**:
- Repository bloat (every rebuild adds 232KB)
- Merge conflicts on auto-generated files
- Git history filled with compiled code
- Code review includes minified JS

**Solution**: Build frontend during Render deployment

**Effort**: 4 hours
**Risk**: Medium (requires Render config change)

---

### ℹ️ Priority 3: Medium (Features & Quality)

#### Issue #5: No Refresh Tokens
**Impact**: Users logged out after 72 hours, no seamless re-auth

#### Issue #6: No Password Reset
**Impact**: Locked-out users require admin intervention

#### Issue #7: No Email Verification
**Impact**: Anyone can create accounts with fake emails

#### Issue #8: No Rate Limiting
**Impact**: API vulnerable to brute force attacks

#### Issue #9: No Logging Middleware
**Impact**: Difficult to debug production issues

#### Issue #10: No Tests
**Impact**: Regressions not caught before deployment

---

## Refactoring Phases

### Phase 1: Fix Admin Dashboard (1 Day) 🔥

**Goal**: Make admin dashboard functional on `/admin-app`

**Changes**:
1. Update `admin-frontend/vite.config.js`:
   ```javascript
   export default defineConfig({
     plugins: [react()],
     base: '/admin-app/',
     build: {
       outDir: 'dist',
       assetsDir: 'assets',
       manifest: true
     }
   })
   ```

2. Rebuild frontend:
   ```bash
   cd admin-frontend
   npm run build
   ```

3. Verify locally:
   ```bash
   # Start backend
   uvicorn server:app --reload

   # Visit http://localhost:8000/admin-app
   # Assets should load from /admin-app/assets/
   ```

4. Commit and deploy:
   ```bash
   git add admin-frontend/vite.config.js admin-frontend/dist/
   git commit -m "Fix admin dashboard base path for /admin-app mount"
   git push origin main
   ```

**Success Criteria**:
- ✅ Admin dashboard loads at https://dwc-omnichat.onrender.com/admin-app
- ✅ No 404 errors in browser console
- ✅ Can log in and see conversations
- ✅ WebSocket connection established

**Rollback Plan**: Revert commit if issues

---

### Phase 2: Modularize Backend (1 Week) 🏗️

**Goal**: Split monolithic `server.py` into proper FastAPI structure

**New Structure**:
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                   # Application factory
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py       # get_db, get_current_user, etc.
│   │   │
│   │   └── v1/
│   │       ├── __init__.py       # APIRouter aggregation
│   │       ├── auth.py           # Login, logout, /me
│   │       ├── conversations.py  # List, get, close conversations
│   │       ├── messages.py       # Send/receive messages
│   │       ├── websockets.py     # WebSocket endpoints
│   │       ├── admin.py          # Admin-specific endpoints
│   │       ├── webhooks.py       # Twilio, external webhooks
│   │       └── health.py         # Health check, root endpoint
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py             # Settings (Pydantic BaseSettings)
│   │   ├── security.py           # Password hashing, JWT utils
│   │   ├── database.py           # Database session, connection
│   │   └── websocket_manager.py  # WebSocket connection pool
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py               # User, Tenant
│   │   ├── conversation.py       # Conversation, Message
│   │   └── event.py              # Event (audit log)
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py               # UserCreate, UserRead, UserUpdate
│   │   ├── conversation.py       # ConversationRead, MessageCreate
│   │   ├── auth.py               # Token, TokenData, LoginRequest
│   │   └── websocket.py          # WebSocket message schemas
│   │
│   ├── crud/
│   │   ├── __init__.py
│   │   ├── base.py               # CRUDBase class
│   │   ├── user.py               # User CRUD operations
│   │   └── conversation.py       # Conversation CRUD operations
│   │
│   └── services/
│       ├── __init__.py
│       ├── escalation.py         # Background escalation logic
│       └── twilio.py             # Twilio SMS integration
│
├── alembic/
│   ├── versions/
│   └── env.py
│
├── scripts/
│   ├── init_db.py                # Database initialization
│   └── seed_admin.py             # Create default admin
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   ├── test_auth.py
│   ├── test_conversations.py
│   └── test_websockets.py
│
├── requirements.txt
└── alembic.ini
```

**Migration Steps**:

1. **Create directory structure**:
   ```bash
   mkdir -p backend/app/{api/v1,core,models,schemas,crud,services}
   mkdir -p backend/alembic/versions
   mkdir -p backend/scripts
   mkdir -p backend/tests
   touch backend/app/__init__.py
   # ... create all __init__.py files
   ```

2. **Move code from server.py to modules**:

   **app/main.py**:
   ```python
   from fastapi import FastAPI
   from fastapi.middleware.cors import CORSMiddleware
   from fastapi.staticfiles import StaticFiles
   from pathlib import Path

   from app.api.v1 import api_router
   from app.core.config import settings
   from app.core.database import engine
   from app.models import Base

   def create_app() -> FastAPI:
       app = FastAPI(
           title=settings.PROJECT_NAME,
           openapi_url=f"{settings.API_V1_STR}/openapi.json"
       )

       # CORS
       app.add_middleware(
           CORSMiddleware,
           allow_origins=settings.BACKEND_CORS_ORIGINS,
           allow_credentials=True,
           allow_methods=["*"],
           allow_headers=["*"],
       )

       # API routes
       app.include_router(api_router, prefix=settings.API_V1_STR)

       # Static files (admin dashboard)
       if Path("admin-frontend/dist").exists():
           app.mount(
               "/admin-app",
               StaticFiles(directory="admin-frontend/dist", html=True),
               name="admin-app"
           )

       return app

   app = create_app()

   @app.on_event("startup")
   async def startup():
       # Create tables (replace with Alembic migrations)
       Base.metadata.create_all(bind=engine)
   ```

   **app/core/config.py**:
   ```python
   from pydantic_settings import BaseSettings
   from typing import List

   class Settings(BaseSettings):
       PROJECT_NAME: str = "DWC Omnichat"
       API_V1_STR: str = "/api/v1"

       # Database
       DATABASE_URL: str = "sqlite:///./handoff.sqlite"

       # Security
       SECRET_KEY: str
       ALGORITHM: str = "HS256"
       ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 3

       # CORS
       BACKEND_CORS_ORIGINS: List[str] = [
           "http://localhost:5173",
           "https://dwc-omnichat.onrender.com"
       ]

       # Twilio
       TWILIO_ACCOUNT_SID: str | None = None
       TWILIO_AUTH_TOKEN: str | None = None
       TWILIO_NUMBER: str | None = None

       class Config:
           env_file = ".env"
           case_sensitive = True

   settings = Settings()
   ```

   **app/api/v1/__init__.py**:
   ```python
   from fastapi import APIRouter
   from .auth import router as auth_router
   from .conversations import router as conversations_router
   from .messages import router as messages_router
   from .websockets import router as websockets_router
   from .admin import router as admin_router
   from .webhooks import router as webhooks_router
   from .health import router as health_router

   api_router = APIRouter()
   api_router.include_router(health_router, tags=["health"])
   api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
   api_router.include_router(conversations_router, prefix="/conversations", tags=["conversations"])
   api_router.include_router(messages_router, prefix="/messages", tags=["messages"])
   api_router.include_router(websockets_router, tags=["websockets"])
   api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
   api_router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
   ```

3. **Test incrementally**:
   ```bash
   # Test each module as you migrate it
   pytest backend/tests/test_auth.py
   pytest backend/tests/test_conversations.py
   ```

4. **Update imports in frontend**:
   ```javascript
   // config.js
   const BACKEND_URL = window.DWC_BACKEND_URL || 'http://localhost:8000';
   export const API_BASE_URL = `${BACKEND_URL}/api/v1`;  // ✅ Add /api/v1
   ```

**Effort**: 40 hours (5 days)
**Risk**: High (extensive changes, potential downtime)
**Testing**: Unit tests for each module + integration tests
**Rollback**: Keep `server.py` as backup, switch WSGI command if issues

---

### Phase 3: Add Migrations & Docker (2 Weeks) 🐳

**Goal**: Database migrations, Docker support, CI/CD

**3.1: Alembic Migrations (3 days)**

1. **Install Alembic**:
   ```bash
   pip install alembic
   alembic init alembic
   ```

2. **Configure `alembic/env.py`**:
   ```python
   from app.core.config import settings
   from app.models import Base

   config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
   target_metadata = Base.metadata
   ```

3. **Create initial migration**:
   ```bash
   alembic revision --autogenerate -m "Initial schema"
   alembic upgrade head
   ```

4. **Update startup to use migrations**:
   ```python
   # Remove from startup:
   # Base.metadata.create_all(bind=engine)

   # Add to scripts/prestart.sh:
   alembic upgrade head
   ```

**3.2: Docker Multi-Stage Build (2 days)**

**Dockerfile**:
```dockerfile
# Stage 1: Build frontend
FROM node:18-alpine AS frontend
WORKDIR /frontend
COPY admin-frontend/package*.json ./
RUN npm ci
COPY admin-frontend/ ./
RUN npm run build

# Stage 2: Python application
FROM python:3.11-slim
WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY alembic.ini ./
COPY scripts/ ./scripts/

# Copy built frontend from stage 1
COPY --from=frontend /frontend/dist ./admin-frontend/dist

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run migrations and start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
```

**docker-compose.yml** (Local Development):
```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:////data/handoff.sqlite
      - SECRET_KEY=${SECRET_KEY}
      - TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID}
      - TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN}
    volumes:
      - ./backend:/app/backend
      - ./data:/data
    command: uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    image: node:18-alpine
    working_dir: /app
    volumes:
      - ./admin-frontend:/app
    command: npm run dev
    ports:
      - "5173:5173"
```

**Render Deployment**:
Update `render.yaml`:
```yaml
services:
  - type: web
    name: dwc-omnichat
    env: docker  # ✅ Change from python to docker
    dockerfilePath: ./Dockerfile
    dockerContext: .
    envVars:
      # ... existing env vars
```

**3.3: GitHub Actions CI/CD (3 days)**

**.github/workflows/test.yml**:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests
      run: pytest backend/tests/ --cov=backend

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

**.github/workflows/deploy.yml**:
```yaml
name: Deploy to Render

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
    - name: Trigger Render deployment
      run: |
        curl -X POST ${{ secrets.RENDER_DEPLOY_HOOK }}
```

**Effort**: 80 hours (2 weeks)
**Risk**: Medium (Docker adds complexity)
**Benefits**: Reproducible builds, easier local development

---

### Phase 4: Testing & Monitoring (Ongoing) 🧪

**4.1: Unit Tests**

**tests/conftest.py**:
```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

**tests/test_auth.py**:
```python
def test_create_user(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpass123"
        }
    )
    assert response.status_code == 201
    assert "id" in response.json()

def test_login(client, db):
    # Create user
    from app.crud.user import create_user
    from app.schemas.user import UserCreate
    user = create_user(
        db,
        UserCreate(email="test@example.com", username="testuser", password="testpass123")
    )

    # Login
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "testpass123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
```

**4.2: Monitoring & Logging**

**Install Sentry**:
```bash
pip install sentry-sdk[fastapi]
```

**app/main.py**:
```python
import sentry_sdk

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1
    )
```

**Add structured logging**:
```python
import logging
import sys
from pythonjsonlogger import jsonlogger

logHandler = logging.StreamHandler(sys.stdout)
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logging.root.addHandler(logHandler)
logging.root.setLevel(logging.INFO)
```

---

## Implementation Details

### File-by-File Migration Checklist

#### From server.py → Multiple Files

| Current (server.py) | New Location | Lines | Status |
|---------------------|--------------|-------|--------|
| `db_init()` | `app/core/database.py` or `scripts/init_db.py` | 82 | ⏳ TODO |
| `seed_admin_user()` | `scripts/seed_admin.py` | 43 | ⏳ TODO |
| `WSManager` | `app/core/websocket_manager.py` | ~50 | ⏳ TODO |
| `get_websocket_token()` | `app/api/dependencies.py` | 39 | ⏳ TODO |
| `@app.get("/")` | `app/api/v1/health.py` | 10 | ⏳ TODO |
| `@app.get("/health")` | `app/api/v1/health.py` | 4 | ⏳ TODO |
| `@app.get("/admin")` | `app/api/v1/admin.py` | 5 | ⏳ TODO |
| `/admin/api/*` endpoints | `app/api/v1/admin.py` | ~200 | ⏳ TODO |
| `@app.post("/webchat")` | `app/api/v1/messages.py` | 50 | ⏳ TODO |
| `@app.post("/sms")` | `app/api/v1/webhooks.py` | 80 | ⏳ TODO |
| `@app.websocket("/ws/*")` | `app/api/v1/websockets.py` | 100 | ⏳ TODO |
| `escalation_loop()` | `app/services/escalation.py` | 30 | ⏳ TODO |

#### From auth.py → Multiple Files

| Current (auth.py) | New Location | Lines | Status |
|-------------------|--------------|-------|--------|
| Pydantic models | `app/schemas/auth.py` | 30 | ⏳ TODO |
| Security functions | `app/core/security.py` | 80 | ⏳ TODO |
| Router | `app/api/v1/auth.py` | 40 | ⏳ TODO |

---

## Migration Strategy

### Pre-Migration Checklist

- [ ] **Backup production database**
  ```bash
  # On Render, via SSH or dashboard
  cp /data/handoff.sqlite /data/handoff.sqlite.backup
  ```

- [ ] **Create feature branch**
  ```bash
  git checkout -b refactor/modular-backend
  ```

- [ ] **Document current API endpoints**
  - Run `http://localhost:8000/docs`
  - Export OpenAPI spec: `curl http://localhost:8000/openapi.json > openapi.backup.json`

- [ ] **Set up local testing environment**
  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  pip install pytest pytest-cov
  ```

### Migration Process

#### Step 1: Create New Structure (No Code Changes Yet)
```bash
# Create directories
mkdir -p backend/app/{api/v1,core,models,schemas,crud,services}
mkdir -p backend/alembic/versions
mkdir -p backend/scripts
mkdir -p backend/tests

# Create __init__.py files
find backend -type d -exec touch {}/__init__.py \;

# Copy server.py as backup
cp server.py server.py.backup
```

#### Step 2: Move Code Module by Module

**Order** (least to most dependencies):
1. Configuration (`core/config.py`)
2. Models (`models/`)
3. Schemas (`schemas/`)
4. Database (`core/database.py`)
5. Security (`core/security.py`)
6. CRUD operations (`crud/`)
7. Dependencies (`api/dependencies.py`)
8. API routes (`api/v1/`)
9. Main app (`main.py`)

**For each module**:
1. Create new file
2. Copy relevant code
3. Update imports
4. Write unit test
5. Run test to verify
6. Commit

**Example - Moving config**:
```bash
# 1. Create file
touch backend/app/core/config.py

# 2. Copy environment variables logic
cat > backend/app/core/config.py << 'EOF'
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Copy from server.py lines 1-50
    ...

settings = Settings()
EOF

# 3. Update imports in server.py
# from os import getenv
# + from app.core.config import settings

# 4. Write test
cat > backend/tests/test_config.py << 'EOF'
def test_settings_loaded():
    from app.core.config import settings
    assert settings.PROJECT_NAME == "DWC Omnichat"
EOF

# 5. Run test
pytest backend/tests/test_config.py

# 6. Commit
git add backend/app/core/config.py backend/tests/test_config.py
git commit -m "refactor: move configuration to core/config.py"
```

#### Step 3: Update Frontend API URLs

**admin-frontend/src/config.js**:
```javascript
// Before
const BACKEND_URL = window.DWC_BACKEND_URL || 'http://localhost:8000';

// After
const BACKEND_URL = window.DWC_BACKEND_URL || 'http://localhost:8000';
export const API_BASE_URL = `${BACKEND_URL}/api/v1`;  // ✅ Add version prefix
```

**Update all fetch calls**:
```javascript
// Before
fetch(`${BACKEND_URL}/admin/api/convos`, ...)

// After
import { API_BASE_URL } from './config';
fetch(`${API_BASE_URL}/admin/convos`, ...)  // Note: /admin/api → /api/v1/admin
```

#### Step 4: Test Each Endpoint

**Create test script**:
```bash
# test_endpoints.sh
#!/bin/bash

BASE_URL="http://localhost:8000/api/v1"
TOKEN=""

echo "Testing health endpoint..."
curl -f $BASE_URL/health || exit 1

echo "Testing login..."
RESPONSE=$(curl -X POST $BASE_URL/auth/login \
  -d "username=admin@dwc.com&password=admin123")
TOKEN=$(echo $RESPONSE | jq -r '.access_token')

echo "Testing authenticated endpoint..."
curl -f -H "Authorization: Bearer $TOKEN" $BASE_URL/admin/convos || exit 1

echo "✅ All endpoints working"
```

#### Step 5: Deploy to Staging

**Option A: Use Render Preview Environments**
```bash
# Create pull request
git push origin refactor/modular-backend
# Render auto-creates preview URL
```

**Option B: Deploy to separate Render service**
```yaml
# render-staging.yaml
services:
  - type: web
    name: dwc-omnichat-staging
    env: python
    branch: refactor/modular-backend
    # ... same config
```

#### Step 6: Smoke Test Production

**After deployment**:
1. ✅ Health check: `curl https://dwc-omnichat.onrender.com/api/v1/health`
2. ✅ Login: Test with admin credentials
3. ✅ Admin dashboard: Load and verify WebSocket connection
4. ✅ Visitor chat: Test widget on WordPress
5. ✅ SMS webhook: Send test SMS via Twilio

### Rollback Plan

**If issues occur**:

1. **Quick rollback** (< 5 min):
   ```bash
   git revert HEAD
   git push origin main
   # Render auto-deploys previous version
   ```

2. **Manual rollback** (if git fails):
   ```bash
   # On Render dashboard
   # Go to "Deploys" tab
   # Click "Rollback" on previous successful deploy
   ```

3. **Database rollback** (if schema changed):
   ```bash
   # Restore backup
   cp /data/handoff.sqlite.backup /data/handoff.sqlite

   # Or use Alembic downgrade
   alembic downgrade -1
   ```

---

## Testing Strategy

### Test Pyramid

```
        /\
       /  \
      / E2E\       5% (Playwright, full stack)
     /------\
    /   INT  \     15% (FastAPI TestClient, API integration)
   /----------\
  /    UNIT    \   80% (pytest, individual functions)
 /--------------\
```

### Unit Tests (80%)

**Test each function in isolation**:

```python
# tests/unit/test_security.py
from app.core.security import verify_password, get_password_hash

def test_password_hashing():
    password = "testpass123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrongpass", hashed)

def test_jwt_creation():
    from app.core.security import create_access_token
    token = create_access_token({"sub": "test@example.com"})
    assert isinstance(token, str)
    assert len(token) > 50
```

**Run unit tests**:
```bash
pytest backend/tests/unit/ -v
```

### Integration Tests (15%)

**Test API endpoints with database**:

```python
# tests/integration/test_auth_api.py
def test_login_success(client, db):
    # Create user
    from app.crud.user import create_user
    from app.schemas.user import UserCreate
    user_data = UserCreate(
        email="test@example.com",
        name="Test User",
        password="testpass123"
    )
    create_user(db, user_data)

    # Test login
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "testpass123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "nonexistent@example.com", "password": "wrong"}
    )
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]
```

**Run integration tests**:
```bash
pytest backend/tests/integration/ -v
```

### E2E Tests (5%)

**Test full user flows with Playwright**:

```javascript
// tests/e2e/admin-dashboard.spec.js
import { test, expect } from '@playwright/test';

test('admin can login and view conversations', async ({ page }) => {
  // Navigate to dashboard
  await page.goto('http://localhost:8000/admin-app/');

  // Should redirect to login
  await expect(page).toHaveURL(/.*login/);

  // Fill login form
  await page.fill('input[name="email"]', 'admin@dwc.com');
  await page.fill('input[name="password"]', 'admin123');
  await page.click('button[type="submit"]');

  // Should redirect to dashboard
  await expect(page).toHaveURL(/.*dashboard/);

  // Should see conversations
  await expect(page.locator('.conversation-item')).toHaveCount(3);

  // Click on conversation
  await page.click('.conversation-item:first-child');

  // Should see chat box
  await expect(page.locator('.chat-box')).toBeVisible();
});

test('admin can send message', async ({ page }) => {
  // ... login steps ...

  // Type message
  await page.fill('textarea[name="message"]', 'Test message');
  await page.click('button:has-text("Send")');

  // Should appear in chat
  await expect(page.locator('.message:last-child')).toContainText('Test message');
});
```

**Run E2E tests**:
```bash
# Start backend and frontend
docker-compose up -d

# Run Playwright tests
npx playwright test
```

### Test Coverage Goals

- **Overall**: > 80%
- **Core modules** (`core/`, `crud/`): > 90%
- **API routes** (`api/v1/`): > 85%
- **Models & schemas**: > 75%

**Measure coverage**:
```bash
pytest --cov=backend --cov-report=html
# Open htmlcov/index.html in browser
```

---

## Deployment Plan

### Pre-Deployment

- [ ] **Run full test suite**
  ```bash
  pytest backend/tests/ --cov=backend
  npx playwright test
  ```

- [ ] **Review Render logs** for recent errors

- [ ] **Backup database**
  ```bash
  # Via Render shell
  cp /data/handoff.sqlite /data/handoff.sqlite.$(date +%Y%m%d_%H%M%S)
  ```

- [ ] **Set maintenance mode** (optional)
  ```python
  # Add to main.py
  @app.middleware("http")
  async def maintenance_mode(request, call_next):
      if os.getenv("MAINTENANCE_MODE") == "true":
          return JSONResponse(
              status_code=503,
              content={"detail": "Service under maintenance"}
          )
      return await call_next(request)
  ```

### Deployment Steps

#### Phase 1 Deployment (Admin Dashboard Fix)

**Checklist**:
- [ ] Update `vite.config.js` with `base: '/admin-app/'`
- [ ] Rebuild frontend: `npm run build`
- [ ] Test locally: `http://localhost:8000/admin-app`
- [ ] Commit changes
- [ ] Push to GitHub
- [ ] Monitor Render build logs
- [ ] Test production: `https://dwc-omnichat.onrender.com/admin-app`
- [ ] Verify WebSocket connection
- [ ] Check Sentry for errors (if configured)

**Estimated Downtime**: 0 minutes (Render zero-downtime deploy)

#### Phase 2 Deployment (Backend Refactor)

**Checklist**:
- [ ] Merge feature branch to main
- [ ] Push to GitHub
- [ ] Monitor Render build (~5-10 min)
- [ ] Run smoke tests:
  ```bash
  ./scripts/smoke_test.sh https://dwc-omnichat.onrender.com
  ```
- [ ] Check all endpoints:
  - `/api/v1/health`
  - `/api/v1/auth/login`
  - `/api/v1/admin/convos`
  - `/admin-ws` WebSocket
- [ ] Monitor error rate in Render logs
- [ ] Test admin dashboard functionality
- [ ] Test visitor chat widget

**Estimated Downtime**: ~30 seconds (container restart)

#### Phase 3 Deployment (Docker + Alembic)

**Checklist**:
- [ ] Update `render.yaml` to use Docker
- [ ] Test Docker build locally:
  ```bash
  docker build -t dwc-omnichat .
  docker run -p 8000:8000 dwc-omnichat
  ```
- [ ] Push to GitHub
- [ ] Monitor Render build (~10-15 min for Docker)
- [ ] Verify migrations ran:
  ```bash
  # Check Render logs for:
  # "Running migrations..."
  # "INFO  [alembic.runtime.migration] Running upgrade -> abc123"
  ```
- [ ] Run full smoke test suite
- [ ] Monitor for 1 hour

**Estimated Downtime**: ~1 minute (Docker container start)

### Post-Deployment

- [ ] **Monitor for 24 hours**
  - Check Render logs every hour
  - Monitor error rate
  - Check WebSocket connection count

- [ ] **User acceptance testing**
  - Admin logs in and sends message
  - Visitor widget works on WordPress
  - SMS messages are received

- [ ] **Performance check**
  - Response times < 200ms
  - WebSocket latency < 50ms
  - Database query time < 50ms

- [ ] **Update documentation**
  - API documentation (`/docs`)
  - README.md
  - Architecture diagrams

### Rollback Triggers

**Automatic rollback if**:
- Error rate > 5%
- Response time > 2 seconds
- WebSocket connections fail
- Health check fails

**Manual rollback if**:
- Critical bugs reported
- Database corruption
- Admin dashboard inaccessible

---

## Success Metrics

### Technical Metrics

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| **Code Organization** | 1 file (814 lines) | 20+ modules | `find backend/app -name "*.py" \| wc -l` |
| **Test Coverage** | 0% | > 80% | `pytest --cov` |
| **Response Time** | ~150ms | < 100ms | Render metrics |
| **Error Rate** | Unknown | < 1% | Sentry dashboard |
| **Build Time** | ~2 min | < 5 min | Render build logs |
| **Bundle Size** | 232KB | < 200KB | `ls -lh admin-frontend/dist/assets/*.js` |

### Business Metrics

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| **Admin Login Success** | ~70% (guessing) | > 95% | Track login attempts vs successes |
| **Message Delivery Rate** | Unknown | > 99% | Track sent vs delivered |
| **WebSocket Uptime** | Unknown | > 99.9% | Monitor disconnections |
| **Time to Resolve Conversation** | Unknown | < 5 min | Track timestamps |

### Developer Experience

| Metric | Current | Target |
|--------|---------|--------|
| **Time to add new endpoint** | 30 min | 10 min (with template) |
| **Time to onboard new developer** | 2 days | 4 hours (with docs) |
| **Local setup time** | 30 min | 5 min (with Docker) |
| **Code review time** | N/A | < 2 hours |

---

## Appendix

### A. Commands Reference

#### Development

```bash
# Start backend (old)
uvicorn server:app --reload

# Start backend (new)
uvicorn backend.app.main:app --reload

# Start frontend
cd admin-frontend && npm run dev

# Run tests
pytest backend/tests/

# Run linter
ruff check backend/

# Format code
black backend/

# Type checking
mypy backend/
```

#### Database

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

#### Docker

```bash
# Build image
docker build -t dwc-omnichat .

# Run container
docker run -p 8000:8000 --env-file .env dwc-omnichat

# Run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop all containers
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

### B. Environment Variables

```bash
# .env.example
# Copy this to .env and fill in values

# Application
PROJECT_NAME=DWC Omnichat
ENVIRONMENT=production

# Database
DATABASE_URL=sqlite:///./handoff.sqlite

# Security
SECRET_KEY=your-secret-key-here  # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=4320  # 3 days

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:5173","https://dwc-omnichat.onrender.com"]

# Twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_NUMBER=

# Facebook
FB_PAGE_ACCESS_TOKEN=
FB_VERIFY_TOKEN=
FB_APP_SECRET=

# Monitoring (optional)
SENTRY_DSN=

# Feature Flags
MAINTENANCE_MODE=false
ENABLE_REGISTRATION=false
```

### C. Troubleshooting

#### Issue: Import errors after refactoring

**Symptom**: `ModuleNotFoundError: No module named 'app'`

**Solution**:
```bash
# Ensure PYTHONPATH includes backend directory
export PYTHONPATH="${PYTHONPATH}:${PWD}/backend"

# Or use absolute imports in all files
from backend.app.core.config import settings
```

#### Issue: Alembic can't find models

**Symptom**: `alembic revision --autogenerate` doesn't detect changes

**Solution**:
```python
# Ensure all models are imported in alembic/env.py
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
# ...

target_metadata = Base.metadata
```

#### Issue: Docker build fails on frontend

**Symptom**: `npm install` fails with permission errors

**Solution**:
```dockerfile
# Use node user instead of root
FROM node:18-alpine AS frontend
USER node
WORKDIR /home/node/app
COPY --chown=node:node admin-frontend/package*.json ./
RUN npm ci
COPY --chown=node:node admin-frontend/ ./
RUN npm run build
```

### D. Code Style Guide

**FastAPI Conventions**:
- Use async/await for database operations
- Use dependency injection for reusable logic
- Follow RESTful naming (plural nouns: `/users`, `/conversations`)
- Use HTTP status codes correctly (201 for created, 204 for deleted)
- Always include response_model for type safety

**Python Style**:
- Follow PEP 8
- Use type hints everywhere
- Docstrings for all public functions
- Max line length: 88 (Black default)
- Import order: stdlib, third-party, local

**React/JavaScript Style**:
- Use functional components with hooks
- Prefer const over let
- Use async/await over .then()
- Use destructuring for props
- One component per file

### E. Resources

**Documentation**:
- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- Alembic: https://alembic.sqlalchemy.org/
- React: https://react.dev/
- Vite: https://vitejs.dev/

**Templates & Examples**:
- FastAPI Full-Stack: https://github.com/fastapi/full-stack-fastapi-template
- FastAPI Boilerplate: https://github.com/benavlabs/fastapi-boilerplate
- Awesome FastAPI: https://github.com/mjhea0/awesome-fastapi

**Tools**:
- Ruff (linter): https://github.com/astral-sh/ruff
- Black (formatter): https://github.com/psf/black
- Pytest (testing): https://docs.pytest.org/
- Playwright (E2E): https://playwright.dev/

---

## Next Steps

### Immediate (This Week)
1. ✅ Fix admin dashboard base path issue
2. ⏳ Create backup of production database
3. ⏳ Set up feature branch for refactoring
4. ⏳ Begin Phase 2: Move config to `app/core/config.py`

### Short-term (Next 2 Weeks)
1. Complete backend modularization
2. Write unit tests for each module
3. Update frontend API calls
4. Deploy to staging for testing

### Long-term (Next Month)
1. Add Alembic migrations
2. Implement Docker builds
3. Set up CI/CD with GitHub Actions
4. Add monitoring with Sentry

---

**Document maintained by**: Development Team
**Last updated**: 2025-01-22
**Next review**: After Phase 1 completion
