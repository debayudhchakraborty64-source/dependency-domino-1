#!/bin/bash
# Dependency Domino — Quick Start Script

echo "═══════════════════════════════════════════"
echo "  DEPENDENCY DOMINO — Quick Start"
echo "═══════════════════════════════════════════"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required. Install from https://python.org"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 18+ is required. Install from https://nodejs.org"
    exit 1
fi

echo "✓ Python: $(python3 --version)"
echo "✓ Node.js: $(node --version)"
echo ""

# Backend setup
echo "--- Setting up backend ---"
cd backend

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null

echo "Installing backend dependencies..."
pip install -r requirements.txt -q

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ Created backend/.env from .env.example"
    echo "  ⚠ Configure WATSONX_API_KEY and WATSONX_PROJECT_ID for AI features (optional)"
fi

echo ""
echo "--- Setting up frontend ---"
cd ../frontend
npm install --silent

echo ""
echo "═══════════════════════════════════════════"
echo "  Ready! Start the application:"
echo ""
echo "  Terminal 1 (Backend):"
echo "    cd dependency-domino/backend"
echo "    source .venv/bin/activate"
echo "    uvicorn main:app --reload --port 8000"
echo ""
echo "  Terminal 2 (Frontend):"
echo "    cd dependency-domino/frontend"
echo "    npm start"
echo ""
echo "  Then open: http://localhost:3000"
echo "  API docs:  http://localhost:8000/api/docs"
echo "═══════════════════════════════════════════"
