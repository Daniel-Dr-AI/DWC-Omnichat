#!/usr/bin/env python3
"""
Migration: Add 'viewed' column to followups table
This allows tracking which followups have been opened by admins
"""

import sqlite3

DB_PATH = "handoff.sqlite"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Check if column already exists
    cols = [row[1] for row in c.execute("PRAGMA table_info(followups)").fetchall()]

    if 'viewed' not in cols:
        print("Adding 'viewed' column to followups table...")
        c.execute("ALTER TABLE followups ADD COLUMN viewed INTEGER DEFAULT 0")
        conn.commit()
        print("✅ Migration complete - 'viewed' column added")
    else:
        print("ℹ️  'viewed' column already exists, skipping migration")

    # Show current schema
    print("\nCurrent followups schema:")
    for row in c.execute("PRAGMA table_info(followups)").fetchall():
        print(f"  {row[1]}: {row[2]}")

    # Show count of unviewed followups
    unviewed = c.execute("SELECT COUNT(*) FROM followups WHERE viewed = 0").fetchone()[0]
    total = c.execute("SELECT COUNT(*) FROM followups").fetchone()[0]
    print(f"\nFollowup stats:")
    print(f"  Total: {total}")
    print(f"  Unviewed: {unviewed}")
    print(f"  Viewed: {total - unviewed}")

    conn.close()

if __name__ == "__main__":
    migrate()
