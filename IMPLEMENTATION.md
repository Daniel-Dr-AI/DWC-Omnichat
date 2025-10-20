# DWC Omnichat — Implementation & SaaS Roadmap (2025)

> Single source of truth for setup, development flow, and future-proof upgrades.  
> Optimized for local dev + Render deploy, React admin, multi-user auth, analytics, mobile app with push, automation, and AI insights.

---

## 0) Current status (you are here)

- **Backend:** FastAPI running locally. DB path logic fixed (local file vs Render `/data`).  
- **Frontend:** React + Vite + Tailwind v4 working. Dev proxy to FastAPI confirmed.  
- **Goal shift:** Twilio/SMS not required for notifications. Use admin dashboard + future mobile app with push.  
- **Next steps:** Add multi-user auth, analytics logging, and continue React admin pages.

---

## 1) Prerequisites

- **Windows 10/11** with **PowerShell**
- **Python 3.11+**
- **Node.js 22+** + npm
- (Optional) **Render.com** account for deploy
- (Later) **Apple Developer** account for push notifications to iOS (not required for local dev)

Verify:
```powershell
python --version
node -v
npm -v
```

---

## 2) Repo layout

```
Omnichat/
├─ server.py
├─ requirements.txt
├─ admin-frontend/
│  ├─ index.html
│  ├─ vite.config.js
│  ├─ postcss.config.js
│  ├─ tailwind.config.js
│  └─ src/
│     ├─ main.jsx
│     ├─ App.jsx
│     └─ index.css
├─ .env
└─ handoff.sqlite
```

---

## 3) Running locally

### 3.1 Backend (FastAPI)

```powershell
cd C:\Users\YOURUSER\Desktop\DWC-Omnichat
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
python server.py
```

Open: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 3.2 Frontend (React + Vite + Tailwind v4)

```powershell
cd admin-frontend
npm install
npm run dev
```

Open: [http://localhost:5173](http://localhost:5173)

---

## 4) Phases overview (SaaS roadmap — SMB & Mid-Market)

| Phase | Objective | Core deliverables |
|-------|------------|------------------|
| 1 | **Admin Dashboard (UI foundation)** | Chat list + chat window + WebSocket integration |
| 2 | **Auth & Staff Identity** | Multi-user JWT login, tenants, RBAC |
| 3 | **Analytics & Metrics** | KPI endpoints, chart dashboard |
| 4 | **File Uploads & Media Sharing** | Drag-and-drop to FastAPI UploadFile |
| 5 | **Automation & Rules Engine** | Event-based triggers, smart routing |
| 6 | **Billing & SaaS Readiness** | Stripe integration, metered usage |
| 7 | **AI Summaries & Insights** | Auto-summary, sentiment, intent tagging |
| 8 | **Integrations (CRM / Webhooks)** | Slack, HubSpot, Zapier, API webhooks |
| 9 | **White-Label & Custom Branding** | Tenant logos, color themes, domains |
| 10 | **Mobile App + Push Notifications** | React Native + FCM/APNs device registration |
| 11 | **Analytics v2 + AI Query Interface** | Natural-language analytics over chat data |

---

## 5) Database schema upgrades (apply now)

> Use SQLite locally (same SQL works in Postgres later).

```sql
CREATE TABLE IF NOT EXISTS tenants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL,
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'staff',
  created_at TEXT NOT NULL,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

ALTER TABLE conversations ADD COLUMN tenant_id INTEGER;
ALTER TABLE conversations ADD COLUMN assigned_staff_id INTEGER;
ALTER TABLE messages ADD COLUMN tenant_id INTEGER;
ALTER TABLE messages ADD COLUMN staff_id INTEGER;

ALTER TABLE conversations ADD COLUMN created_at TEXT;
ALTER TABLE conversations ADD COLUMN first_user_message_at TEXT;
ALTER TABLE conversations ADD COLUMN first_staff_reply_at TEXT;
ALTER TABLE conversations ADD COLUMN closed_at TEXT;

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
  updated_at TEXT NOT NULL,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER,
  conversation_id INTEGER,
  user_id INTEGER,
  type TEXT NOT NULL,
  payload TEXT,
  ts TEXT NOT NULL
);
```

---

### 🔍 Extended Schema for Quality & Performance Monitoring

To support conversation quality tracking, agent performance analytics, and AI auditability, append the following tables and fields:

```sql
CREATE TABLE IF NOT EXISTS conversation_feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL,
  rating INTEGER CHECK(rating BETWEEN 1 AND 5),
  comment TEXT,
  ts TEXT NOT NULL,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

ALTER TABLE conversation_metrics ADD COLUMN quality_score INTEGER;
ALTER TABLE conversation_metrics ADD COLUMN rating_comment TEXT;

CREATE TABLE IF NOT EXISTS agent_metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  staff_id INTEGER NOT NULL,
  date TEXT NOT NULL,
  total_chats INTEGER DEFAULT 0,
  avg_response_seconds INTEGER,
  avg_duration_seconds INTEGER,
  avg_quality_score INTEGER,
  FOREIGN KEY (staff_id) REFERENCES users(id)
);

ALTER TABLE conversations ADD COLUMN resolved INTEGER DEFAULT 0;
ALTER TABLE conversations ADD COLUMN last_staff_activity_at TEXT;

CREATE TABLE IF NOT EXISTS ai_actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER,
  model TEXT,
  action_type TEXT,
  input_ref TEXT,
  output_ref TEXT,
  ts TEXT NOT NULL,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

---

### 🧠 Feedback & QA Features

| Feature | Description | Example endpoint |
|----------|--------------|------------------|
| Conversation feedback | Collect post-chat rating (1–5) + comment | `POST /api/v1/feedback` |
| Agent metrics rollup | Nightly batch aggregates daily agent stats | `/api/v1/analytics/agents/daily` |
| Resolution tracking | Agents mark chats resolved | `PATCH /api/v1/conversations/{id}/resolve` |
| Staff activity tracking | Update on every staff message | handled in `add_message()` |
| AI audit trail | Log summarization or auto-actions | `INSERT INTO ai_actions` after model call |

---

✅ This extended schema ensures measurable **CSAT**, **FCR**, daily **agent performance insights**, and transparent **AI audit trails** for scalable SMB analytics.

---

## 6) Backend: analytics and automation hooks

Hook into existing message functions:
- Set timestamps on first user/staff messages.
- Increment counters in `conversation_metrics`.
- Insert `events` rows for message, assign, upload, close.

Example (SQLite-compatible):
```sql
UPDATE conversation_metrics
SET total_messages = total_messages + 1,
    user_messages  = user_messages + CASE WHEN :sender='user' THEN 1 ELSE 0 END,
    staff_messages = staff_messages + CASE WHEN :sender='staff' THEN 1 ELSE 0 END,
    updated_at = :now
WHERE conversation_id = :convo_id;
```

---
