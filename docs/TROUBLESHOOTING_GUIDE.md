# Troubleshooting Guide - Admin Dashboard Issues

## Issues Addressed

### 1. ✅ Followup Button Not Turning Red / No Badge Count
### 2. ✅ "End Chat" Not Working for Followups
### 3. ✅ Browser Cache Problems

---

## Issue 1: Followup Button Not Showing Red Border/Badge

### Root Cause
**Browser caching old JavaScript** - The browser was serving cached React code that didn't include the new notification badge logic.

### Solution
**Hard refresh the browser** to clear the cache and load the latest JavaScript.

### Steps to Fix:

1. **Restart the servers** (to ensure latest code is loaded):
   ```bash
   /workspace/dev.sh
   ```

2. **Hard refresh your browser**:
   - **Windows/Linux**: Press `Ctrl + Shift + R`
   - **Mac**: Press `Cmd + Shift + R`
   - Or: Clear browser cache completely

3. **Verify the badge appears**:
   - Badge should show number "5" (current unviewed count)
   - Red ring border around Followups tab
   - Text "You have new followups!" below tab name

### How to Verify It's Working:

**Check 1: View source in browser**
- Open DevTools (F12)
- Go to Sources tab
- Find `AdminDashboard.jsx` and check it contains:
  ```javascript
  await fetchWithAuth("/admin/api/followups/unviewed-count");
  ```

**Check 2: Network tab**
- Open DevTools → Network tab
- Reload page
- Look for request to `/admin/api/followups/unviewed-count`
- Should return: `{"count": 5}`

**Check 3: React DevTools**
- Install React DevTools extension
- Find `<AdminDashboard>` component
- Check state: `followupCount: 5`
- Find `<Tabs>` component
- Check props: `followupCount: 5`

### If Badge Still Doesn't Show:

**Option 1: Clear ALL browser data**
```
Settings → Privacy → Clear browsing data
Select: Cached images and files
Time range: All time
```

**Option 2: Try incognito/private window**
- Open new incognito/private window
- Navigate to http://localhost:5173/admin-app/
- Login and check if badge appears

**Option 3: Check console for errors**
- F12 → Console tab
- Look for errors like:
  - "Failed to fetch followup count"
  - CORS errors
  - 401 Unauthorized
- If you see errors, the backend may not be running

**Option 4: Verify backend is responding**
```bash
# Get your auth token from browser localStorage
# Then test the endpoint:
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/admin/api/followups/unviewed-count

# Should return: {"count": 5}
```

---

## Issue 2: "End Chat" Not Working for Followups

### Root Cause
**Followups are NOT conversations** - They're contact form submissions without active chats.

The original "End Chat" button tried to call `/handoff/close`, which only works for active conversation records. Followups don't exist in the `conversations` table, so this endpoint would fail.

### Solution
**Different buttons for different types**:
- **Conversations**: Show "End Chat" button
- **Followups**: Show "Delete Followup" button

### Implementation:

**Detection Logic** (ChatBox.jsx):
```javascript
const isFollowup = conversation.id !== undefined;
```

**Conditional Button**:
```javascript
<button onClick={isFollowup ? handleDeleteFollowup : handleEndChat}>
  {isFollowup ? "Delete Followup" : "End Chat"}
</button>
```

**Delete Followup Function**:
```javascript
const handleDeleteFollowup = async () => {
  await fetchWithAuth(`/admin/api/followups/${conversation.id}`, {
    method: "DELETE"
  });
  alert("Followup deleted");
  window.location.reload();
};
```

**Backend Endpoint** (server.py):
```python
@app.delete("/admin/api/followups/{followup_id}")
def delete_followup(followup_id: int):
    with db() as conn:
        c.execute("DELETE FROM followups WHERE id = ?", (followup_id,))
        conn.commit()
    return {"success": True, "id": followup_id, "deleted": True}
```

### Expected Behavior:

**When viewing a Followup**:
- Header shows: "Followup from [Name]"
- Button shows: "Delete Followup" (red)
- No "Channel" or "Assigned" info displayed
- Contact information shown at bottom
- Clicking "Delete Followup" removes it from database

**When viewing a Conversation**:
- Header shows: "Chat with [user_id]"
- Button shows: "End Chat" (red)
- Shows "Channel" and "Assigned" info
- Clicking "End Chat" moves to history

### Data Model Explanation:

**Conversations Table**:
- Active chats between users and staff
- Fields: user_id, channel, assigned_staff, open, etc.
- Can be "ended" (moved to history)

**Followups Table**:
- Contact form submissions after escalation timeout
- Fields: id, user_id, channel, name, email, phone, message, ts, viewed
- Can only be "deleted" (removed from list)

**Key Difference**:
- Followups have an `id` field
- Conversations don't have an `id` field (they use user_id+channel as composite key)
- This is how we detect which type we're viewing

---

## Issue 3: Browser Cache Issues

### Why This Happens:

**Vite Dev Server** uses Hot Module Replacement (HMR), which normally updates code instantly. However:
- Browser can cache compiled JavaScript bundles
- Service workers can cache old versions
- Hard refreshes don't always clear everything

### Prevention:

**Always hard refresh after code changes**:
```
Windows/Linux: Ctrl + Shift + R
Mac: Cmd + Shift + R
```

**Or disable cache while DevTools open**:
1. Open DevTools (F12)
2. Go to Network tab
3. Check "Disable cache"
4. Keep DevTools open while testing

### When to Clear Cache:

**Clear cache if you see**:
- Old UI after code changes
- Console errors about missing modules
- Outdated text/styles
- Features not working that should work

**How to clear**:
1. Chrome: Settings → Privacy → Clear browsing data → Cached images/files
2. Firefox: Settings → Privacy → Clear Data → Cached Web Content
3. Safari: Develop → Empty Caches
4. Or just use incognito/private window for testing

---

## Current Status

### Servers:
- ✅ Backend running: http://localhost:8000
- ✅ Frontend running: http://localhost:5173/admin-app/

### Database:
- ✅ 5 followups in database (all unviewed)
- ✅ `viewed` column exists and working
- ✅ `followups` table ready for testing

### Code Changes:
- ✅ AdminDashboard fetches unviewed count
- ✅ Tabs shows badge when count > 0
- ✅ ChatBox marks followups as viewed when opened
- ✅ ChatBox shows "Delete Followup" for followups
- ✅ ChatBox shows "End Chat" for conversations
- ✅ Backend has all required endpoints

---

## Testing Checklist

### Test 1: Followup Badge Appears
- [ ] Navigate to http://localhost:5173/admin-app/
- [ ] **Hard refresh** (Ctrl+Shift+R or Cmd+Shift+R)
- [ ] Login to admin dashboard
- [ ] Followups tab should show:
  - [ ] Red ring border
  - [ ] Red badge with number "5"
  - [ ] Text "You have new followups!"

### Test 2: Badge Decrements When Opening Followup
- [ ] Click on Followups tab
- [ ] Click on first followup in left panel
- [ ] Wait 2 seconds
- [ ] Check Followups tab button
- [ ] Badge should now show "4" (decremented from 5)

### Test 3: Delete Followup Works
- [ ] While viewing a followup
- [ ] Header should say "Followup from [Name]"
- [ ] Button should say "Delete Followup" (not "End Chat")
- [ ] Click "Delete Followup"
- [ ] Confirm the dialog
- [ ] Page should reload
- [ ] Followup should be gone from list
- [ ] Badge should decrement

### Test 4: End Chat Works for Conversations
- [ ] Click on "Open" tab
- [ ] Click on an active conversation
- [ ] Header should say "Chat with [user_id]"
- [ ] Button should say "End Chat" (not "Delete Followup")
- [ ] Should see Channel and Assigned info
- [ ] Click "End Chat"
- [ ] Confirm the dialog
- [ ] Chat should move to History tab

---

## Database Queries for Debugging

### Check unviewed count:
```bash
python3 -c "import sqlite3; \
conn = sqlite3.connect('handoff.sqlite'); \
print('Unviewed:', conn.execute('SELECT COUNT(*) FROM followups WHERE viewed = 0').fetchone()[0])"
```

### List all followups:
```bash
python3 -c "import sqlite3; \
conn = sqlite3.connect('handoff.sqlite'); \
[print(f'ID {r[0]}: {r[3]} ({r[4]}) - viewed={r[8]}') \
for r in conn.execute('SELECT * FROM followups').fetchall()]"
```

### Reset all to unviewed:
```bash
python3 -c "import sqlite3; \
conn = sqlite3.connect('handoff.sqlite'); \
conn.execute('UPDATE followups SET viewed = 0'); \
conn.commit(); \
print('✅ All followups reset to unviewed')"
```

---

## Quick Fixes

### Problem: Badge not showing
**Fix**: Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)

### Problem: "End Chat" fails for followup
**Fix**: Servers restarted - should now show "Delete Followup" instead

### Problem: Changes not appearing
**Fix**:
```bash
# 1. Restart servers
/workspace/dev.sh

# 2. Hard refresh browser
Ctrl+Shift+R (or Cmd+Shift+R on Mac)

# 3. Check console for errors
F12 → Console tab
```

### Problem: Backend not responding
**Fix**:
```bash
# Check if backend is running
curl http://localhost:8000/health

# If no response, restart
/workspace/dev.sh

# Check logs
tail -f /tmp/backend.log
```

---

## Summary

All three issues have been fixed:

1. ✅ **Badge not showing** → Browser cache issue → Hard refresh fixes it
2. ✅ **End Chat not working for followups** → Followups now show "Delete Followup" button
3. ✅ **Code changes** → All implemented and servers restarted

**Next Step**: Hard refresh your browser at http://localhost:5173/admin-app/ and all features should work!
