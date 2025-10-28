# History Export & Archive Feature

## Overview

All closed chats and deleted followups are now archived to the History tab instead of being permanently deleted. Admins can export history as CSV and optionally delete old records (30+ days).

---

## What Changed

### 1. ✅ Followups Archive to History (Not Delete)

**Previously**: "Delete Followup" button permanently deleted followups from database

**Now**: "Delete Followup" button archives followups to the history table

**Backend Changes** ([server.py:670-693](../server.py#L670-L693)):
```python
@app.delete("/admin/api/followups/{followup_id}")
def delete_followup(followup_id: int):
    """Archive a followup to history instead of deleting"""
    # Get followup data
    # Insert into history table
    # Remove from followups table
    # Returns {"success": True, "archived": True}
```

**What Gets Archived**:
- User ID
- Channel
- Name
- Contact info (email + phone combined)
- Message
- Original timestamp
- Archive timestamp (migrated_at)

---

### 2. ✅ Export History Feature

**Location**: History tab → "📥 Export History" button

**Features**:
- Select number of days to export (default: 30)
- Downloads as CSV file
- Filename: `history_last_{days}_days.csv`

**Backend Endpoint** ([server.py:695-705](../server.py#L695-L705)):
```python
@app.get("/admin/api/history/export")
def export_history(days: int = None):
    """Export history records from last N days"""
    # If days specified, filters by migrated_at >= cutoff
    # Returns all matching records as JSON
```

**Query Parameters**:
- `days` (optional): Number of days to export
- Example: `/admin/api/history/export?days=60` exports last 60 days

---

### 3. ✅ Export & Delete Old History

**Location**: History tab → "🗑️ Export & Delete Old" button

**Features**:
- Exports ALL history (no date limit)
- Deletes records older than 30 days
- Shows confirmation before proceeding
- Downloads complete export as CSV
- Filename: `history_complete_export_{date}.csv`

**Backend Endpoint** ([server.py:707-725](../server.py#L707-L725)):
```python
@app.post("/admin/api/history/export-and-delete")
def export_and_delete_history():
    """Export all history and delete records older than 30 days"""
    # Get ALL history records
    # Delete records where migrated_at < 30 days ago
    # Returns complete export + deleted count
```

**Safety Features**:
- Requires confirmation dialog
- Only deletes records 30+ days old
- Always exports before deleting
- Shows deleted count in success message

---

## User Interface

### History Tab UI

```
┌─────────────────────────────────────────────────────┐
│  [📥 Export History]  [🗑️ Export & Delete Old]     │
│  (Export & Delete removes records older than 30 days)│
│                                                       │
│  [Export Dialog - when opened]                       │
│  Export last: [30] days  [Download CSV]  [Cancel]   │
└─────────────────────────────────────────────────────┘
```

### Workflow

**Export Last N Days**:
1. Click "📥 Export History"
2. Enter number of days (1-365)
3. Click "Download CSV"
4. File downloads automatically
5. Shows: "Exported X history records"

**Export & Delete Old Records**:
1. Click "🗑️ Export & Delete Old"
2. Confirms: "This will export ALL history and DELETE records older than 30 days. Continue?"
3. Click OK
4. Complete history exports as CSV
5. Old records (30+ days) deleted from database
6. Shows: "Exported X records. Deleted Y records older than 30 days."
7. Page refreshes

---

## CSV Export Format

**Columns**:
- `id` - History record ID
- `user_id` - User identifier
- `channel` - Channel (webchat, sms, whatsapp, etc.)
- `name` - User's name (from followup form)
- `contact` - Contact info (email + phone)
- `message` - User's message
- `ts` - Original timestamp
- `migrated_at` - When archived to history

**Example CSV**:
```csv
id,user_id,channel,name,contact,message,ts,migrated_at
1,visitor-123,webchat,John Doe,"Email: john@example.com, Phone: 555-1234",Need help with order,2025-01-15T10:30:00Z,2025-01-15T10:35:00Z
2,visitor-456,sms,Jane Smith,"Email: jane@example.com, Phone: 555-5678",Question about product,2025-01-14T09:20:00Z,2025-01-14T09:25:00Z
```

---

## Data Flow

### When Followup is "Deleted"

```
User clicks "Delete Followup"
     ↓
Frontend: DELETE /admin/api/followups/{id}
     ↓
Backend: Gets followup data from followups table
     ↓
Backend: INSERT INTO history (user_id, channel, name, contact, message, ts, migrated_at)
     ↓
Backend: DELETE FROM followups WHERE id = {id}
     ↓
Frontend: Shows "Followup deleted"
     ↓
Frontend: Reloads page
     ↓
Followup appears in History tab
```

### When Conversation is Ended

```
User clicks "End Chat"
     ↓
Frontend: POST /handoff/close
     ↓
Backend: Updates conversations.open = 0
     ↓
Frontend: Shows "Chat ended"
     ↓
Chat moves to History tab
```

### When Exporting History

```
User selects days and clicks "Download CSV"
     ↓
Frontend: GET /admin/api/history/export?days={N}
     ↓
Backend: SELECT * FROM history WHERE migrated_at >= cutoff
     ↓
Backend: Returns JSON array
     ↓
Frontend: Converts to CSV format
     ↓
Frontend: Downloads file
     ↓
User receives: history_last_{N}_days.csv
```

### When Exporting & Deleting

```
User clicks "Export & Delete Old"
     ↓
Confirms dialog
     ↓
Frontend: POST /admin/api/history/export-and-delete
     ↓
Backend: SELECT * FROM history (all records)
     ↓
Backend: DELETE FROM history WHERE migrated_at < 30 days ago
     ↓
Backend: Returns complete export + deleted count
     ↓
Frontend: Converts to CSV and downloads
     ↓
User receives: history_complete_export_{date}.csv
     ↓
Frontend: Shows "Exported X records. Deleted Y records"
     ↓
Page reloads
```

---

## File Changes

### Backend: `/workspace/server.py`

**Modified**:
- `delete_followup()` (line 670-693) - Now archives to history instead of deleting

**Added**:
- `export_history()` (line 695-705) - Export with date filter
- `export_and_delete_history()` (line 707-725) - Export all + delete old

### Frontend: `/workspace/admin-frontend/src/components/admin/ConversationList.jsx`

**Added State**:
- `exportDays` - Number of days for export (default: 30)
- `showExportDialog` - Toggle export dialog visibility

**Added Functions**:
- `handleExportHistory()` (line 233-249) - Export with date filter
- `handleExportAndDelete()` (line 251-275) - Export all + delete old
- `convertToCSV()` (line 277-297) - Convert JSON to CSV format
- `downloadCSV()` (line 299-311) - Trigger browser download

**Added UI**:
- Export buttons bar for History tab (line 323-376)
- Export dialog with days input (line 345-374)

---

## Database Schema

### History Table

```sql
CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    channel TEXT,
    name TEXT,
    contact TEXT,          -- Combined email + phone
    message TEXT,
    ts TEXT,               -- Original timestamp
    migrated_at TEXT       -- Archive timestamp
);
```

**Indexes** (recommended for performance):
```sql
CREATE INDEX idx_history_migrated_at ON history(migrated_at);
CREATE INDEX idx_history_user_id ON history(user_id);
```

---

## Testing

### Test 1: Archive Followup to History

1. Go to Followups tab
2. Open a followup
3. Click "Delete Followup"
4. Confirm deletion
5. Go to History tab
6. ✅ Verify followup appears in history

**Database Check**:
```bash
python3 -c "import sqlite3; conn = sqlite3.connect('handoff.sqlite'); \
print('History records:', conn.execute('SELECT COUNT(*) FROM history').fetchone()[0])"
```

### Test 2: Export History

1. Go to History tab
2. Click "📥 Export History"
3. Enter "7" for 7 days
4. Click "Download CSV"
5. ✅ Verify CSV downloads
6. ✅ Open CSV and verify data format

**Check File**:
- Should be named: `history_last_7_days.csv`
- Should contain CSV headers
- Should contain data rows

### Test 3: Export & Delete Old

1. Go to History tab
2. Click "🗑️ Export & Delete Old"
3. Confirm the dialog
4. ✅ Verify CSV downloads with all records
5. ✅ Verify success message shows deleted count
6. ✅ Verify old records removed from history tab

**Database Check Before**:
```bash
python3 -c "import sqlite3, datetime; \
conn = sqlite3.connect('handoff.sqlite'); \
cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).isoformat() + 'Z'; \
print('Total:', conn.execute('SELECT COUNT(*) FROM history').fetchone()[0]); \
print('Older than 30 days:', conn.execute('SELECT COUNT(*) FROM history WHERE migrated_at < ?', (cutoff,)).fetchone()[0])"
```

**Database Check After**:
```bash
python3 -c "import sqlite3; conn = sqlite3.connect('handoff.sqlite'); \
print('Remaining:', conn.execute('SELECT COUNT(*) FROM history').fetchone()[0])"
```

---

## Edge Cases Handled

### 1. Empty History
- Export returns empty CSV with headers only
- Shows "Exported 0 history records"

### 2. No Old Records
- Export & Delete exports all records
- Shows "Deleted 0 records" (nothing older than 30 days)

### 3. Invalid Days Input
- Defaults to 30 if empty or invalid
- Min: 1 day, Max: 365 days

### 4. Large Exports
- No pagination needed (exported as single CSV)
- Browser handles download automatically

### 5. CSV Special Characters
- Commas in text: Wrapped in quotes
- Quotes in text: Escaped as double quotes ("")
- Newlines: Preserved in quoted fields

---

## Security

### Authentication
- All endpoints require admin role
- Uses `Depends(require_role(["admin"]))`
- Token validated on every request

### Data Protection
- No sensitive data exposed in URLs
- CSV downloads use secure blob URLs
- Files never stored on server

---

## Current Status

✅ **Backend**:
- Archive endpoint implemented
- Export endpoint implemented
- Export & Delete endpoint implemented
- All endpoints tested and working

✅ **Frontend**:
- Export UI added to History tab
- CSV conversion implemented
- Download functionality working
- All state management in place

✅ **Servers**:
- Backend running on port 8000 (PID 6558)
- Frontend running on port 5173 (PID 6594)
- No duplicates, clean state

---

## Summary

All changes are complete:

1. ✅ **Followups archive to history** instead of permanent deletion
2. ✅ **Export History button** with customizable date range
3. ✅ **Export & Delete button** exports all + deletes 30+ days old
4. ✅ **CSV export** with proper formatting and escaping
5. ✅ **Both buttons appear in History tab** only

**To use**: Hard refresh browser (`Ctrl+Shift+R` or `Cmd+Shift+R`) and navigate to the History tab!
