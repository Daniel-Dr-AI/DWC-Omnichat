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
import os, logging, datetime, itertools, json, sqlite3, httpx, asyncio
from logging.handlers import RotatingFileHandler
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Dict, List, Set

# ========================
# Load env & App
# ========================
load_dotenv()

app = FastAPI()

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "")

allowed_origins = ["*"]
if FRONTEND_ORIGIN:
    allowed_origins = [FRONTEND_ORIGIN, "https://dwc-omnichat.onrender.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static + Templates (Admin UI)
if Path("static").exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


# ========================
# Logging (rotating file)
# ========================
log_handler = RotatingFileHandler("chat.log", maxBytes=1_000_000, backupCount=5)
logging.basicConfig(handlers=[log_handler], level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ========================
# Twilio / Meta / Config
# ========================
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")    # E.164, e.g. +15551234567
VERIFY_TWILIO_SIGNATURE = os.getenv("VERIFY_TWILIO_SIGNATURE", "0") == "1"
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")

twilio_client = TwilioClient(ACCOUNT_SID, AUTH_TOKEN) if (ACCOUNT_SID and AUTH_TOKEN) else None
twilio_validator = RequestValidator(AUTH_TOKEN) if (AUTH_TOKEN) else None

FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
FB_VERIFY_TOKEN = os.getenv("FB_VERIFY_TOKEN", "")

BACKUP_NUMBER = os.getenv("BACKUP_NUMBER")  # optional
AUTO_CLOSE_MINUTES = int(os.getenv("AUTO_CLOSE_MINUTES", "30"))
ESCALATE_AFTER_SECONDS = int(os.getenv("ESCALATE_AFTER_SECONDS", "300"))

# ========================
# Shift routing (JSON)
# ========================
SHIFT_CONFIG_PATH = Path("shift_config.json")

def load_shift_config():
    if SHIFT_CONFIG_PATH.exists():
        # use utf-8-sig so BOM won't break json.load
        with open(SHIFT_CONFIG_PATH, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return [
        {
            "name": "default",
            "start": "00:00",
            "end": "23:59",
            "numbers": [TWILIO_NUMBER]
        }
    ]


def parse_hhmm(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)

SHIFT_ROTA = load_shift_config()
for s in SHIFT_ROTA:
    s["start_min"] = parse_hhmm(s["start"])
    s["end_min"]   = parse_hhmm(s["end"])
    s["cycle"]     = itertools.cycle(s["numbers"])

def select_staff_number(now=None) -> str:
    now = now or datetime.datetime.now(datetime.timezone.utc)
    mins = now.hour * 60 + now.minute
    for s in SHIFT_ROTA:
        if s["start_min"] <= s["end_min"]:
            in_window = s["start_min"] <= mins < s["end_min"]
        else:
            in_window = mins >= s["start_min"] or mins < s["end_min"]
        if in_window and s["numbers"]:
            chosen = next(s["cycle"])
            logging.info(f"Shift '{s['name']}' -> {chosen}")
            return chosen
    return SHIFT_ROTA[0]["numbers"][0]

# ========================
# SQLite persistence
# ========================
DB_PATH = Path("handoff.sqlite")

@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def db_init():
    with db() as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS conversations (
            user_id TEXT,
            channel TEXT,
            assigned_staff TEXT,
            open INTEGER NOT NULL DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            PRIMARY KEY (user_id, channel)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            channel TEXT,
            sender TEXT,  -- 'user' | 'staff' | 'system'
            text TEXT,
            ts TEXT
        )""")
        conn.commit()

def ensure_conversation(user_id: str, channel: str):
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM conversations WHERE user_id=? AND channel=?", (user_id, channel))
        if not c.fetchone():
            # New conversations should start as open=1 so they appear in admin dashboard
            c.execute(
                "INSERT INTO conversations (user_id, channel, assigned_staff, open, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, channel, None, 1, ts, ts)
            )
            conn.commit()



def set_assignment(user_id: str, channel: str, staff_number: Optional[str], open_state: bool):
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    with db() as conn:
        c = conn.cursor()
        c.execute("UPDATE conversations SET assigned_staff=?, open=?, updated_at=? WHERE user_id=? AND channel=?",
                  (staff_number, 1 if open_state else 0, ts, user_id, channel))
        conn.commit()

def add_message(user_id: str, channel: str, sender: str, text: str):
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    with db() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO messages (user_id, channel, sender, text, ts) VALUES (?, ?, ?, ?, ?)",
                  (user_id, channel, sender, text, ts))
        c.execute("UPDATE conversations SET updated_at=? WHERE user_id=? AND channel=?", (ts, user_id, channel))
        conn.commit()

def get_messages(user_id: str, channel: str):
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT sender, text, ts FROM messages WHERE user_id=? AND channel=? ORDER BY id ASC", (user_id, channel))
        rows = c.fetchall()
        c.execute("SELECT assigned_staff, open, updated_at FROM conversations WHERE user_id=? AND channel=?", (user_id, channel))
        convo = c.fetchone()
    return {
        "assigned_staff": convo["assigned_staff"] if convo else None,
        "open": bool(convo["open"]) if convo else False,
        "last_updated": convo["updated_at"] if convo else None,
        "messages": [dict(r) for r in rows]
    }

def latest_user_for_staff(staff_number: str) -> Optional[tuple]:
    with db() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT user_id, channel FROM conversations
            WHERE assigned_staff=? AND open=1
            ORDER BY updated_at DESC
            LIMIT 1
        """, (staff_number,))
        row = c.fetchone()
        return (row["user_id"], row["channel"]) if row else None

# ========================
# Webchat REST endpoint (for widget)
# ========================
@app.post("/webchat")
async def webchat_post(msg: PostMessageSchema):
    reply = await route_user_text(msg.user_id, "webchat", msg.text)
    await ws_manager.push(
        msg.user_id,
        "webchat",
        {"sender": "system", "text": reply, "ts": datetime.datetime.utcnow().isoformat() + "Z"}
    )
    return {"status": "ok", "message": reply}

# ========================
# WebSocket manager (webchat)
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
# Helpers: trim/escalate/auto-close, rate-limit
# ========================
def trim_message(text: str, limit: int = 160) -> str:
    return text if len(text) <= limit else text[: max(0, limit-3) ] + "..."

def escalate_if_needed(user_id: str, channel: str):
    if not BACKUP_NUMBER or not twilio_client:
        return
    convo = get_messages(user_id, channel)
    if not convo["open"]:
        return
    last_updated = datetime.datetime.fromisoformat((convo["last_updated"] or "1970-01-01T00:00:00").replace("Z", ""))
    if (datetime.datetime.utcnow() - last_updated).total_seconds() > ESCALATE_AFTER_SECONDS:
        body = f"Escalation: user {user_id} on {channel} waiting."
        try:
            twilio_client.messages.create(from_=TWILIO_NUMBER, to=BACKUP_NUMBER, body=body)
        except Exception as e:
            logging.exception("Escalation SMS failed")

def auto_close_inactive(user_id: str, channel: str, minutes: int = None):
    minutes = minutes or AUTO_CLOSE_MINUTES
    convo = get_messages(user_id, channel)
    if convo["open"] and convo["last_updated"]:
        last_updated = datetime.datetime.fromisoformat(convo["last_updated"].replace("Z", ""))
        if (datetime.datetime.utcnow() - last_updated).total_seconds() > minutes * 60:
            set_assignment(user_id, channel, None, False)
            logging.info(f"Auto-closed inactive conversation: {user_id} [{channel}]")

RATE_WINDOW_SECONDS = int(os.getenv("RATE_WINDOW_SECONDS", "10"))
RATE_MAX_HITS = int(os.getenv("RATE_MAX_HITS", "6"))
_rate_cache: Dict[str, List[float]] = {}

def rate_check(user_id: str, channel: str) -> bool:
    now = datetime.datetime.utcnow().timestamp()
    key = f"{user_id}|{channel}"
    hits = _rate_cache.get(key, [])
    hits = [t for t in hits if now - t < RATE_WINDOW_SECONDS]
    hits.append(now)
    _rate_cache[key] = hits
    return len(hits) <= RATE_MAX_HITS

# ========================
# Unified send helper
# ========================
async def send_outbound(to_channel: str, to_id: str, text: str):
    text = trim_message(text)
    if to_channel in ("sms", "whatsapp"):
        if not twilio_client:
            logging.warning("Twilio not configured; cannot send.")
            return
        dest = to_id
        try:
            if to_channel == "whatsapp" and not to_id.startswith("whatsapp:"):
                dest = f"whatsapp:{to_id}"
            twilio_client.messages.create(
                from_=TWILIO_NUMBER if to_channel=="sms" else f"whatsapp:{TWILIO_NUMBER}",
                to=dest,
                body=text
            )
        except Exception:
            logging.exception("Twilio outbound failed")
    elif to_channel == "messenger":
        if not FB_PAGE_ACCESS_TOKEN:
            logging.warning("Messenger token missing; cannot send.")
            return
        url = "https://graph.facebook.com/v19.0/me/messages"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(url, params={"access_token": FB_PAGE_ACCESS_TOKEN},
                                  json={"recipient": {"id": to_id}, "message": {"text": text}})
        except Exception:
            logging.exception("Messenger outbound failed")
    elif to_channel == "webchat":
        await ws_manager.push(to_id, "webchat", {"sender": "staff", "text": text, "ts": datetime.datetime.utcnow().isoformat()+"Z"})

# ========================
# Handoff core
# ========================
def start_handoff(user_id: str, channel: str, initial_text: Optional[str] = None) -> str:
    ensure_conversation(user_id, channel)
    staff_number = select_staff_number()
    set_assignment(user_id, channel, staff_number, True)
    add_message(user_id, channel, "system", f"Handoff started to {staff_number}.")
    if initial_text:
        add_message(user_id, channel, "user", initial_text)
    if twilio_client:
        try:
            twilio_client.messages.create(from_=TWILIO_NUMBER, to=staff_number,
                                          body=trim_message(f"📩 New {channel}. Msg: {initial_text or ''}"))
        except Exception:
            logging.exception("Notify staff failed")
    return staff_number

async def route_user_text(user_id: str, channel: str, text: str) -> str:
    ensure_conversation(user_id, channel)
    auto_close_inactive(user_id, channel)
    if not rate_check(user_id, channel):
        return "Too many messages; please slow down."
    add_message(user_id, channel, "user", text)

    convo = get_messages(user_id, channel)
    if text.strip().lower() in ("human", "agent", "staff", "appointment"):
        staff = start_handoff(user_id, channel, initial_text=text)
        escalate_if_needed(user_id, channel)
        return "You're being connected to a staff member."
    if convo["open"] and convo["assigned_staff"]:
        if twilio_client:
            try:
                twilio_client.messages.create(from_=TWILIO_NUMBER, to=convo["assigned_staff"],
                                              body=trim_message(f"{channel}:{user_id}: {text}"))
            except Exception:
                logging.exception("Forward to staff failed")
        escalate_if_needed(user_id, channel)
        return "Message sent to staff."
    return "Reply 'human' to connect with a staff member."

# ========================
# Schemas
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
# Startup & Health
# ========================
@app.on_event("startup")
def on_startup():
    db_init()
    logging.info("DB initialized.")
    if ACCOUNT_SID and AUTH_TOKEN and TWILIO_NUMBER:
        logging.info("Twilio configured [OK]")
    else:
        logging.warning("Twilio not fully configured (SMS/WhatsApp will be limited) [X]")
    if FB_PAGE_ACCESS_TOKEN:
        logging.info("Messenger configured [OK]…")

@app.get("/health")
def health():
    return {
        "status": "running",
        "twilio": bool(ACCOUNT_SID and AUTH_TOKEN and TWILIO_NUMBER),
        "messenger": bool(FB_PAGE_ACCESS_TOKEN),
        "db": str(DB_PATH),
        "shifts": [s["name"] for s in SHIFT_ROTA]
    }

@app.get("/")
def root():
    return {"message": "DWC Omnichat live (SMS/WhatsApp/Messenger/Webchat + Admin)."}

# ========================
# Webchat WebSocket
# ========================
@app.websocket("/ws/{user_id}")
async def ws_endpoint(websocket: WebSocket, user_id: str):
    await ws_manager.connect(user_id, "webchat", websocket)
    try:
        while True:
            # Keep the connection alive (no data expected from client directly)
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id, "webchat", websocket)
        logging.info(f"WebSocket disconnected for user {user_id}")

# ========================
# SMS & WhatsApp via Twilio
# ========================
@app.post("/sms")
async def sms_webhook(request: Request):
    if VERIFY_TWILIO_SIGNATURE and twilio_validator:
        signature = request.headers.get("X-Twilio-Signature", "")
        url = (PUBLIC_BASE_URL.rstrip("/") + str(request.url.path)) if PUBLIC_BASE_URL else str(request.url)
        form_a = await request.form()
        form = dict(form_a.items())
        if not twilio_validator.validate(url, form, signature):
            logging.warning("Twilio signature validation failed.")
            return PlainTextResponse("Invalid signature", status_code=403)

    form = await request.form()
    From = form.get("From", "")
    Body = form.get("Body", "")

    if From.startswith("whatsapp:"):
        user_id = From.replace("whatsapp:", "")
        channel = "whatsapp"
    else:
        user_id = From
        channel = "sms"

    reply = await route_user_text(user_id, channel, Body)
    resp = MessagingResponse()
    resp.message(trim_message(reply))
    return Response(content=str(resp), media_type="application/xml")

# ========================
# Messenger webhook (verify + inbound)
# ========================
@app.get("/messenger")
def messenger_verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == FB_VERIFY_TOKEN:
        return PlainTextResponse(challenge or "")
    return PlainTextResponse("forbidden", status_code=403)

@app.post("/messenger")
async def messenger_receive(payload: dict):
    try:
        for entry in payload.get("entry", []):
            for event in entry.get("messaging", []):
                sender = event.get("sender", {}).get("id")
                message = event.get("message", {}).get("text", "")
                if sender and message:
                    reply = await route_user_text(sender, "messenger", message)
                    await send_outbound("messenger", sender, reply)
        return {"status": "ok"}
    except Exception:
        logging.exception("Messenger parse error")
        return JSONResponse({"error": "bad payload"}, status_code=400)

# ========================
# Handoff REST (generic)
# ========================
@app.post("/handoff/start")
def handoff_start(payload: StartHandoffSchema):
    staff = start_handoff(payload.user_id, payload.channel, payload.initial_message)
    return {"status": "ok", "assigned_staff": staff}

@app.post("/handoff/message")
async def handoff_message(payload: PostMessageSchema):
    ensure_conversation(payload.user_id, payload.channel)
    add_message(payload.user_id, payload.channel, "user", payload.text)
    convo = get_messages(payload.user_id, payload.channel)
    if convo["open"] and convo["assigned_staff"] and twilio_client:
        try:
            twilio_client.messages.create(from_=TWILIO_NUMBER, to=convo["assigned_staff"],
                                          body=trim_message(f"{payload.channel}:{payload.user_id}: {payload.text}"))
        except Exception:
            logging.exception("Forward to staff failed")
        return {"status": "sent_to_staff"}
    return {"status": "queued_or_closed"}

@app.post("/handoff/close")
def handoff_close(payload: StartHandoffSchema):
    ensure_conversation(payload.user_id, payload.channel)
    set_assignment(payload.user_id, payload.channel, None, False)
    add_message(payload.user_id, payload.channel, "system", "Handoff closed.")
    return {"status": "closed"}

@app.get("/handoff/messages/{channel}/{user_id}")
def handoff_messages(channel: str, user_id: str):
    ensure_conversation(user_id, channel)
    return get_messages(user_id, channel)

# ========================
# Admin Dashboard
# ========================

@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/admin/api/convos")
def admin_convos():
    with db() as conn:
        c = conn.cursor()
        # Show all conversations ordered by last update
        c.execute("SELECT * FROM conversations WHERE open=1 ORDER BY updated_at DESC")
        convos = [dict(r) for r in c.fetchall()]
    return {"conversations": convos}

@app.get("/admin/api/history")
def admin_history():
    with db() as conn:
        c = conn.cursor()
        # Only closed conversations
        c.execute("SELECT * FROM conversations WHERE open=0 ORDER BY updated_at DESC")
        convos = [dict(r) for r in c.fetchall()]
    return {"conversations": convos}

@app.get("/admin/api/messages/{channel}/{user_id}")
def admin_messages(channel: str, user_id: str):
    # Pass args in correct order: user_id first, then channel
    return get_messages(user_id, channel)

@app.post("/admin/api/send")
async def admin_send(payload: AdminSendSchema):
    add_message(payload.user_id, payload.channel, "staff", payload.text)
    await send_outbound(payload.channel, payload.user_id, payload.text)
    return {"status": "sent"}

# ========================
# Simulate (local testing)
# ========================
@app.post("/simulate")
async def simulate(payload: PostMessageSchema):
    reply = await route_user_text(payload.user_id, payload.channel, payload.text)
    return {"status": "ok", "message": reply}
