from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, WebSocketException, HTTPException, UploadFile, File, Form, Depends, Query, status
from fastapi.responses import Response, JSONResponse, PlainTextResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import File
from pydantic import BaseModel
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client as TwilioClient
from twilio.request_validator import RequestValidator
from dotenv import load_dotenv
import os, logging, datetime, sqlite3, asyncio
from auth import router as auth_router, require_role, TokenData, SECRET_KEY, ALGORITHM
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Dict, Set
from jose import jwt
DEBUG_ADMIN_PUSH = False
import json

# ========================
# Load env & App
# ========================
load_dotenv()

# Use Render's persistent disk if available, otherwise local file
if os.path.exists("/data"):
    DB_PATH = "/data/handoff.sqlite"
else:
    DB_PATH = str(Path(__file__).parent / "handoff.sqlite")

from fastapi.openapi.utils import get_openapi
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="DWC Omnichat",
        version="1.0.0",
        description="Omnichat API for managing conversations, users, and more.",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/api/v1/auth/login",
                    "scopes": {}
                }
            }
        }
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method.setdefault("security", []).append({"OAuth2PasswordBearer": []})
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app = FastAPI(title="DWC Omnichat")
app.openapi = custom_openapi

app.include_router(auth_router)

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "")
# Allow both production Render URL and local development
if not FRONTEND_ORIGIN:
    logging.warning("⚠️  FRONTEND_ORIGIN not set in environment - using wildcard CORS (insecure for production)")
    allowed_origins = ["*"]
else:
    allowed_origins = [
        FRONTEND_ORIGIN,
        "https://dwc-omnichat.onrender.com",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",  # Vite fallback port
        "http://127.0.0.1:5174",
        "null"  # Allow file:// protocol for local testing
    ]
    logging.info(f"✅ CORS configured for origins: {', '.join(allowed_origins)}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
if Path("static").exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount React Admin Dashboard
if Path("admin-frontend/dist").exists():
    app.mount("/admin-app", StaticFiles(directory="admin-frontend/dist", html=True), name="admin-app")
    logging.info("✅ Admin dashboard mounted at /admin-app")
else:
    logging.warning("⚠️  Admin frontend dist directory not found - run 'npm run build' in admin-frontend/")

# Logging
log_handler = RotatingFileHandler("chat.log", maxBytes=1_000_000, backupCount=5)
console_handler = logging.StreamHandler()  # ensure logs also go to stdout for Render
logging.basicConfig(
    handlers=[log_handler, console_handler],
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ========================
# Twilio / Config
# ========================
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
VERIFY_TWILIO_SIGNATURE = os.getenv("VERIFY_TWILIO_SIGNATURE", "0") == "1"
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")

twilio_client = None
twilio_validator = None
if ACCOUNT_SID and AUTH_TOKEN:
    twilio_client = TwilioClient(ACCOUNT_SID, AUTH_TOKEN)
    twilio_validator = RequestValidator(AUTH_TOKEN)

SHIFT_ROTA = [{"name": "Default"}]  # stub for config
BACKUP_NUMBER = os.getenv("BACKUP_NUMBER")
ESCALATE_AFTER_SECONDS = 120

# ========================
# DB Helpers
# ========================
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def db_init():
    with db() as conn:
        c = conn.cursor()

        # Create tenants table first (foreign key dependency for users)
        c.execute("""CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""")

        # Create users table for authentication
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL DEFAULT 1,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'staff',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (tenant_id) REFERENCES tenants(id)
        )""")

        # Create events table for audit logging
        c.execute("""CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tenant_id INTEGER,
            type TEXT NOT NULL,
            payload TEXT,
            ts TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (tenant_id) REFERENCES tenants(id)
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT, channel TEXT,
            assigned_staff TEXT,
            open INTEGER, updated_at TEXT,
            patience_sent INTEGER DEFAULT 0,
            final_sent INTEGER DEFAULT 0,
            escalation_active INTEGER DEFAULT 1
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT, channel TEXT,
            sender TEXT, text TEXT, ts TEXT
        )""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS followups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT, channel TEXT,
            name TEXT, email TEXT, phone TEXT,
            message TEXT, ts TEXT
        )
        """)

        # ✅ Add this for migration from followups
        c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            channel TEXT,
            name TEXT,
            contact TEXT,
            message TEXT,
            ts TEXT,
            migrated_at TEXT
        )
        """)


        # Backward compatibility: add new columns if missing
        try:
            c.execute("ALTER TABLE conversations ADD COLUMN patience_sent INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            c.execute("ALTER TABLE conversations ADD COLUMN final_sent INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            c.execute("ALTER TABLE conversations ADD COLUMN escalation_active INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass

        conn.commit()


def seed_admin_user():
    """
    Create default admin user and tenant if they don't exist.
    This runs on every startup but only creates the user once.
    """
    with db() as conn:
        c = conn.cursor()

        # Check if default tenant exists
        c.execute("SELECT id FROM tenants WHERE id = 1")
        if not c.fetchone():
            c.execute(
                "INSERT INTO tenants (id, name, created_at) VALUES (?, ?, datetime('now'))",
                (1, "Default Tenant")
            )
            logging.info("✅ Created default tenant")

        # Check if admin user exists
        c.execute("SELECT id FROM users WHERE email = ?", ("admin@dwc.com",))
        if not c.fetchone():
            # Import password hashing from auth module
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

            # Default admin password - CHANGE THIS IMMEDIATELY AFTER FIRST LOGIN
            default_password = "admin123"
            password_hash = pwd_context.hash(default_password)

            c.execute(
                """INSERT INTO users (tenant_id, email, name, password_hash, role, created_at)
                   VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                (1, "admin@dwc.com", "Default Admin", password_hash, "admin")
            )
            conn.commit()
            logging.info("✅ Created default admin user")
            logging.info("   📧 Email: admin@dwc.com")
            logging.info("   🔑 Password: admin123")
            logging.info("   ⚠️  PLEASE CHANGE THIS PASSWORD IMMEDIATELY!")
        else:
            logging.info("ℹ️  Admin user already exists")


# ========================
# Models
# ========================
class StartHandoffSchema(BaseModel):
    user_id: str
    channel: str = "webchat"
    initial_message: Optional[str] = None

class PostMessageSchema(BaseModel):
    user_id: str
    channel: str = "webchat"
    text: str

class AdminSendSchema(BaseModel):
    user_id: str
    channel: str
    text: str


class FollowupSchema(BaseModel):
    user_id: str
    channel: str = "webchat"
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    message: Optional[str] = None
class BulkCloseSchema(BaseModel):
    conversations: list[dict]  # List of {user_id, channel} dicts


# ========================
# Conversation Helpers
# ========================
def ensure_conversation(user_id: str, channel: str) -> bool:
    """
    Ensures conversation exists and is open.
    Returns True if this is a brand new conversation (first message ever).
    """
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    is_new = False

    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, open FROM conversations WHERE user_id=? AND channel=?",
                  (user_id, channel))
        row = c.fetchone()
        if not row:
            # First message ever - create conversation with escalation enabled
            c.execute("INSERT INTO conversations (user_id, channel, assigned_staff, open, updated_at, escalation_active) VALUES (?,?,?,?,?,?)",
                      (user_id, channel, None, 1, ts, 1))
            is_new = True
        else:
            # Conversation exists - check if it was closed
            was_closed = row["open"] == 0
            if was_closed:
                # Reopening after being closed - re-enable escalation for new user message
                c.execute("UPDATE conversations SET open=1, updated_at=?, escalation_active=1, patience_sent=0, final_sent=0 WHERE user_id=? AND channel=?",
                          (ts, user_id, channel))
            else:
                # Conversation still open - just update timestamp, don't touch escalation
                c.execute("UPDATE conversations SET updated_at=? WHERE user_id=? AND channel=?",
                          (ts, user_id, channel))
        conn.commit()

    return is_new

def add_message(user_id: str, channel: str, sender: str, text: str):
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    with db() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO messages (user_id, channel, sender, text, ts) VALUES (?,?,?,?,?)",
                  (user_id, channel, sender, text, ts))
        c.execute("UPDATE conversations SET updated_at=? WHERE user_id=? AND channel=?",
                  (ts, user_id, channel))
        conn.commit()

def get_messages(user_id: str, channel: str):
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT sender, text, ts FROM messages WHERE user_id=? AND channel=? ORDER BY id ASC",
                  (user_id, channel))
        rows = c.fetchall()
        c.execute("SELECT assigned_staff, open, updated_at FROM conversations WHERE user_id=? AND channel=?",
                  (user_id, channel))
        convo = c.fetchone()
    return {
        "assigned_staff": convo["assigned_staff"] if convo else None,
        "open": bool(convo["open"]) if convo else False,
        "last_updated": convo["updated_at"] if convo else None,
        "messages": [dict(r) for r in rows]
    }

def set_assignment(user_id: str, channel: str, staff_number: Optional[str], open_state: bool):
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    with db() as conn:
        c = conn.cursor()
        c.execute("UPDATE conversations SET assigned_staff=?, open=?, updated_at=? WHERE user_id=? AND channel=?",
                  (staff_number, 1 if open_state else 0, ts, user_id, channel))
        conn.commit()

# ========================
# WebSocket Manager
# ========================
class WSManager:
    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}

    def key(self, user_id: str, channel: str) -> str:
        return f"{user_id}|{channel}"

    async def connect(self, user_id: str, channel: str, ws: WebSocket):
        await ws.accept()
        k = self.key(user_id, channel)
        self.connections.setdefault(k, set()).add(ws)

    def disconnect(self, user_id: str, channel: str, ws: WebSocket):
        k = self.key(user_id, channel)
        if k in self.connections and ws in self.connections[k]:
            self.connections[k].remove(ws)
            if not self.connections[k]:
                del self.connections[k]

    async def push(self, user_id: str, channel: str, payload: dict):
        k = self.key(user_id, channel)
        for ws in list(self.connections.get(k, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(user_id, channel, ws)

ws_manager = WSManager()

# ========================
# WebSocket Authentication
# ========================
async def get_websocket_token(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None),
) -> TokenData:
    """
    Validate JWT token for WebSocket connections.
    Token should be passed as a query parameter: ws://host/admin-ws?token=<jwt>

    IMPORTANT: This function accepts the websocket connection before validation
    to allow proper error handling and connection closure.
    """
    # Accept the connection first (required before we can close it)
    await websocket.accept()

    if token is None:
        logging.warning("[WebSocket] Connection attempt without token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    try:
        # Decode and validate JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_data = TokenData(**payload)

        # Verify role is admin or staff
        if token_data.role not in ["admin", "staff"]:
            logging.warning(f"[WebSocket] Unauthorized role attempt: {token_data.role} from {token_data.email}")
            await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
            raise WebSocketException(code=status.WS_1003_UNSUPPORTED_DATA)

        logging.info(f"[WebSocket] Authenticated: {token_data.email} ({token_data.role})")
        return token_data

    except jwt.ExpiredSignatureError:
        logging.warning("[WebSocket] Expired token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    except jwt.JWTError as e:
        logging.warning(f"[WebSocket] Invalid token: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    except Exception as e:
        logging.error(f"[WebSocket] Token validation error: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

# ========================
# Routes
# ========================
@app.on_event("startup")
async def startup_tasks():
    db_init()
    seed_admin_user()
    logging.info("DB initialized, admin user seeded, and escalation loop starting.")
    logging.info(f"Env check: SID={'set' if ACCOUNT_SID else 'missing'}, "
                 f"Token={'set' if AUTH_TOKEN else 'missing'}, "
                 f"Number={TWILIO_NUMBER}, "
                 f"Client={'ready' if twilio_client else 'NONE'}")
    asyncio.create_task(escalation_loop())

@app.get("/")
def root():
    """Root endpoint - API information"""
    return {
        "name": "DWC Omnichat API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "admin_login": "/api/v1/auth/login"
    }

@app.get("/health")
def health():
    return {"status": "running", "db": str(DB_PATH), "shifts": [s["name"] for s in SHIFT_ROTA]}

# Admin dashboard - redirect legacy route to new React dashboard
@app.get("/admin")
def admin_dashboard_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin-app/login", status_code=301)

# Admin API
@app.get("/admin/api/convos", dependencies=[Depends(require_role(["admin", "staff"]))])
def admin_convos():
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM conversations WHERE open=1 ORDER BY updated_at DESC")
        rows = c.fetchall()

        conversations = []
        for row in rows:
            convo = dict(row)

            # Get message count and preview for this conversation
            c.execute("""
                SELECT COUNT(*) as count,
                       GROUP_CONCAT(sender || ': ' || text, ' | ') as preview
                FROM (
                    SELECT sender, text FROM messages
                    WHERE user_id=? AND channel=?
                    ORDER BY ts DESC LIMIT 3
                )
            """, (convo['user_id'], convo['channel']))
            msg_data = c.fetchone()

            convo['message_count'] = msg_data['count'] if msg_data else 0
            convo['preview'] = msg_data['preview'] if msg_data and msg_data['preview'] else "No messages yet"
            conversations.append(convo)

    return {"conversations": conversations}

@app.get("/admin/api/messages/{user_id}/{channel}", dependencies=[Depends(require_role(["admin", "staff"]))])
def get_conversation_messages(user_id: str, channel: str):
    """Fetch all messages for a specific conversation"""
    with db() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT sender, text, ts
            FROM messages
            WHERE user_id=? AND channel=?
            ORDER BY ts ASC
        """, (user_id, channel))
        messages = [dict(row) for row in c.fetchall()]

        # Also get conversation metadata
        c.execute("""
            SELECT * FROM conversations
            WHERE user_id=? AND channel=?
        """, (user_id, channel))
        convo = c.fetchone()

    return {
        "messages": messages,
        "conversation": dict(convo) if convo else None
    }

# ✅ Corrected: merged closed convos + migrated followups
@app.get("/admin/api/history", dependencies=[Depends(require_role(["admin"]))])
def admin_history():
    with db() as conn:
        c = conn.cursor()

        # Closed conversations from conversations table (show all fields)
        c.execute("""
            SELECT user_id, channel, assigned_staff, updated_at,
                   created_at, closed_at, 'conversation' as source,
                   NULL as name, NULL as email, NULL as phone, NULL as message
            FROM conversations
            WHERE open=0
            ORDER BY updated_at DESC
        """)
        convos = [dict(r) for r in c.fetchall()]

        # Count messages for each conversation
        for convo in convos:
            c.execute("SELECT COUNT(*) FROM messages WHERE user_id=? AND channel=?",
                     (convo["user_id"], convo["channel"]))
            convo["message_count"] = c.fetchone()[0]

        # Migrated followups from history table (show all fields)
        c.execute("""
            SELECT id, user_id, channel, name, contact, message,
                   ts as created_at, migrated_at as updated_at, 'followup' as source,
                   NULL as assigned_staff, NULL as closed_at, 0 as message_count
            FROM history
            ORDER BY migrated_at DESC
        """)
        followup_histories = [dict(r) for r in c.fetchall()]

        # Parse contact field into email and phone for followups
        for fh in followup_histories:
            contact = fh.get("contact", "")
            # Extract email and phone from "Email: x, Phone: y" format
            fh["email"] = None
            fh["phone"] = None
            if contact:
                parts = contact.split(", ")
                for part in parts:
                    if part.startswith("Email: "):
                        fh["email"] = part.replace("Email: ", "").strip()
                    elif part.startswith("Phone: "):
                        fh["phone"] = part.replace("Phone: ", "").strip()

    # Combine both lists (no deduplication - show all history)
    combined = convos + followup_histories
    combined.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

    return {"history": combined}

@app.get("/admin/api/history/export", dependencies=[Depends(require_role(["admin"]))])
def export_and_purge_history():
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).isoformat() + "Z"
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM conversations WHERE updated_at < ?", (cutoff,))
        convos = [dict(r) for r in c.fetchall()]
        c.execute("SELECT * FROM messages WHERE ts < ?", (cutoff,))
        msgs = [dict(r) for r in c.fetchall()]
        c.execute("DELETE FROM conversations WHERE updated_at < ?", (cutoff,))
        c.execute("DELETE FROM messages WHERE ts < ?", (cutoff,))
        conn.commit()
    return {"conversations": convos, "messages": msgs}

@app.post("/admin/api/followups/clear/{fid}")
def clear_followup(fid: int, user: TokenData = Depends(require_role(["admin"]))):
    with db() as conn:
        c = conn.cursor()
        # Step 1: fetch followup row
        c.execute("SELECT id, user_id, channel, name, contact, message, ts FROM followups WHERE id=?", (fid,))
        row = c.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Followup not found")

        # Step 2: insert into history (keeping fields consistent)
        c.execute("""
            INSERT INTO history (user_id, channel, name, contact, message, ts, migrated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            row["user_id"],
            row["channel"],
            row["name"],
            row["contact"],
            row["message"],
            row["ts"],
            datetime.datetime.utcnow().isoformat()+"Z"
        ))

        # Step 2b: also log followup in messages so it appears in history threads
        c.execute("""
            INSERT INTO messages (user_id, channel, sender, text, ts)
            VALUES (?, ?, ?, ?, ?)
        """, (
            row["user_id"],
            row["channel"],
            "system",
            f"Follow-up submitted:\nName: {row['name']}\nContact: {row['contact']}\nMessage: {row['message']}",
            row["ts"]
        ))

        # Step 3: delete from followups
        c.execute("DELETE FROM followups WHERE id=?", (fid,))
        conn.commit()

    return {"status": "migrated", "id": fid}

@app.get("/admin/api/escalated", dependencies=[Depends(require_role(["admin", "staff"]))])
def admin_escalated():
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM conversations WHERE open=1 AND final_sent=1 ORDER BY updated_at DESC")
        rows = c.fetchall()
    return {"conversations": [dict(r) for r in rows]}

@app.get("/admin/api/followups", dependencies=[Depends(require_role(["admin"]))])
def admin_followups():
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM followups ORDER BY ts DESC LIMIT 200")
        rows = c.fetchall()
    return {"followups": [dict(r) for r in rows]}

@app.get("/admin/api/conversations", dependencies=[Depends(require_role(["admin", "staff"]))])
def admin_conversations(status: str = "open"):
    """Get conversations filtered by status (open, escalated, closed)"""
    with db() as conn:
        c = conn.cursor()

        if status == "open":
            # Get open conversations that are NOT escalated
            c.execute("""
                SELECT * FROM conversations
                WHERE open=1 AND final_sent=0
                ORDER BY updated_at DESC
            """)
        elif status == "escalated":
            # Get escalated conversations (open AND final_sent=1)
            c.execute("""
                SELECT * FROM conversations
                WHERE open=1 AND final_sent=1
                ORDER BY updated_at DESC
            """)
        elif status == "closed":
            # Get closed conversations
            c.execute("""
                SELECT * FROM conversations
                WHERE open=0
                ORDER BY updated_at DESC LIMIT 100
            """)
        else:
            # Default: all open conversations
            c.execute("""
                SELECT * FROM conversations
                WHERE open=1
                ORDER BY updated_at DESC
            """)

        rows = c.fetchall()
        conversations = [dict(r) for r in rows]

        # Add message count for each conversation
        for convo in conversations:
            c.execute("""
                SELECT COUNT(*) FROM messages
                WHERE user_id=? AND channel=?
            """, (convo["user_id"], convo["channel"]))
            convo["message_count"] = c.fetchone()[0]

    return {"conversations": conversations}

@app.get("/admin/api/followups/unviewed-count", dependencies=[Depends(require_role(["admin"]))])
def admin_followups_unviewed_count():
    """Get count of unviewed followups for notification badge"""
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM followups WHERE viewed = 0")
        count = c.fetchone()[0]
    return {"count": count}

@app.post("/admin/api/followups/{followup_id}/mark-viewed", dependencies=[Depends(require_role(["admin"]))])
def mark_followup_viewed(followup_id: int):
    """Mark a followup as viewed when admin opens it"""
    with db() as conn:
        c = conn.cursor()
        c.execute("UPDATE followups SET viewed = 1 WHERE id = ?", (followup_id,))
        conn.commit()
    return {"success": True, "id": followup_id}

@app.delete("/admin/api/followups/{followup_id}", dependencies=[Depends(require_role(["admin"]))])
def delete_followup(followup_id: int):
    """Archive a followup to history instead of deleting"""
    with db() as conn:
        c = conn.cursor()
        # Get the followup data
        c.execute("SELECT user_id, channel, name, email, phone, message, ts FROM followups WHERE id = ?", (followup_id,))
        row = c.fetchone()

        if row:
            # Archive to history table
            contact = f"Email: {row[3] or 'N/A'}, Phone: {row[4] or 'N/A'}"
            c.execute(
                "INSERT INTO history (user_id, channel, name, contact, message, ts, migrated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (row[0], row[1], row[2], contact, row[5], row[6], datetime.datetime.utcnow().isoformat() + "Z")
            )

            # Remove from followups
            c.execute("DELETE FROM followups WHERE id = ?", (followup_id,))
            conn.commit()
            return {"success": True, "id": followup_id, "archived": True}
        else:
            raise HTTPException(status_code=404, detail="Followup not found")

@app.get("/admin/api/history/export", dependencies=[Depends(require_role(["admin"]))])
def export_history(days: int = None):
    """Export history records. If days specified, only exports records from last N days."""
    with db() as conn:
        c = conn.cursor()
        if days:
            cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat() + "Z"
            c.execute("SELECT * FROM history WHERE migrated_at >= ? ORDER BY migrated_at DESC", (cutoff_date,))
        else:
            c.execute("SELECT * FROM history ORDER BY migrated_at DESC")
        rows = c.fetchall()
    return {"history": [dict(r) for r in rows], "count": len(rows)}

@app.post("/admin/api/history/export-and-delete", dependencies=[Depends(require_role(["admin"]))])
def export_and_delete_history():
    """Export all history and delete records older than 30 days"""
    with db() as conn:
        c = conn.cursor()

        # Get all history for export
        c.execute("SELECT * FROM history ORDER BY migrated_at DESC")
        all_history = [dict(r) for r in c.fetchall()]

        # Delete records older than 30 days
        cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).isoformat() + "Z"
        c.execute("DELETE FROM history WHERE migrated_at < ?", (cutoff_date,))
        deleted_count = c.rowcount
        conn.commit()

    return {
        "success": True,
        "history": all_history,
        "total_exported": len(all_history),
        "deleted_count": deleted_count
    }

@app.get("/admin/api/messages/{channel}/{user_id}", dependencies=[Depends(require_role(["admin", "staff"]))])
def admin_messages(channel: str, user_id: str):
    return get_messages(user_id, channel)


@app.post("/admin/api/send")
async def admin_send(msg: AdminSendSchema, user: TokenData = Depends(require_role(["admin", "staff"]))):
    add_message(msg.user_id, msg.channel, "staff", msg.text)
    # Terminate escalation completely when staff replies
    with db() as conn:
        conn.execute("UPDATE conversations SET escalation_active=0, final_sent=0, patience_sent=0 WHERE user_id=? AND channel=?",
                     (msg.user_id, msg.channel))
        conn.commit()

    await push_with_admin(msg.user_id, msg.channel,
                          {"sender": "staff", "text": msg.text,
                           "ts": datetime.datetime.utcnow().isoformat() + "Z"})

    # Forward to Twilio if SMS/WhatsApp, with normalization + debug logging
    if twilio_client:
        channel = (msg.channel or "").strip().lower()
        if channel in ("sms", "whatsapp"):
            try:
                if channel == "whatsapp":
                    if not msg.user_id.startswith("whatsapp:"):
                        to_number = f"whatsapp:{msg.user_id}"
                    else:
                        to_number = msg.user_id
                    from_number = f"whatsapp:{TWILIO_NUMBER}"
                else:
                    to_number = msg.user_id
                    from_number = TWILIO_NUMBER

                logging.info(f"Sending via Twilio: from={from_number}, to={to_number}, body={msg.text}")
                twilio_client.messages.create(
                    body=msg.text,
                    from_=from_number,
                    to=to_number
                )
            except Exception as e:
                logging.exception(f"Twilio send failed with exception: {repr(e)}")

    return {"status": "ok"}


@app.post("/followup")
async def followup_submit(data: FollowupSchema):
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    # write to followups
    with db() as conn:
        conn.execute(
            "INSERT INTO followups (user_id, channel, name, email, phone, message, ts) VALUES (?,?,?,?,?,?,?)",
            (data.user_id, data.channel, data.name, data.email, data.phone, data.message, ts),
        )
        # close the conversation so escalation loop won't re-fire
        conn.execute("UPDATE conversations SET open=0, updated_at=? WHERE user_id=? AND channel=?",
                     (ts, data.user_id, data.channel))
        conn.commit()

    # thank-you system message goes to history
    add_message(data.user_id, data.channel, "system", "✅ Thank you for your message. Our team will respond promptly.")

    # push to visitor
    await ws_manager.push(data.user_id, data.channel, {
        "sender": "system",
        "text": "✅ Thank you for your message. Our team will respond promptly.",
        "ts": ts
    })

    # notify admin dashboards
    await push_with_admin(
        data.user_id, data.channel,
        {"sender": "system", "text": f"[Follow-up submitted by visitor]", "ts": ts}
    )
    return {"status": "ok"}

@app.post("/handoff/close")
def handoff_close(data: StartHandoffSchema, user: TokenData = Depends(require_role(["admin", "staff"]))):
    set_assignment(data.user_id, data.channel, None, False)
    return {"status": "closed"}

@app.post("/handoff/close-bulk")
def handoff_close_bulk(data: BulkCloseSchema, user: TokenData = Depends(require_role(["admin", "staff"]))):
    """Close multiple conversations at once"""
    logging.info(f"[BULK CLOSE] Received request to close {len(data.conversations)} conversations")
    closed_count = 0
    errors = []
    
    for convo in data.conversations:
        try:
            user_id = convo.get("user_id")
            channel = convo.get("channel", "webchat")
            
            logging.info(f"[BULK CLOSE] Processing: user_id={user_id}, channel={channel}")
            
            if user_id:
                set_assignment(user_id, channel, None, False)
                closed_count += 1
                logging.info(f"[BULK CLOSE] Successfully closed: {user_id} on {channel}")
            else:
                logging.warning(f"[BULK CLOSE] Skipping conversation with no user_id: {convo}")
        except Exception as e:
            error_msg = f"Failed to close {convo.get('user_id')}: {str(e)}"
            logging.error(f"[BULK CLOSE] {error_msg}")
            errors.append(error_msg)
    
    result = {
        "status": "ok",
        "closed": closed_count,
        "total": len(data.conversations),
        "errors": errors if errors else None
    }
    logging.info(f"[BULK CLOSE] Result: {result}")
    return result

# Webchat
@app.get("/webchat")
def webchat_check():
    return {"status": "ok"}

@app.post("/webchat")
async def webchat_post(msg: PostMessageSchema):
    channel = msg.channel or "webchat"

    is_new_conversation = ensure_conversation(msg.user_id, channel)
    add_message(msg.user_id, channel, "user", msg.text)

    # Broadcast the actual user message to admin dashboards
    await push_with_admin(msg.user_id, channel, {
        "sender": "user",
        "text": msg.text,
        "ts": datetime.datetime.utcnow().isoformat() + "Z"
    })
    # Send push notifications to admin mobile apps
    await notify_admins_new_message(msg.user_id, channel, msg.text)


    # Send push notifications to admin mobile apps
    await notify_admins_new_message(msg.user_id, channel, msg.text)

    # Send greeting ONLY on first message ever
    if is_new_conversation:
        auto_msg = "Connecting you with a staff member, please wait..."
        await ws_manager.push(msg.user_id, channel, {
            "sender": "system",
            "text": auto_msg,
            "ts": datetime.datetime.utcnow().isoformat() + "Z"
        })

    return {"status": "ok"}


# Twilio SMS webhook
@app.post("/sms")
async def sms_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...)
):
    user_id = From
    channel = "whatsapp" if From.startswith("whatsapp:") else "sms"
    text = Body.strip()

    ensure_conversation(user_id, channel)
    add_message(user_id, channel, "user", text)

    await push_with_admin(user_id, channel,
                          {"sender": "user", "text": text,
                           "ts": datetime.datetime.utcnow().isoformat() + "Z"})

    resp = MessagingResponse()
    resp.message("Thanks, we got your message!")
    return PlainTextResponse(str(resp), media_type="application/xml")

# WebSocket for webchat visitors
@app.websocket("/ws/{user_id}")
async def ws_endpoint(websocket: WebSocket, user_id: str):
    await ws_manager.connect(user_id, "webchat", websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
            except Exception:
                continue  # ignore invalid messages

            ev_type = (data.get("type") or "").lower()
            if ev_type in ("typing", "stop_typing"):
                await push_with_admin(
                    user_id,
                    "webchat",
                    {
                        "sender": "user",
                        "type": ev_type,
                        "text": "",
                        "ts": datetime.datetime.utcnow().isoformat() + "Z",
                    },
                )
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(user_id, "webchat", websocket)

# WebSocket for admin dashboard (broadcast)
# Store connections with user metadata for authentication tracking
# Using List instead of Set because connection dicts are unhashable
admin_connections: list[dict] = []
admin_connections_lock = asyncio.Lock()

@app.websocket("/admin-ws")
async def ws_admin(websocket: WebSocket, user: TokenData = Depends(get_websocket_token)):
    # WebSocket already accepted in get_websocket_token dependency
    # Store connection with user metadata
    connection_info = {
        "ws": websocket,
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "tenant_id": user.tenant_id,
        "connected_at": datetime.datetime.utcnow().isoformat() + "Z"
    }
    async with admin_connections_lock:
        admin_connections.append(connection_info)

    logging.info(f"[admin] Authenticated dashboard connected: {user.email} ({user.role}), total={len(admin_connections)}")

    try:
        with db() as conn:
            c = conn.cursor()
            c.execute("SELECT user_id, channel FROM conversations WHERE open=1 ORDER BY updated_at DESC")
            convos = c.fetchall()
        for row in convos:
            convo_data = get_messages(row["user_id"], row["channel"])
            enriched = {
                "user_id": row["user_id"],
                "channel": row["channel"],
                **convo_data
            }
            try:
                await websocket.send_json({"type": "snapshot", "data": enriched})
            except Exception as e:
                logging.exception("Failed to send snapshot to admin", exc_info=e)
    except Exception as e:
        logging.exception("Replay on connect failed", exc_info=e)

    try:
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=20)
                logging.debug("[admin] received frame: %s", msg[:120])

                # Handle typing messages sent by admin dashboard
                try:
                    data = json.loads(msg)
                except Exception as e:
                    logging.warning("Failed to parse admin WS message: %s", msg)
                    continue

                ev_type = (data.get("type") or "").lower()
                user_id = data.get("user_id")
                channel = data.get("channel", "webchat")

                # Handle typing indicators from admin dashboard or mobile app
                if ev_type in ("typing", "stop_typing", "staff_typing", "staff_stop_typing") and user_id:
                    # Normalize type to typing/stop_typing for visitor
                    normalized_type = "typing" if "typing" in ev_type and "stop" not in ev_type else "stop_typing"
                    await ws_manager.push(user_id, channel, {
                        "type": normalized_type,
                        "sender": "staff",
                        "ts": datetime.datetime.utcnow().isoformat() + "Z"
                    })

            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        # Remove connection from list with lock
        async with admin_connections_lock:
            try:
                admin_connections.remove(connection_info)
            except ValueError:
                pass  # Connection already removed
        logging.info(f"[admin] Dashboard disconnected: {user.email}, total={len(admin_connections)}")

# -------------------------------------------------------------
# Simple test endpoint to verify React ↔ FastAPI proxy
# -------------------------------------------------------------
@app.get("/api/test")
def test_connection():
    return {"status": "ok", "message": "React ↔ FastAPI connection successful"}

# Helper: push to both user channel + admin dashboard
DEBUG_ADMIN_PUSH = True  # set False in production if logs too noisy

async def push_with_admin(user_id: str, channel: str, payload: dict):
    if DEBUG_ADMIN_PUSH:
        logging.info("[DEBUG] push_with_admin -> user=%s, channel=%s, payload=%s", user_id, channel, payload)
        logging.info("[DEBUG] active admin connections = %d", len(admin_connections))

    if payload.get("sender") != "user":
        await ws_manager.push(user_id, channel, payload)

    enriched = {
        "user_id": user_id,
        "channel": channel,
        "sender": payload.get("sender", ""),
        "text": payload.get("text", ""),
        "type": payload.get("type", ""),
        "ts": payload.get("ts") or datetime.datetime.utcnow().isoformat() + "Z",
    }

    # Broadcast to all authenticated admin connections
    # Create snapshot of connections to avoid lock during send
    async with admin_connections_lock:
        connections_snapshot = list(admin_connections)
    
    failed_connections = []
    for connection in connections_snapshot:
        try:
            ws = connection["ws"]
            await ws.send_json(enriched)
        except Exception as e:
            logging.warning(f"[push_with_admin] Failed to send to {connection.get('email', 'unknown')}: {e}")
            failed_connections.append(connection)
    
    # Remove failed connections
    if failed_connections:
        async with admin_connections_lock:
            for conn in failed_connections:
                try:
                    admin_connections.remove(conn)
                except ValueError:
                    pass  # Already removed

# ========================
# Escalation Loop
# ========================
async def escalation_loop():
    await asyncio.sleep(5)  # startup delay
    while True:
        try:
            now = datetime.datetime.utcnow()
            with db() as conn:
                c = conn.cursor()
                c.execute("SELECT user_id, channel, assigned_staff, updated_at, patience_sent, final_sent, escalation_active FROM conversations WHERE open=1")
                rows = c.fetchall()

            for row in rows:
                assigned = row["assigned_staff"]
                updated_at = row["updated_at"]
                patience_sent = row["patience_sent"] or 0
                final_sent = row["final_sent"] or 0
                escalation_active = row.get("escalation_active", 1)  # Default to 1 for backward compatibility

                # Skip escalation if it's been terminated by staff reply
                if not escalation_active:
                    continue

                if not assigned and updated_at:
                    try:
                        last_update = datetime.datetime.fromisoformat(updated_at.replace("Z", ""))
                    except Exception:
                        continue
                    delta = (now - last_update).total_seconds()

                    # Step 1: 30s patience reply
                    if delta >= 30 and patience_sent == 0:
                        patience_text = "We are still trying to locate an available staff member, thank you for your patience."
                        add_message(row["user_id"], row["channel"], "system", patience_text)
                        await push_with_admin(
                            row["user_id"], row["channel"],
                            {"sender": "system", "text": patience_text,
                             "ts": datetime.datetime.utcnow().isoformat() + "Z"}
                        )
                        if twilio_client and row["channel"] in ("sms", "whatsapp"):
                            try:
                                to_number = row["user_id"]
                                from_number = TWILIO_NUMBER if row["channel"] == "sms" else f"whatsapp:{TWILIO_NUMBER}"
                                if row["channel"] == "whatsapp" and not to_number.startswith("whatsapp:"):
                                    to_number = f"whatsapp:{to_number}"
                                twilio_client.messages.create(body=patience_text, from_=from_number, to=to_number)
                            except Exception as e:
                                logging.exception(f"Twilio patience send failed: {repr(e)}")

                        with db() as conn:
                            conn.execute("UPDATE conversations SET patience_sent=1 WHERE user_id=? AND channel=?",
                                         (row["user_id"], row["channel"]))
                            conn.commit()
                        logging.info(f"Escalation: patience auto-reply sent to {row['user_id']} ({row['channel']})")

                    # Step 2: Final callback prompt
                    if delta >= ESCALATE_AFTER_SECONDS and final_sent == 0:
                        final_text = "All staff are currently assisting others. Please leave your message and contact info, and a team member will respond as soon as possible."
                        add_message(row["user_id"], row["channel"], "system", final_text)
                        await push_with_admin(
                            row["user_id"], row["channel"],
                            {"sender": "system", "text": final_text,
                             "ts": datetime.datetime.utcnow().isoformat() + "Z"}
                        )
                        if twilio_client and row["channel"] in ("sms", "whatsapp"):
                            try:
                                to_number = row["user_id"]
                                from_number = TWILIO_NUMBER if row["channel"] == "sms" else f"whatsapp:{TWILIO_NUMBER}"
                                if row["channel"] == "whatsapp" and not to_number.startswith("whatsapp:"):
                                    to_number = f"whatsapp:{to_number}"
                                twilio_client.messages.create(body=final_text, from_=from_number, to=to_number)
                            except Exception as e:
                                logging.exception(f"Twilio final send failed: {repr(e)}")

                        with db() as conn:
                            conn.execute("UPDATE conversations SET final_sent=1 WHERE user_id=? AND channel=?",
                                         (row["user_id"], row["channel"]))
                            conn.commit()
                        logging.info(f"Escalation: final callback prompt sent to {row['user_id']} ({row['channel']})")

                        # SMS manager alert if BACKUP_NUMBER is set
                        if twilio_client and BACKUP_NUMBER:
                            try:
                                alert_text = (
                                    f"[Escalation Alert] Conversation with {row['user_id']} "
                                    f"({row['channel']}) has escalated. Visitor was asked to leave contact info."
                                )
                                twilio_client.messages.create(
                                    body=alert_text,
                                    from_=TWILIO_NUMBER,
                                    to=BACKUP_NUMBER
                                )
                                logging.info(f"Escalation alert SMS sent to manager at {BACKUP_NUMBER}")
                            except Exception as e:
                                logging.exception(f"Failed to send escalation alert SMS: {repr(e)}")

        except Exception as e:
            logging.exception("Error in escalation_loop", exc_info=e)
        await asyncio.sleep(30)
# ============================================================================
# PUSH NOTIFICATION ENDPOINTS
# ============================================================================

# Store for admin push tokens (in production, use database)
admin_push_tokens = {}

@app.post("/admin/api/push-token", dependencies=[Depends(require_role(["admin", "staff"]))])
def register_push_token(request: Request):
    """Register admin's Expo push notification token"""
    import json
    data = json.loads(request._body.decode() if hasattr(request, '_body') else '{}')
    
    push_token = data.get('push_token')
    if not push_token:
        raise HTTPException(status_code=400, detail="push_token is required")
    
    # Get user info from JWT token
    user = request.state.user
    user_id = user.get('id') or user.get('email')
    
    # Store the push token
    admin_push_tokens[user_id] = push_token
    
    print(f"✅ Registered push token for {user_id}: {push_token[:50]}...")
    
    return {"success": True, "message": "Push token registered"}


async def send_push_notification(expo_token: str, title: str, body: str, data: dict = None):
    """
    Send push notification via Expo Push Notification service
    
    Args:
        expo_token: Expo push token (ExponentPushToken[...])
        title: Notification title
        body: Notification body
        data: Optional data payload
    """
    import httpx
    
    message = {
        "to": expo_token,
        "sound": "default",
        "title": title,
        "body": body,
        "data": data or {},
        "priority": "high",
        "channelId": "dwc-admin-messages"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://exp.host/--/api/v2/push/send",
                json=message,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Push notification sent: {result}")
                return result
            else:
                print(f"❌ Failed to send push notification: {response.text}")
                return None
    except Exception as e:
        print(f"❌ Error sending push notification: {e}")
        return None


async def notify_admins_new_message(user_id: str, channel: str, message_text: str):
    """Send push notifications to all registered admin devices"""
    if not admin_push_tokens:
        print("No admin push tokens registered")
        return
    
    title = f"New message from {user_id}"
    body = message_text[:100]  # Truncate long messages
    data = {
        "type": "new_message",
        "user_id": user_id,
        "channel": channel
    }
    
    # Send to all registered admin tokens
    for admin_id, token in admin_push_tokens.items():
        print(f"📤 Sending push notification to {admin_id}")
        await send_push_notification(token, title, body, data)

