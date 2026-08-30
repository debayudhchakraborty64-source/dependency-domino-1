# Dependency Domino

> **"Know the blast radius before you touch the code."**

Dependency Domino is a **pre-change impact intelligence tool** for software developers. It analyzes repository dependency graphs and predicts what could break when you modify a file — before you commit.

## The Problem

Developers frequently modify one component without knowing which other components, functions, tests, APIs, or workflows depend on it. This causes:

- Unexpected regressions
- Missed test coverage
- Hard-to-debug integration failures
- Costly production incidents

## The Solution

Dependency Domino answers: **"If I change this code, what else could be affected?"**

Using static analysis, graph theory, and IBM watsonx.ai, it visualizes the "domino effect" of a change, calculates an explainable impact score, and recommends exactly which tests to run.

---

## Architecture

```
React Frontend (port 3000)
       │
       │ REST API (axios)
       ▼
FastAPI Backend (port 8000)
       │
       ├── Repository Analyzer    (static code parser)
       │
       ├── Dependency Graph Engine (NetworkX + import resolution)
       │
       ├── Impact Analysis Engine  (deterministic scoring formula)
       │
       ├── Risk Scoring Engine     (6-signal model)
       │
       ├── Test Analysis Engine    (name-proximity + edge matching)
       │
       └── IBM watsonx.ai Service  (structured AI explanation)
                │
                ▼
        AI Explanation / Test Plans / Change Simulation
```

### Directory Structure

```
dependency-domino/
├── backend/
│   ├── main.py                   # FastAPI application, all endpoints
│   ├── config.py                 # Settings from environment variables
│   ├── models.py                 # Pydantic data models
│   ├── store.py                  # In-memory data store
│   ├── requirements.txt
│   ├── .env.example
│   ├── analysis/
│   │   ├── repository_analyzer.py   # ZIP extraction, static file parsing
│   │   ├── graph_engine.py          # NetworkX dependency graph builder
│   │   └── impact_engine.py         # Deterministic impact scoring
│   ├── ai/
│   │   └── watsonx_service.py       # IBM watsonx.ai integration + fallback
│   ├── demo/
│   │   └── demo_data.py             # "Developer Portal" demo repository
│   └── tests/
│       └── test_backend.py          # Backend test suite
│
└── frontend/
    ├── public/index.html
    ├── package.json
    ├── src/
    │   ├── App.js                   # Root app + routing
    │   ├── index.js
    │   ├── styles/globals.css       # Design system variables + utilities
    │   ├── store/useStore.js        # Zustand global state
    │   ├── services/apiService.js   # All backend API calls
    │   ├── components/
    │   │   ├── layout/              # Sidebar, Header
    │   │   ├── ui/                  # CommandPalette, NotificationStack
    │   │   ├── repository/          # UploadModal
    │   │   └── impact/              # ImpactPanel (main interaction)
    │   ├── pages/
    │   │   ├── OverviewPage.jsx
    │   │   ├── RepositoryPage.jsx
    │   │   ├── DependencyMapPage.jsx  ← HERO FEATURE
    │   │   ├── ImpactPage.jsx
    │   │   ├── RiskCenterPage.jsx
    │   │   ├── TestImpactPage.jsx
    │   │   ├── ReportsPage.jsx
    │   │   └── SettingsPage.jsx
    │   └── tests/
    │       └── App.test.js
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router 6, ReactFlow, Zustand, Axios |
| Backend | Python 3.10+, FastAPI, Pydantic v2, NetworkX |
| AI | IBM watsonx.ai (granite-13b-instruct-v2) |
| Graph | NetworkX (backend), ReactFlow (frontend) |
| Testing | pytest (backend), @testing-library/react (frontend) |
| Fonts | Inter, JetBrains Mono |

---

## Installation

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm or yarn

### Backend Setup

```bash
cd dependency-domino/backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your watsonx.ai credentials (optional)

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd dependency-domino/frontend

# Install dependencies
npm install

# Start development server
npm start
```

Open http://localhost:3000

---

## Environment Variables

Create `backend/.env` from `backend/.env.example`:

```env
# IBM watsonx.ai (optional — app works without these)
WATSONX_API_KEY=your_api_key_here
WATSONX_PROJECT_ID=your_project_id_here
WATSONX_URL=https://us-south.ml.cloud.ibm.com

# Application
APP_ENV=development
MAX_UPLOAD_SIZE_MB=50
UPLOAD_DIR=./uploads
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

> **Security**: API keys are never exposed to the frontend. All AI calls are made server-side.

---

## API Documentation

FastAPI provides interactive API docs at:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/repositories/upload` | Upload and analyze ZIP repository |
| GET | `/api/repositories/{id}` | Get repository info |
| GET | `/api/repositories/{id}/graph` | Get dependency graph |
| GET | `/api/repositories/{id}/components` | List components (filterable) |
| GET | `/api/repositories/{id}/risks` | Get risk assessment |
| POST | `/api/components/{id}/impact` | Calculate impact score |
| POST | `/api/components/{id}/explain` | Get AI explanation |
| POST | `/api/components/{id}/test-plan` | Generate test plan |
| POST | `/api/components/{id}/simulate` | Simulate a change |
| GET | `/api/search?q=…` | Global search |
| POST | `/api/reports` | Generate impact report |

---

## Demo Mode

The demo repository ("Developer Portal") is pre-loaded on startup. It requires no external credentials.

To use the demo:

1. Open http://localhost:3000
2. Click **"Open Demo Repository"** on the Overview page
3. The demo repository is automatically analyzed and ready

The demo includes:
- React frontend with authentication, dashboard, user profile
- Python FastAPI backend with auth service, user service, dashboard service
- Database layer
- Frontend and backend test suites
- Realistic dependency relationships (65+ edges)

---

## watsonx.ai Setup

1. Create an [IBM Cloud account](https://cloud.ibm.com)
2. Create a Watson Studio project
3. Get your API key from IBM Cloud IAM
4. Set in `backend/.env`:
   ```
   WATSONX_API_KEY=your_key
   WATSONX_PROJECT_ID=your_project_id
   WATSONX_URL=https://us-south.ml.cloud.ibm.com
   ```

If watsonx.ai is not configured, the application falls back to deterministic rule-based analysis and displays:
> "IBM watsonx.ai is not configured. Rule-based analysis is active."

---

## Testing

### Backend Tests

```bash
cd dependency-domino/backend
pip install pytest pytest-asyncio httpx
pytest tests/test_backend.py -v
```

### Frontend Tests

```bash
cd dependency-domino/frontend
npm test
# or
npm run test:ci
```

---

## Impact Scoring Formula

The impact score is **deterministic and explainable** — not a random number.

```
Impact Score (0–100) = sum of 6 signals:

Signal 1: Dependent count         → max 30 pts
  (normalized: dependents / total non-test components × 200, capped at 30)

Signal 2: Direct dependency count → max 15 pts
  (normalized: direct_deps / total × 150, capped at 15)

Signal 3: Indirect dependency count → max 15 pts
  (normalized: indirect_deps / total × 100, capped at 15)

Signal 4: Betweenness centrality  → max 20 pts
  (NetworkX betweenness_centrality × 200, capped at 20)

Signal 5: Test coverage inverse   → max 10 pts
  (0 = good coverage, 10 = no coverage)

Signal 6: Service/API/entry-point → max 10 pts
  (service type: +5, index/entry: +5)
```

Risk levels:
- CRITICAL: ≥ 75
- HIGH:     ≥ 50
- MEDIUM:   ≥ 25
- LOW:      < 25

---

## Security Notes

- ZIP extraction prevents path traversal attacks (blocks `../` paths)
- No uploaded code is ever executed — analysis is static only
- File size limits enforced (500 KB per file, 50 MB total ZIP)
- Ignored directories: `node_modules`, `.git`, `dist`, `build`, `__pycache__`, `.venv`, etc.
- No frontend secrets — API keys are backend-only environment variables
- CORS configured to allow only specified origins
- Input validation via Pydantic models
- No SQL injection risk (in-memory store; future: parameterized queries)

---

## Known Limitations

1. **Dependency resolution is path-based**: Import `'react'` or `'fastapi'` (third-party) are not resolved to repo files — this is by design and labeled as `confidence: 0.4 / POSSIBLE`

2. **No semantic analysis**: The engine uses regex-based import parsing. Dynamically constructed imports (e.g., `require(variable)`) cannot be detected

3. **In-memory store**: Data does not persist across server restarts. A production version would use SQLite or PostgreSQL

4. **Large repositories**: Repositories > 2,000 files are truncated. Very large codebases need a background job queue

5. **Function-level analysis**: The current graph is file-level. Function-level cross-file call graphs require full AST parsing (planned)

6. **watsonx.ai latency**: AI explanation calls can take 5–15 seconds. A loading spinner is shown; the app never freezes

---

## Future Improvements

- [ ] SQLite persistence layer
- [ ] AST-based function dependency extraction (Babel for JS, ast module for Python)
- [ ] Git diff integration: analyze only changed files
- [ ] WebSocket progress for large repo analysis
- [ ] CI/CD integration (GitHub Actions, Jenkins webhook)
- [ ] Team collaboration: shared reports
- [ ] VS Code extension
- [ ] Historical impact trend tracking

---

## IBM Hackathon Alignment

This application demonstrates:

- **Developer productivity**: Prevent regressions before they happen
- **Code understanding**: Visual dependency graph of the entire codebase
- **Risk awareness**: Quantified, explainable impact scores
- **AI-assisted reasoning**: IBM watsonx.ai explains impact in natural language
- **Testing assistance**: AI-recommended test plans for every change

**IBM Bob** was used as the primary AI-assisted development environment throughout the construction of this application.

**IBM watsonx.ai** provides the AI explanation, test plan generation, and change simulation features at runtime.
