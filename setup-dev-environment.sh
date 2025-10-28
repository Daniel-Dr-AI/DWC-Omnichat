#!/bin/bash
# DWC-Omnichat Development Environment Setup
# This script installs all necessary tools and dependencies for the project
# Run this after devcontainer rebuild or on fresh environment

set -e  # Exit on error

echo "🚀 Setting up DWC-Omnichat development environment..."
echo ""

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================
# 1. Python Virtual Environment & Dependencies
# ============================================
echo -e "${BLUE}📦 Step 1: Python environment${NC}"

if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${YELLOW}⚠️  Virtual environment already exists, skipping...${NC}"
fi

echo "Installing Python dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✅ Python dependencies installed${NC}"
echo ""

# ============================================
# 2. Node.js Dependencies (Frontend)
# ============================================
echo -e "${BLUE}📦 Step 2: Frontend dependencies${NC}"

# Root package.json (if exists - for Tailwind)
if [ -f "package.json" ]; then
    echo "Installing root npm packages..."
    npm install
    echo -e "${GREEN}✅ Root npm packages installed${NC}"
fi

# Admin frontend
if [ -d "admin-frontend" ]; then
    echo "Installing admin-frontend dependencies..."
    cd admin-frontend
    npm install
    cd ..
    echo -e "${GREEN}✅ Admin frontend dependencies installed${NC}"
fi

# Mobile app (if exists)
if [ -d "dwc-admin-mobile" ]; then
    echo "Installing mobile app dependencies..."
    cd dwc-admin-mobile
    npm install
    cd ..
    echo -e "${GREEN}✅ Mobile app dependencies installed${NC}"
fi
echo ""

# ============================================
# 3. Optional Tools & Extensions
# ============================================
echo -e "${BLUE}🔧 Step 3: Optional development tools${NC}"

# Serena AI assistant
read -p "Install Serena AI assistant? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing Serena..."
    pip install serena-ai || echo -e "${YELLOW}⚠️  Serena installation failed - may need manual setup${NC}"
    echo -e "${GREEN}✅ Serena installation attempted${NC}"
fi

# Database browser (optional)
read -p "Install sqlite3 CLI tools? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing sqlite3..."
    sudo apt-get update && sudo apt-get install -y sqlite3
    echo -e "${GREEN}✅ SQLite3 installed${NC}"
fi
echo ""

# ============================================
# 4. Initialize Database
# ============================================
echo -e "${BLUE}🗄️  Step 4: Database initialization${NC}"

if [ ! -f "handoff.sqlite" ]; then
    echo "Database will be created on first server start..."
    echo -e "${YELLOW}ℹ️  Run 'uvicorn server:app --reload' to initialize${NC}"
else
    echo -e "${GREEN}✅ Database already exists${NC}"
fi
echo ""

# ============================================
# 5. Build Frontend
# ============================================
echo -e "${BLUE}🏗️  Step 5: Build frontend${NC}"

read -p "Build admin frontend now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd admin-frontend
    npm run build
    cd ..
    echo -e "${GREEN}✅ Frontend built${NC}"
else
    echo -e "${YELLOW}ℹ️  Skipping frontend build (you can run 'npm run build' later)${NC}"
fi
echo ""

# ============================================
# 6. Environment Variables
# ============================================
echo -e "${BLUE}⚙️  Step 6: Environment variables${NC}"

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  No .env file found!${NC}"
    read -p "Create .env from template? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cat > .env << 'EOF'
# DWC-Omnichat Environment Variables
# Copy this file to .env and fill in your values

# Security (REQUIRED)
JWT_SECRET=your-secret-key-here-replace-me

# Twilio (Optional - for SMS/WhatsApp)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_NUMBER=

# Facebook Messenger (Optional)
FB_PAGE_ACCESS_TOKEN=
FB_VERIFY_TOKEN=

# Configuration
FRONTEND_ORIGIN=http://localhost:5173
PUBLIC_BASE_URL=http://localhost:8000
AUTO_CLOSE_MINUTES=30
ESCALATE_AFTER_SECONDS=300
EOF
        echo -e "${GREEN}✅ .env template created - EDIT THIS FILE BEFORE RUNNING!${NC}"
        echo -e "${YELLOW}⚠️  Generate a secure JWT_SECRET with: python -c 'import secrets; print(secrets.token_urlsafe(32))'${NC}"
    fi
else
    echo -e "${GREEN}✅ .env file exists${NC}"
fi
echo ""

# ============================================
# 7. Git Configuration (if needed)
# ============================================
echo -e "${BLUE}🔧 Step 7: Git configuration${NC}"

if ! git config user.name > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Git user not configured${NC}"
    read -p "Configure git user? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your name: " git_name
        read -p "Enter your email: " git_email
        git config --global user.name "$git_name"
        git config --global user.email "$git_email"
        echo -e "${GREEN}✅ Git configured${NC}"
    fi
else
    echo -e "${GREEN}✅ Git already configured${NC}"
fi
echo ""

# ============================================
# Summary
# ============================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Setup complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Edit .env file (especially JWT_SECRET)"
echo "   Generate secure key: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
echo ""
echo "2. Start backend server:"
echo "   source .venv/bin/activate"
echo "   uvicorn server:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "3. Start frontend dev server (in separate terminal):"
echo "   cd admin-frontend && npm run dev"
echo ""
echo "4. Access application:"
echo "   - Backend API: http://localhost:8000/docs"
echo "   - Admin Dashboard: http://localhost:5173/admin-app/"
echo "   - Test Widget: Open test-chat-widget.html in browser"
echo ""
echo "📚 Documentation:"
echo "   - LOCAL_DEV_GUIDE.md - Complete development guide"
echo "   - CLAUDE.md - AI assistant reference"
echo "   - IMPLEMENTATION.md - Feature roadmap"
echo ""
