
import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "handoff.sqlite")

def migrate():
    print(f"🔧 Migrating schema at: {os.path.abspath(DB_PATH)}")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Tables: users, tenants, events, metrics
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            email TEXT NOT NULL UNIQUE,
            name TEXT,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            tenant_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            data TEXT
        );

        CREATE TABLE IF NOT EXISTS conversation_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            tenant_id INTEGER NOT NULL,
            avg_response_time REAL DEFAULT 0,
            messages_sent INTEGER DEFAULT 0,
            escalated BOOLEAN DEFAULT 0,
            updated_at TEXT
        );
        """)

    print("✅ Extended schema migration complete.")

if __name__ == "__main__":
    migrate()
