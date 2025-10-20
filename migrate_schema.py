# migrate_schema.py — full and working version (Extended Schema)
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "handoff.sqlite"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

def try_exec(sql):
    """Attempt to run a SQL statement and skip if it already exists."""
    try:
        cursor.execute(sql)
    except sqlite3.OperationalError as e:
        print(f"[skip] {sql.strip().splitlines()[0]} – {e}")

print(f"🔧 Migrating schema at: {DB_PATH}")

# ==========================================================
# CORE TABLES
# ==========================================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS tenants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL,
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'staff',
  created_at TEXT NOT NULL,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS conversation_metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL,
  conversation_id INTEGER NOT NULL,
  total_messages INTEGER NOT NULL DEFAULT 0,
  user_messages INTEGER NOT NULL DEFAULT 0,
  staff_messages INTEGER NOT NULL DEFAULT 0,
  first_response_seconds INTEGER,
  duration_seconds INTEGER,
  assigned_staff_id INTEGER,
  quality_score INTEGER,
  rating_comment TEXT,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER,
  conversation_id INTEGER,
  user_id INTEGER,
  type TEXT NOT NULL,
  payload TEXT,
  ts TEXT NOT NULL
)
""")

# ==========================================================
# ALTER EXISTING TABLES
# ==========================================================
alterations = [
    "ALTER TABLE conversations ADD COLUMN tenant_id INTEGER",
    "ALTER TABLE conversations ADD COLUMN assigned_staff_id INTEGER",
    "ALTER TABLE conversations ADD COLUMN created_at TEXT",
    "ALTER TABLE conversations ADD COLUMN first_user_message_at TEXT",
    "ALTER TABLE conversations ADD COLUMN first_staff_reply_at TEXT",
    "ALTER TABLE conversations ADD COLUMN closed_at TEXT",
    "ALTER TABLE conversations ADD COLUMN resolved INTEGER DEFAULT 0",
    "ALTER TABLE conversations ADD COLUMN last_staff_activity_at TEXT",
    "ALTER TABLE messages ADD COLUMN tenant_id INTEGER",
    "ALTER TABLE messages ADD COLUMN staff_id INTEGER",
]

for sql in alterations:
    try_exec(sql)

# ==========================================================
# EXTENDED TABLES
# ==========================================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS conversation_feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL,
  rating INTEGER CHECK(rating BETWEEN 1 AND 5),
  comment TEXT,
  ts TEXT NOT NULL,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS agent_metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  staff_id INTEGER NOT NULL,
  date TEXT NOT NULL,
  total_chats INTEGER DEFAULT 0,
  avg_response_seconds INTEGER,
  avg_duration_seconds INTEGER,
  avg_quality_score INTEGER,
  FOREIGN KEY (staff_id) REFERENCES users(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS ai_actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER,
  model TEXT,
  action_type TEXT,
  input_ref TEXT,
  output_ref TEXT,
  ts TEXT NOT NULL,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id)
)
""")

conn.commit()
conn.close()
print("✅ Extended schema migration complete.")
