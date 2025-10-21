from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, WebSocketException, HTTPException, UploadFile, File, Form, Depends, Query, status
from fastapi.responses import Response, JSONResponse, PlainTextResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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
else:from fastapi.openapi.utils import get_openapi
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

DB_PATH = str(Path(__file__).parent / "handoff.sqlite")

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
        "http://127.0.0.1:5173"
    ]
    logging.info(f"✅ CORS configured for origins: {', '.join(allowed_origins)}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static + Templates
if Path("static").exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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

# Use Render's persistent disk if available, otherwise local file
if os.path.exists("/data"):
    DB_PATH = "/data/handoff.sqlite"
else:
    DB_PATH = str(Path(__file__).parent / "handoff.sqlite")
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
        c.execute("""CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT, channel TEXT,
            assigned_staff TEXT,
            open INTEGER, updated_at TEXT,
            patience_sent INTEGER DEFAULT 0,
            final_sent INTEGER DEFAULT 0
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
            name TEXT, contact TEXT,
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

        conn.commit()

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
    name: str
    contact: str
    message: str

# ========================
# Conversation Helpers
# ========================
def ensure_conversation(user_id: str, channel: str):
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM conversations WHERE user_id=? AND channel=?",
                  (user_id, channel))
        row = c.fetchone()
        if not row:
            c.execute("INSERT INTO conversations (user_id, channel, assigned_staff, open, updated_at) VALUES (?,?,?,?,?)",
                      (user_id, channel, None, 1, ts))
        else:
            c.execute("UPDATE conversations SET open=1, updated_at=? WHERE user_id=? AND channel=?",
                      (ts, user_id, channel))
        conn.commit()

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
    """
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
    logging.info("DB initialized and escalation loop starting.")
    logging.info(f"Env check: SID={'set' if ACCOUNT_SID else 'missing'}, "
                 f"Token={'set' if AUTH_TOKEN else 'missing'}, "
                 f"Number={TWILIO_NUMBER}, "
                 f"Client={'ready' if twilio_client else 'NONE'}")
    asyncio.create_task(escalation_loop())

@app.get("/health")
def health():
    return {"status": "running", "db": str(DB_PATH), "shifts": [s["name"] for s in SHIFT_ROTA]}

# Admin dashboard
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

# Admin API
@app.get("/admin/api/convos", dependencies=[Depends(require_role(["admin", "staff"]))])
def admin_convos():
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM conversations WHERE open=1 ORDER BY updated_at DESC")
        rows = c.fetchall()
    return {"conversations": [dict(r) for r in rows]}

# ✅ Corrected: merged closed convos + migrated followups
@app.get("/admin/api/history", dependencies=[Depends(require_role(["admin"]))])
def admin_history():
    with db() as conn:
        c = conn.cursor()

        # Closed conversations from conversations table
        c.execute("""
            SELECT user_id, channel, updated_at, 'conversations' as source
            FROM conversations
            WHERE open=0
            ORDER BY updated_at DESC LIMIT 50
        """)
        convos = [dict(r) for r in c.fetchall()]

        # Migrated followups from history table
        c.execute("""
            SELECT user_id, channel, migrated_at as updated_at, 'history' as source
            FROM history
            ORDER BY migrated_at DESC LIMIT 50
        """)
        followup_histories = [dict(r) for r in c.fetchall()]

    # Merge and deduplicate: prefer the 'history' version if duplicate
    merged = {}
    for convo in convos + followup_histories:
        key = (convo["user_id"], convo["channel"])
        if key not in merged or convo.get("source") == "history":
            merged[key] = convo

    # Final sorted list by timestamp
    combined = list(merged.values())
    combined.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

    return {"conversations": combined}

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

@app.get("/admin/api/messages/{channel}/{user_id}", dependencies=[Depends(require_role(["admin", "staff"]))])
def admin_messages(channel: str, user_id: str):
    return get_messages(user_id, channel)


@app.post("/admin/api/send")
async def admin_send(msg: AdminSendSchema, user: TokenData = Depends(require_role(["admin", "staff"]))):
    add_message(msg.user_id, msg.channel, "staff", msg.text)
    # Reset escalation flag once staff replies
    with db() as conn:
        conn.execute("UPDATE conversations SET final_sent=0 WHERE user_id=? AND channel=?",
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
            "INSERT INTO followups (user_id, channel, name, contact, message, ts) VALUES (?,?,?,?,?,?)",
            (data.user_id, data.channel, data.name, data.contact, data.message, ts),
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
def handoff_close(data: StartHandoffSchema):
    set_assignment(data.user_id, data.channel, None, False)
    return {"status": "closed"}

# Webchat
@app.get("/webchat")
def webchat_check():
    return {"status": "ok"}

@app.post("/webchat")
async def webchat_post(msg: PostMessageSchema):
    channel = msg.channel or "webchat"

    ensure_conversation(msg.user_id, channel)
    add_message(msg.user_id, channel, "user", msg.text)

    # Broadcast the actual user message to admin dashboards
    await push_with_admin(msg.user_id, channel, {
        "sender": "user",
        "text": msg.text,
        "ts": datetime.datetime.utcnow().isoformat() + "Z"
    })

    # Immediate auto-reply for the visitor only
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
admin_connections: Set[Dict] = set()

@app.websocket("/admin-ws")
async def ws_admin(websocket: WebSocket, user: TokenData = Depends(get_websocket_token)):
    await websocket.accept()

    # Store connection with user metadata
    connection_info = {
        "ws": websocket,
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "tenant_id": user.tenant_id,
        "connected_at": datetime.datetime.utcnow().isoformat() + "Z"
    }
    admin_connections.add(connection_info)

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

                if ev_type in ("typing", "stop_typing") and user_id:
                    await ws_manager.push(user_id, channel, {
                        "type": ev_type,
                        "sender": "staff",
                        "ts": datetime.datetime.utcnow().isoformat() + "Z"
                    })

            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        # Remove connection by finding the matching dict entry
        admin_connections.discard(connection_info)
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
    for connection in list(admin_connections):
        try:
            ws = connection["ws"]
            await ws.send_json(enriched)
        except Exception as e:
            logging.warning(f"[push_with_admin] Failed to send to {connection.get('email', 'unknown')}: {e}")
            admin_connections.discard(connection)

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
                c.execute("SELECT user_id, channel, assigned_staff, updated_at, patience_sent, final_sent FROM conversations WHERE open=1")
                rows = c.fetchall()

            for row in rows:
                assigned = row["assigned_staff"]
                updated_at = row["updated_at"]
                patience_sent = row["patience_sent"] or 0
                final_sent = row["final_sent"] or 0

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