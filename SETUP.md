# DWC-Omnichat Setup Guide

Quick reference for setting up your development environment.

## 🚀 Automated Setup (Recommended)

After devcontainer rebuild or fresh clone:

```bash
./setup-dev-environment.sh
```

This interactive script installs everything you need!

## 📦 What Gets Installed

### Python Dependencies (from `requirements.txt`)
- FastAPI + Uvicorn (backend framework)
- WebSocket support (websockets, wsproto)
- Twilio SDK (SMS/WhatsApp integration)
- JWT authentication (python-jose, passlib, bcrypt)
- Data validation (pydantic)
- HTTP client (httpx, aiohttp)
- Templates (jinja2)

### Node.js Dependencies

**Root package.json** (Tailwind CSS):
- tailwindcss
- autoprefixer
- postcss

**admin-frontend/package.json** (React admin dashboard):
- react + react-dom
- react-router-dom
- vite (build tool)
- Tailwind CSS v4
- ESLint

**dwc-admin-mobile/** (if exists - React Native mobile app):
- React Native dependencies
- Expo (if used)

### Optional Tools

Prompted during setup:
- **Serena AI** - AI coding assistant with language server
- **SQLite3 CLI** - Database inspection tool

## 🔧 Manual Installation

If you prefer manual control:

```bash
# 1. Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Frontend
npm install                          # Root (Tailwind)
cd admin-frontend && npm install     # Admin dashboard

# 3. Environment
python -c 'import secrets; print(secrets.token_urlsafe(32))'  # Generate JWT_SECRET
# Copy output to .env file as JWT_SECRET=...

# 4. Build frontend (for production)
cd admin-frontend && npm run build
```

## 🐳 Devcontainer Customization

### Adding Tools Permanently

Edit `.devcontainer/Dockerfile`:

```dockerfile
# System packages (apt-get)
RUN apt-get update && apt-get install -y \
  your-package-here \
  && apt-get clean

# Python packages (pip)
RUN pip install package-name

# Global npm packages
RUN npm install -g package-name
```

Then: Rebuild devcontainer (`Ctrl+Shift+P` → "Rebuild Container")

### Current Devcontainer Includes

Base tools already in Dockerfile:
- ✅ Node.js 20
- ✅ Python 3 + pip
- ✅ Git + GitHub CLI (gh)
- ✅ Zsh with Oh My Zsh
- ✅ fzf (fuzzy finder)
- ✅ jq (JSON processor)
- ✅ nano, vim editors
- ✅ iptables, ipset (firewall tools)
- ✅ git-delta (better git diffs)

## 📁 What Persists vs What Resets

### ✅ Persists Across Rebuilds
- Your code files
- Git history
- Database (handoff.sqlite)
- Configuration files (.env, .context7, .serena/)
- node_modules and .venv (if using bind mounts)

### ❌ Resets on Rebuild
- System packages (apt-get)
- Python packages (pip) - unless in requirements.txt
- Global npm packages - unless in package.json
- Shell customizations - unless in Dockerfile

**Solution**: Use `setup-dev-environment.sh` after each rebuild!

## 🔐 Environment Variables

Required in `.env`:

```bash
# REQUIRED
JWT_SECRET=your-secret-key-here

# OPTIONAL (for integrations)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_NUMBER=

FB_PAGE_ACCESS_TOKEN=
FB_VERIFY_TOKEN=

# CONFIGURATION (with defaults)
FRONTEND_ORIGIN=http://localhost:5173
PUBLIC_BASE_URL=http://localhost:8000
AUTO_CLOSE_MINUTES=30
ESCALATE_AFTER_SECONDS=300
```

Generate secure JWT_SECRET:
```bash
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

## 🚦 Verify Setup

```bash
# Check Python environment
source .venv/bin/activate
python --version
pip list | grep fastapi

# Check frontend dependencies
cd admin-frontend
npm list react

# Check database (created on first server start)
ls -la handoff.sqlite

# Check environment variables
cat .env | grep JWT_SECRET
```

## 🏃 Running the Application

After setup:

```bash
# Terminal 1: Backend
source .venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd admin-frontend
npm run dev

# Access:
# - API Docs: http://localhost:8000/docs
# - Admin Dashboard: http://localhost:5173/admin-app/
# - Test Widget: Open test-chat-widget.html in browser
```

## 📚 More Information

- **CLAUDE.md** - Complete project reference for AI assistants
- **LOCAL_DEV_GUIDE.md** - Detailed development workflow
- **IMPLEMENTATION.md** - Feature roadmap and architecture
- **REFACTORING_PLAN.md** - Future improvements plan

## ❓ Troubleshooting

### "ModuleNotFoundError" when running server
```bash
# Activate virtual environment first!
source .venv/bin/activate
```

### Frontend build errors
```bash
cd admin-frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Database "table doesn't exist" errors
```bash
# Database auto-creates on first run
# If issues persist, delete and restart:
rm handoff.sqlite
uvicorn server:app --reload  # Will recreate DB
```

### Port already in use
```bash
# Find process using port 8000
lsof -ti:8000

# Kill it
kill -9 $(lsof -ti:8000)
```

## 🎯 Quick Commands Reference

```bash
# Setup (after rebuild)
./setup-dev-environment.sh

# Start development
source .venv/bin/activate && uvicorn server:app --reload     # Backend
cd admin-frontend && npm run dev                              # Frontend

# Build for production
cd admin-frontend && npm run build

# Database migrations (manual)
python migrate_schema.py

# Run tests (when implemented)
pytest

# Code formatting (if tools installed)
black server.py auth.py
ruff check .
```
