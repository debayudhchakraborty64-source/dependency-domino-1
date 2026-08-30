@echo off
echo ═══════════════════════════════════════════
echo   DEPENDENCY DOMINO — Quick Start (Windows)
echo ═══════════════════════════════════════════
echo.

cd backend

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate

echo Installing backend dependencies...
pip install -r requirements.txt -q

if not exist .env (
    copy .env.example .env
    echo Created backend\.env from .env.example
)

echo.
echo Backend ready.
echo.
echo To start:
echo   Terminal 1: cd backend ^& .venv\Scripts\activate ^& uvicorn main:app --reload
echo   Terminal 2: cd frontend ^& npm install ^& npm start
echo.
echo Then open: http://localhost:3000
