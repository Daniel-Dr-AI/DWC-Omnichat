
from fastapi import FastAPI, Form, HTTPException, Request, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import PlainTextResponse, HTMLResponse
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

if Path("static").exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Logging
log_handler = RotatingFileHandler("chat.log", maxBytes=1_000_000, backupCount=5)
console_handler = logging.StreamHandler()
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
BACKUP_NUMBER = os.getenv("BACKUP_NUMBER")
ESCALATE_AFTER_SECONDS = int(os.getenv("ESCALATE_AFTER_SECONDS", "120"))

twilio_client = None
twilio_validator = None
if ACCOUNT_SID and AUTH_TOKEN:
    twilio_client = TwilioClient(ACCOUNT_SID, AUTH_TOKEN)
    twilio_validator = RequestValidator(AUTH_TOKEN)

DB_PATH = "handoff.sqlite"

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
        c.execute("""CREATE TABLE IF NOT EXISTS callbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            channel TEXT,
            contact TEXT,
            message TEXT,
            ts TEXT,
            resolved INTEGER DEFAULT 0
        )""")
        conn.commit()

# ========================
# Models
# ========================
class PostMessageSchema(BaseModel):
    user_id: str
    channel: str = "webchat"
    text: str

# ========================
# Helpers
# ========================
def ensure_conversation(user_id: str, channel: str):
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM conversations WHERE user_id=? AND channel=?", (user_id, channel))
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

# ========================
# WS Manager
# ========================
class WSManager:
    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}
    def key(self, user_id, channel): return f"{user_id}|{channel}"
    async def connect(self, user_id, channel, ws: WebSocket):
        await ws.accept()
        self.connections.setdefault(self.key(user_id, channel), set()).add(ws)
    def disconnect(self, user_id, channel, ws: WebSocket):
        k = self.key(user_id, channel)
        if k in self.connections and ws in self.connections[k]:
            self.connections[k].remove(ws)
            if not self.connections[k]: del self.connections[k]
    async def push(self, user_id, channel, payload: dict):
        k = self.key(user_id, channel)
        for ws in list(self.connections.get(k, [])):
            try: await ws.send_json(payload)
            except Exception: self.disconnect(user_id, channel, ws)

ws_manager = WSManager()
admin_connections: Set[WebSocket] = set()

async def push_with_admin(user_id, channel, payload):
    await ws_manager.push(user_id, channel, payload)
    for ws in list(admin_connections):
        try: await ws.send_json({"user_id": user_id, "channel": channel, **payload})
        except Exception: admin_connections.remove(ws)

# ========================
# Escalation loop
# ========================
async def escalation_loop():
    while True:
        try:
            now = datetime.datetime.utcnow()
            threshold = now - datetime.timedelta(seconds=ESCALATE_AFTER_SECONDS)
            with db() as conn:
                c = conn.cursor()
                c.execute("""SELECT user_id, channel, updated_at, escalated_count, escalated_at
                             FROM conversations
                             WHERE open=1 AND (assigned_staff IS NULL OR assigned_staff='')
                               AND (escalated_count IS NULL OR escalated_count < 4)""")
                for r in c.fetchall():
                    last_ts = datetime.datetime.fromisoformat(r["updated_at"].replace("Z", ""))
                    last_esc = None
                    if r["escalated_at"]:
                        try: last_esc = datetime.datetime.fromisoformat(r["escalated_at"].replace("Z", ""))
                        except: pass
                    if last_ts < threshold and (not last_esc or last_esc < threshold):
                        count = (r["escalated_count"] or 0) + 1
                        if count <= 3:
                            with db() as conn2:
                                conn2.execute("UPDATE conversations SET escalated_count=?, escalated_at=? WHERE user_id=? AND channel=?",
                                              (count, datetime.datetime.utcnow().isoformat()+"Z", r["user_id"], r["channel"]))
                                conn2.commit()
                            if twilio_client and BACKUP_NUMBER:
                                try:
                                    twilio_client.messages.create(body=f"Escalation {count}/3: {r['user_id']} on {r['channel']}",
                                                                  from_=TWILIO_NUMBER, to=BACKUP_NUMBER)
                                except Exception as e: logging.exception(e)
                        else:
                            auto_msg = "All staff members are currently assisting patients. Would you like to leave your callback number or email and your question? We will respond shortly."
                            add_message(r["user_id"], r["channel"], "system", auto_msg)
                            await push_with_admin(r["user_id"], r["channel"], {"sender":"system","text":auto_msg,"ts":datetime.datetime.utcnow().isoformat()+"Z"})
                            with db() as conn2:
                                conn2.execute("UPDATE conversations SET escalated_count=999 WHERE user_id=? AND channel=?",(r["user_id"],r["channel"]))
                                conn2.commit()
        except Exception as e: logging.exception("Escalation loop error")
        await asyncio.sleep(30)

@app.on_event("startup")
async def on_startup():
    db_init()
    asyncio.create_task(escalation_loop())

# ========================
# Routes
# ========================
@app.get("/admin/api/callbacks")
def get_callbacks():
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM callbacks WHERE resolved=0 ORDER BY ts DESC")
        return {"callbacks":[dict(r) for r in c.fetchall()]}

@app.post("/admin/api/callbacks/resolve")
def resolve_callback(data: dict = Body(...)):
    cb_id = data.get("id")
    with db() as conn:
        c = conn.cursor()
        c.execute("UPDATE callbacks SET resolved=1 WHERE id=?", (cb_id,))
        conn.commit()
    return {"status":"resolved","id":cb_id}

@app.post("/webchat")
async def webchat_post(msg: PostMessageSchema):
    ensure_conversation(msg.user_id, msg.channel)
    add_message(msg.user_id, msg.channel, "user", msg.text)
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT escalated_count FROM conversations WHERE user_id=? AND channel=?", (msg.user_id,msg.channel))
        row = c.fetchone()
        if row and row["escalated_count"]==999:
            c.execute("INSERT INTO callbacks (user_id,channel,message,ts) VALUES (?,?,?,?)",
                      (msg.user_id,msg.channel,msg.text,datetime.datetime.utcnow().isoformat()+"Z"))
            conn.commit()
            await push_with_admin(msg.user_id,msg.channel,{"sender":"system","text":"📌 Callback request saved.","ts":datetime.datetime.utcnow().isoformat()+"Z"})
    await push_with_admin(msg.user_id,msg.channel,{"sender":"user","text":msg.text,"ts":datetime.datetime.utcnow().isoformat()+"Z"})
    return {"status":"ok"}

@app.post("/sms")
async def sms_webhook(request: Request, From: str = Form(...), Body: str = Form(...)):
    user_id=From; channel="whatsapp" if From.startswith("whatsapp:") else "sms"; text=Body.strip()
    ensure_conversation(user_id, channel)
    add_message(user_id, channel, "user", text)
    with db() as conn:
        c=conn.cursor()
        c.execute("SELECT escalated_count FROM conversations WHERE user_id=? AND channel=?", (user_id,channel))
        row=c.fetchone()
        if row and row["escalated_count"]==999:
            c.execute("INSERT INTO callbacks (user_id,channel,message,ts) VALUES (?,?,?,?)",
                      (user_id,channel,text,datetime.datetime.utcnow().isoformat()+"Z"))
            conn.commit()
            await push_with_admin(user_id,channel,{"sender":"system","text":"📌 Callback request saved.","ts":datetime.datetime.utcnow().isoformat()+"Z"})
    await push_with_admin(user_id,channel,{"sender":"user","text":text,"ts":datetime.datetime.utcnow().isoformat()+"Z"})
    resp=MessagingResponse(); resp.message("Thanks, we got your message!")
    return PlainTextResponse(str(resp), media_type="application/xml")

@app.websocket("/ws/{user_id}")
async def ws_endpoint(websocket: WebSocket,user_id:str):
    await ws_manager.connect(user_id,"webchat",websocket)
    try:
        while True: await asyncio.sleep(30)
    except WebSocketDisconnect: ws_manager.disconnect(user_id,"webchat",websocket)

@app.websocket("/ws/admin-dashboard")
async def ws_admin(websocket: WebSocket):
    await websocket.accept(); admin_connections.add(websocket)
    try:
        while True: await asyncio.sleep(30)
    except WebSocketDisconnect:
        if websocket in admin_connections: admin_connections.remove(websocket)
