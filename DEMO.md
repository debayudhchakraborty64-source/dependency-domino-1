# Dependency Domino — Demo Guide

## Pre-Demo Checklist

1. Backend running: `cd backend && uvicorn main:app --reload`
2. Frontend running: `cd frontend && npm start`
3. Browser open at http://localhost:3000
4. (Optional) watsonx.ai configured in `backend/.env`

---

## 3-Minute Demo Flow

### Step 1 — Open Application (20 seconds)

- Application loads to Overview page
- Show: "Know the blast radius before you touch the code."
- Point to sidebar navigation
- Point to backend status (bottom left): "Backend connected"
- If watsonx.ai configured: "watsonx.ai active"

### Step 2 — Open Demo Repository (15 seconds)

- Click **"Open Demo Repository"**
- Redirects to Dependency Map
- Show the "Developer Portal" pre-loaded demo repository

**Speaking point:** "This is a real-world monorepo structure with authentication, dashboard, profile, API layer, database, and test suite — 42 files and 65+ dependency relationships."

### Step 3 — Show Repository Statistics (15 seconds)

- Navigate to Overview
- Show: files count, language distribution, risk overview
- Point to Risk Overview cards (Critical/High/Medium/Low)

### Step 4 — Open Dependency Map (20 seconds)

- Click "Dependency Map" in sidebar
- The interactive graph loads — nodes connected by dependency edges
- Zoom in/out using scroll wheel
- Pan by dragging
- Point to node colors: blue=file, green=test, purple=service, orange=API

### Step 5 — Select a Central Component (10 seconds)

- Click on the **authService.js** node (or search for it)
- The node highlights; dimmer nodes show unrelated files
- Impact panel slides in on the right

**Speaking point:** "authService handles authentication for the entire application. Let's see what happens if we change it."

### Step 6 — Analyze Change Impact (DOMINO EFFECT) (30 seconds)

- Click the **"⚡ Analyze Change Impact"** button
- Watch the domino animation sequence:
  1. authService node activates (white glow)
  2. Direct dependencies activate (orange glow)
  3. Indirect dependencies activate (yellow)
  4. Related tests activate (green)
  5. Score animates in: 72/100 HIGH IMPACT

**Speaking point:** "ONE change — authService — cascades like dominoes. 5 components depend on it. 12 are in the blast radius. The score is 72/100 — HIGH."

### Step 7 — Show Impact Panel (20 seconds)

- Point to right panel:
  - Impact score: 72/100
  - HIGH IMPACT badge
  - DIRECT DEPS: 3
  - INDIRECT DEPS: 8  
  - AFFECTED: 12
  - TESTS: 3
- Show "WHY?" explanation
- Show RISK FACTORS list

### Step 8 — Explain Impact with AI (30 seconds)

- Click **"🧠 Explain Impact"**
- Panel switches to Explain tab
- If watsonx.ai configured: shows AI explanation with "IBM watsonx.ai" badge
- If not configured: shows rule-based analysis with "Not configured" notice
- Read: Summary, Why It Matters, Potential Impact, Recommended Actions

**Speaking point:** "IBM watsonx.ai receives structured context — not the whole repo — and explains the risk in plain language."

### Step 9 — Generate Test Plan (20 seconds)

- Click **"🧪 Test Plan"**
- Shows existing tests: auth.test.js, login.test.jsx
- Shows recommended tests: run full auth regression suite
- Shows coverage gaps

**Speaking point:** "The system identifies which tests exist and which are missing — labeled clearly as recommendations."

### Step 10 — Simulate Change (20 seconds)

- Click **"🎯 Simulate Change"** or navigate to Simulate tab
- Type: "Change authentication token validation logic"
- Click "Simulate Change"
- Shows: affected components, consequence summary, recommended tests

**Speaking point:** "Before writing a single line of code, the developer knows exactly what to test and who to notify."

### Step 11 — Risk Center (15 seconds)

- Navigate to Risk Center
- Show: 2 critical, 8 high, 12 medium components
- Show ranked table
- "Every component gets a deterministic, explainable risk score."

### Step 12 — Export Report (10 seconds)

- Navigate to Reports
- Click "Generate Report"
- Click "⬇ Download"
- "One-click impact report for code review, PR descriptions, or team communication."

---

## Key Talking Points

| Feature | Talking Point |
|---|---|
| Domino animation | "Visual metaphor for cascade risk — one file, blast radius of 12" |
| Deterministic scoring | "Not AI magic — an explainable formula with documented signals" |
| AI fallback | "Works without watsonx.ai; rule-based analysis is always available" |
| Security | "No code is executed — pure static analysis. ZIP traversal blocked." |
| Demo mode | "Full working demo without any database setup or credentials" |

---

## If Things Go Wrong

| Issue | Recovery |
|---|---|
| Backend offline | `cd backend && uvicorn main:app --reload` |
| No repo loaded | Click "Open Demo Repository" on Overview page |
| Empty graph | Click "Fit View" button in toolbar |
| AI explanation slow | "AI is processing — rule-based result shown as fallback" |
| Tests fail | Refresh page — demo data re-loads on startup |
