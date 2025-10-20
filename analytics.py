
import json
import sqlite3
from datetime import datetime

def log_event(user_id: int, tenant_id: int, event_type: str, data: dict = None):
    try:
        conn = sqlite3.connect("handoff.sqlite")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO events (timestamp, user_id, tenant_id, event_type, data)
            VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            user_id,
            tenant_id,
            event_type,
            json.dumps(data or {})
        ))

        conn.commit()
        print(f"📊 Logged event: {event_type} for user {user_id}")
    except Exception as e:
        print(f"⚠️ Failed to log event: {e}")
    finally:
        conn.close()
