# Server Management Guide

## Problem: Multiple Vite Instances & Hot Reload Issues

### Root Cause
The issue of 10+ Vite processes running simultaneously was caused by:

1. **Background Bash processes**: Using `Bash` tool with `run_in_background: true` repeatedly without cleanup
2. **No process management**: Each new `npm run dev` command started a new Vite instance without killing old ones
3. **Shell snapshot accumulation**: Background shells remained active even after losing connection to them

### Why This Breaks Hot Reload
- Browser connects to the **first** Vite dev server instance
- Code changes are picked up by the **latest** Vite instance
- HMR (Hot Module Replacement) messages sent to wrong WebSocket connection
- Result: Changes don't appear even with hard refresh

---

## Solution: Centralized Server Management

### New Startup Script: `start-dev.sh`

A comprehensive bash script that:
- ✅ Kills ALL existing processes before starting new ones
- ✅ Prevents duplicate Vite/uvicorn instances
- ✅ Provides status checking and logging
- ✅ Supports selective startup (backend only, frontend only, or both)

### Usage

#### Start Both Servers
```bash
./start-dev.sh
# or
./start-dev.sh both
```

#### Start Individual Servers
```bash
# Backend only
./start-dev.sh backend

# Frontend only
./start-dev.sh frontend
```

#### Check Server Status
```bash
./start-dev.sh status
```

#### Stop All Servers
```bash
./start-dev.sh stop
```

#### View Logs
```bash
# Backend logs
tail -f /tmp/backend.log

# Frontend logs
tail -f /tmp/frontend.log

# Follow both in real-time
tail -f /tmp/backend.log /tmp/frontend.log
```

---

## Hot Reload Verification

### How to Verify HMR is Working

1. **Start the frontend server**:
   ```bash
   ./start-dev.sh frontend
   ```

2. **Open browser to**: http://localhost:5173/admin-app/

3. **Make a visible change** to any React component:
   ```jsx
   // Example: Add a test message to Tabs.jsx
   <div className="flex gap-4">
     <p>TEST: Hot reload working!</p>  {/* Add this line */}
     {tabs.map((tab) => { /* ... */ })}
   </div>
   ```

4. **Expected behavior**:
   - Change appears in browser **immediately** (< 1 second)
   - No full page reload
   - Browser console shows: `[vite] hot updated: /src/components/admin/Tabs.jsx`

5. **If it doesn't work**:
   ```bash
   # Stop all servers
   ./start-dev.sh stop

   # Start fresh
   ./start-dev.sh frontend

   # Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)
   ```

### What HMR Should Show

When you save a file, the frontend log should show:
```
[timestamp] hmr update /src/components/admin/Tabs.jsx
```

Browser console should show:
```
[vite] hot updated: /src/components/admin/Tabs.jsx
```

---

## Troubleshooting

### Issue: Changes Don't Appear After Save

**Check 1: Verify only ONE Vite process is running**
```bash
ps aux | grep vite | grep -v grep
```

Expected output: **Exactly 3 lines** (npm, sh, node)
```
node     89383  npm run dev
node     89395  sh -c vite
node     89397  node .../node_modules/.bin/vite
```

If you see more than 3 lines, you have duplicate processes.

**Solution**:
```bash
./start-dev.sh stop
./start-dev.sh frontend
```

---

### Issue: "Cannot connect to WebSocket"

**Symptoms**:
- Browser console shows WebSocket connection errors
- HMR not updating

**Solution**:
```bash
# 1. Stop all servers
./start-dev.sh stop

# 2. Clear Vite cache
rm -rf /workspace/admin-frontend/node_modules/.vite

# 3. Restart
./start-dev.sh frontend

# 4. Hard refresh browser
```

---

### Issue: Port Already in Use

**Error**: `Port 5173 is already in use`

**Solution**:
```bash
# Find and kill process on port 5173
lsof -ti:5173 | xargs kill -9

# Or use the script
./start-dev.sh stop
./start-dev.sh frontend
```

---

## Best Practices

### DO ✅
- Always use `./start-dev.sh` to start servers
- Check status with `./start-dev.sh status` before starting
- Use `./start-dev.sh stop` before restarting
- Monitor logs with `tail -f /tmp/frontend.log` when debugging

### DON'T ❌
- Don't run `npm run dev` directly in multiple terminals
- Don't use `nohup npm run dev &` manually
- Don't leave background processes running indefinitely
- Don't ignore "port already in use" errors

---

## Technical Details

### Process Cleanup Strategy

The script uses a two-phase kill approach:

1. **Graceful shutdown** (`SIGTERM`):
   ```bash
   kill -TERM <pid>
   sleep 2
   ```

2. **Force kill if needed** (`SIGKILL`):
   ```bash
   kill -9 <pid>
   ```

### Process Detection

The script finds processes by pattern matching:
- Backend: `uvicorn server:app`
- Frontend: `vite.*admin-frontend` or `npm run dev.*admin-frontend`

This prevents accidentally killing unrelated processes.

### Log Management

- Backend logs: `/tmp/backend.log`
- Frontend logs: `/tmp/frontend.log`
- Logs persist across restarts for debugging
- Use `> /dev/null` in script to keep logs clean

---

## Quick Reference

| Task | Command |
|------|---------|
| Start everything | `./start-dev.sh` |
| Start backend only | `./start-dev.sh backend` |
| Start frontend only | `./start-dev.sh frontend` |
| Check status | `./start-dev.sh status` |
| Stop all servers | `./start-dev.sh stop` |
| View backend logs | `tail -f /tmp/backend.log` |
| View frontend logs | `tail -f /tmp/frontend.log` |
| Check Vite processes | `ps aux \| grep vite` |
| Kill port 5173 | `lsof -ti:5173 \| xargs kill -9` |
| Kill port 8000 | `lsof -ti:8000 \| xargs kill -9` |

---

## Summary

The issue of 10+ duplicate Vite instances was caused by repeatedly starting background processes without cleanup. The solution is a centralized management script (`start-dev.sh`) that:

1. **Always cleans up** old processes before starting new ones
2. **Provides visibility** into what's running via status command
3. **Centralizes logging** to `/tmp/` for easy debugging
4. **Prevents conflicts** by ensuring only one instance per service

**Hot reload should now work perfectly** - changes will appear in the browser within 1 second of saving a file.
