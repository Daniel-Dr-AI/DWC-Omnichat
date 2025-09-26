from fastapi import FastAPI, Form, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, JSONResponse, PlainTextResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client as TwilioClient
from twilio.request_validator import RequestValidator
from dotenv import load_dotenv
import os, logging, datetime, sqlite3, asyncio
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Dict, Set

# ========================
# Load env & App
# ========================
load_dotenv()

app = FastAPI(title="DWC Omnichat")

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "")
allowed_origins = ["*"] if not FRONTEND_ORIGIN else [FRONTEND_ORIGIN, "https://dwc-omnichat.onrender.com"]

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

DB_PATH = "handoff.sqlite"
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
            escalated_count INTEGER DEFAULT 0,
            escalated_at TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT, channel TEXT,
            sender TEXT, text TEXT, ts TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT UNIQUE,
            role TEXT,
            available INTEGER,
            last_seen TEXT
        )""")
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
# Routes (truncated here, but continues as in your uploaded original)
# ========================
