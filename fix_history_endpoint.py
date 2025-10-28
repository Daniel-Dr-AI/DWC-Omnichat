#!/usr/bin/env python3
"""
Fix the history endpoint to return complete data for display
"""

with open('server.py', 'r') as f:
    content = f.read()

old_code = '''@app.get("/admin/api/history", dependencies=[Depends(require_role(["admin"]))])
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

    return {"conversations": combined}'''

new_code = '''@app.get("/admin/api/history", dependencies=[Depends(require_role(["admin"]))])
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

    return {"history": combined}'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('server.py', 'w') as f:
        f.write(content)
    print("✅ History endpoint updated successfully")
else:
    print("❌ Could not find old code to replace")
    print("Endpoint may already be updated or code structure changed")
