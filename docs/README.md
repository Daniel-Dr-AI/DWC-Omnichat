# Documentation Index

This folder contains all troubleshooting and feature documentation for the DWC Omnichat Admin Dashboard.

## Quick Start

### Check Server Status
```bash
/workspace/server-status.sh
```

### Start/Restart Servers
```bash
/workspace/dev.sh
```

---

## Documentation Files

### Server Management
- **[SERVER_MANAGEMENT.md](SERVER_MANAGEMENT.md)** - Comprehensive guide to managing dev servers, preventing duplicate processes, and using the startup scripts

### Feature Documentation
- **[FOLLOWUP_NOTIFICATION_FEATURE.md](FOLLOWUP_NOTIFICATION_FEATURE.md)** - Complete documentation of the followup notification badge feature, including implementation details and testing

### Troubleshooting
- **[TROUBLESHOOTING_GUIDE.md](TROUBLESHOOTING_GUIDE.md)** - Step-by-step troubleshooting for common issues:
  - Badge not showing (browser cache)
  - End Chat not working for followups
  - Code changes not appearing

### Verification
- **[CHANGES_VERIFIED.md](CHANGES_VERIFIED.md)** - Verification that all recent code changes are present and being served correctly

---

## Root-Level Files

### Scripts (in `/workspace/`)
- **`dev.sh`** - Start/restart both backend and frontend servers cleanly
- **`server-status.sh`** - Check server status and process counts
- **`migrate_followups_viewed.py`** - Database migration to add `viewed` column
- **`test_followup_viewing.py`** - Test followup viewing workflow

### Other Docs (in `/workspace/`)
- **`LOCAL_DEV_GUIDE.md`** - General local development setup
- **`IMPLEMENTATION.md`** - Implementation notes
- **`REFACTORING_PLAN.md`** - Planned refactoring work

---

## Common Tasks

### Check if servers are running
```bash
/workspace/server-status.sh
```

**Expected output:**
```
✅ Backend responding on port 8000
✅ Frontend responding on port 5173
uvicorn processes: 1
vite processes: 1
npm processes: 1
```

### Restart servers
```bash
/workspace/dev.sh
```

### View server logs
```bash
# Backend
tail -f /tmp/backend.log

# Frontend
tail -f /tmp/frontend.log

# Both
tail -f /tmp/backend.log /tmp/frontend.log
```

### Check database
```bash
# Unviewed followups count
python3 -c "import sqlite3; \
conn = sqlite3.connect('handoff.sqlite'); \
print('Unviewed:', conn.execute('SELECT COUNT(*) FROM followups WHERE viewed = 0').fetchone()[0])"

# All followups
python3 -c "import sqlite3; \
conn = sqlite3.connect('handoff.sqlite'); \
[print(f'ID {r[0]}: {r[3]} - viewed={r[8]}') \
for r in conn.execute('SELECT * FROM followups').fetchall()]"
```

---

## Important Notes

### Process Management
- **Always use `/workspace/dev.sh` to start servers** - it prevents duplicate processes
- **Use `/workspace/server-status.sh` to check status** - shows actual port usage and process counts
- **Don't run `npm run dev` or `uvicorn` directly** - use the startup script

### Browser Caching
- **Always hard refresh** after code changes: `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac)
- **Enable "Disable cache" in DevTools** while developing
- **Use incognito mode** for testing if cache issues persist

### Server Issues
The backend uses Python multiprocessing, which can create orphaned worker processes. These show up as:
```
python3 -c from multiprocessing.spawn import spawn_main; spawn_main(...)
```

If you see orphaned processes (PPID = 1), restart servers:
```bash
/workspace/dev.sh
```

---

## File Organization

```
/workspace/
├── docs/                           # Documentation (this folder)
│   ├── README.md                   # This file
│   ├── SERVER_MANAGEMENT.md
│   ├── FOLLOWUP_NOTIFICATION_FEATURE.md
│   ├── TROUBLESHOOTING_GUIDE.md
│   └── CHANGES_VERIFIED.md
│
├── dev.sh                          # Main server startup script
├── server-status.sh                # Server status checker
├── migrate_followups_viewed.py     # Database migration
├── test_followup_viewing.py        # Feature test script
│
├── server.py                       # FastAPI backend
├── handoff.sqlite                  # Database
│
└── admin-frontend/                 # React frontend
    └── src/
        └── components/
            └── admin/
                ├── AdminDashboard.jsx
                ├── Tabs.jsx
                ├── ChatBox.jsx
                └── ConversationList.jsx
```

---

## Getting Help

1. **Check server status**: `/workspace/server-status.sh`
2. **Check logs**: `tail -f /tmp/backend.log /tmp/frontend.log`
3. **Read troubleshooting guide**: `docs/TROUBLESHOOTING_GUIDE.md`
4. **Restart servers**: `/workspace/dev.sh`
5. **Hard refresh browser**: `Ctrl+Shift+R` or `Cmd+Shift+R`
