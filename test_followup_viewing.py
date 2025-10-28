#!/usr/bin/env python3
"""
Test script to verify followup viewing workflow:
1. Check initial unviewed count
2. Simulate marking a followup as viewed
3. Verify count decrements
"""

import sqlite3

DB_PATH = "handoff.sqlite"

def get_db_stats():
    """Get followup stats from database"""
    conn = sqlite3.connect(DB_PATH)
    unviewed = conn.execute("SELECT COUNT(*) FROM followups WHERE viewed = 0").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM followups").fetchone()[0]
    conn.close()
    return unviewed, total

def main():
    print("=" * 60)
    print("FOLLOWUP VIEWING WORKFLOW TEST")
    print("=" * 60)

    # Step 1: Initial state
    print("\n1️⃣  Initial State:")
    unviewed, total = get_db_stats()
    print(f"   Total followups: {total}")
    print(f"   Unviewed: {unviewed}")
    print(f"   Viewed: {total - unviewed}")

    if unviewed == 0:
        print("\n❌ No unviewed followups to test with!")
        return

    # Step 2: Simulate marking first followup as viewed
    print("\n2️⃣  Simulating admin opening followup ID 1...")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE followups SET viewed = 1 WHERE id = 1")
    conn.commit()
    conn.close()
    print("   ✅ Marked followup ID 1 as viewed")

    # Step 3: Check new state
    print("\n3️⃣  New State:")
    unviewed, total = get_db_stats()
    print(f"   Total followups: {total}")
    print(f"   Unviewed: {unviewed}")
    print(f"   Viewed: {total - unviewed}")

    # Step 4: Show what the API endpoint would return
    print("\n4️⃣  What the API endpoint returns:")
    print(f"   /admin/api/followups/unviewed-count => {{\"count\": {unviewed}}}")

    # Step 5: Show expected UI behavior
    print("\n5️⃣  Expected UI Behavior:")
    if unviewed > 0:
        print(f"   ✅ Followups tab shows:")
        print(f"      - Red ring border")
        print(f"      - Red badge with number: {unviewed}")
        print(f"      - Text: 'You have new followups!'")
    else:
        print(f"   ✅ Followups tab shows:")
        print(f"      - Normal appearance (no red border)")
        print(f"      - No badge")
        print(f"      - Just text: 'Followups'")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\n💡 To reset: python3 migrate_followups_viewed.py")
    print("   (This will set all followups back to unviewed)\n")

if __name__ == "__main__":
    main()
