# Dependency Domino — Architecture Document

## System Overview

Dependency Domino is a pre-change impact intelligence tool. It consists of:

1. A **React frontend** providing the dependency graph visualization, impact analysis UI, and all interactive features
2. A **FastAPI backend** performing static repository analysis, graph construction, impact scoring, and AI integration
3. An **IBM watsonx.ai integration** for AI-powered explanations, test plans, and change simulation

---

## Backend Modules

### `main.py` — FastAPI Application

Entry point. Registers all API routes. Initializes demo data on startup. Configures CORS.

Key design decisions:
- All analysis is done synchronously (suitable for hackathon scale)
- Demo data pre-loaded on startup — no manual DB setup needed
- In-memory store for simplicity; designed for drop-in database replacement

### `config.py` — Settings

Reads all configuration from environment variables using `pydantic-settings`. Provides:
- `settings.watsonx_configured` — boolean, enables AI features
- `settings.max_upload_size_bytes` — enforced in upload endpoint
- `settings.cors_origins_list` — parsed from comma-separated string

### `models.py` — Data Models

All Pydantic v2 models. Notable models:

| Model | Purpose |
|---|---|
| `Repository` | Repository metadata and analysis status |
| `Component` | A single file with parsed metadata |
| `Dependency` | A directed edge between two components |
| `DependencyGraph` | Graph with nodes and edges for the frontend |
| `ImpactAnalysis` | Full impact result including score and risk factors |
| `AIExplanation` | Structured AI or rule-based explanation |
| `RiskAssessment` | Repository-wide risk summary |
| `Report` | Complete downloadable impact report |

### `store.py` — In-Memory Store

Simple dictionary-based store. Maps:
- `repo_id → Repository`
- `component_id → Component`
- `repo_id → [component_id]`
- `repo_id → [Dependency]`
- `component_id → ImpactAnalysis`
- `report_id → Report`

### `analysis/repository_analyzer.py` — Repository Analyzer

Handles ZIP extraction and file parsing:
- **Security**: `safe_extract_zip()` prevents path traversal, skips ignored directories, enforces file size limits
- **Parsing**: Regex-based import extraction for JS/TS and Python
- Language detection by file extension
- Node type inference (test, service, API, file)

### `analysis/graph_engine.py` — Dependency Graph Engine

Builds a NetworkX `DiGraph` from parsed components:
- **Import resolution**: Attempts to resolve relative imports to actual repo files
- **Confidence scoring**: Resolved local imports get 0.9–0.95; unresolved get 0.4
- **Layout**: Simple BFS-based layered layout for initial node positions

### `analysis/impact_engine.py` — Impact Scoring Engine

Deterministic scoring formula:

```
Score = S1 + S2 + S3 + S4 + S5 + S6  (max 100)

S1: Dependent count          0–30
S2: Direct dependency count  0–15
S3: Indirect dependency count 0–15
S4: Betweenness centrality   0–20
S5: Test coverage inverse    0–10
S6: Service/entry-point bonus 0–10
```

All signals are normalized against repository size to avoid large-repo bias.

### `ai/watsonx_service.py` — IBM watsonx.ai Service

Three main functions:
- `explain_impact()` — Structured impact explanation
- `generate_test_plan()` — Test recommendations
- `simulate_change()` — Change consequence analysis

Each function:
1. Builds a controlled, structured context (NOT the full repo)
2. Calls `_call_watsonx()` → IBM IAM token → watsonx.ai generate API
3. Falls back to rule-based analysis if AI unavailable
4. Returns a Pydantic model either way

### `demo/demo_data.py` — Demo Repository

42-component "Developer Portal" application with:
- React frontend (Login, Dashboard, Profile, services, contexts, hooks)
- Python FastAPI backend (auth, users, dashboard routers + services)
- Database layer
- Shared utilities
- Frontend and backend test suites
- 65+ realistic dependency edges

---

## Frontend Architecture

### State Management (Zustand)

Single global store in `store/useStore.js`:
- `activeRepo` — currently loaded repository
- `selectedComponent` — component under analysis
- `impact` — latest impact analysis result
- `explanation` — AI explanation
- `testPlan` — test recommendations
- `graph` — dependency graph data
- `dominoActive / dominoPhase` — animation state machine (0–5)
- `backendStatus / watsonxConfigured` — connection status

### Routing (React Router 6)

```
/overview         → OverviewPage
/repository       → RepositoryPage
/dependency-map   → DependencyMapPage  ← Hero
/impact           → ImpactPage
/risk-center      → RiskCenterPage
/test-impact      → TestImpactPage
/reports          → ReportsPage
/settings         → SettingsPage
```

### Dependency Map (Hero Feature)

`DependencyMapPage.jsx` uses **ReactFlow** for the interactive graph:
- Custom node type `DominoNode` — shows language dot, name, type, risk score
- Dynamic edge coloring based on selection state
- BFS-based layout for initial node positions
- Domino animation via phase state machine:
  - Phase 0: idle
  - Phase 1: selected node activated
  - Phase 2: direct dependencies activated (orange glow)
  - Phase 3: indirect dependencies activated (yellow)
  - Phase 4: tests activated (green)
  - Phase 5: complete

### ImpactPanel Component

Main interaction surface. Five tabs:
1. **Impact** — score, risk factors, affected components, related tests
2. **Explain** — AI or rule-based explanation
3. **Tests** — test plan with existing/recommended/gap sections
4. **Simulate** — change simulation with AI consequence analysis
5. **Report** — downloadable impact report

All tabs work. All buttons call real backend APIs.

---

## Data Flow

```
User selects a ZIP file
        ↓
UploadModal → POST /api/repositories/upload
        ↓
backend: safe_extract_zip() → walk_repository() → analyze_file()
        ↓
build_dependency_graph() → NetworkX DiGraph
        ↓
compute_impact() for all components
        ↓
Repository stored in memory with analyzed components + impact cache
        ↓
Frontend: GET /api/repositories/{id}/graph
        ↓
ReactFlow renders dependency graph
        ↓
User clicks node → GET /api/components/{id}/impact (cached)
        ↓
ImpactPanel shows score, risk, affected components
        ↓
User clicks "Explain Impact" → POST /api/components/{id}/explain
        ↓
watsonx_service.explain_impact() → watsonx.ai API (or rule-based)
        ↓
Structured explanation returned and displayed
```

---

## Security Architecture

| Threat | Mitigation |
|---|---|
| Path traversal in ZIP | `safe_extract_zip()` blocks `../` and absolute paths |
| Code execution | Static analysis only — no `exec`, `eval`, subprocess |
| Secret exposure | All API keys backend-only; frontend receives no credentials |
| Upload abuse | File type check (.zip), size limit (50MB), per-file limit (500KB) |
| CORS | Configurable allowed origins, default: localhost only |
| Input injection | Pydantic validation on all request bodies |

---

## Performance Characteristics

| Operation | Typical Time |
|---|---|
| Demo repo load (startup) | < 200ms |
| ZIP upload + analyze (50 files) | 1–3 seconds |
| Dependency graph build | < 100ms |
| Impact calculation (single) | < 50ms |
| Betweenness centrality (50 nodes) | < 100ms |
| watsonx.ai explanation | 5–15 seconds |
| Rule-based explanation | < 10ms |
| Frontend graph render (50 nodes) | < 500ms |
