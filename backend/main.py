"""
Dependency Domino - FastAPI Main Application
"""
import os
import sys
import shutil
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import networkx as nx

# Ensure parent dir is in path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from models import (
    Repository, RepositoryResponse, Component, Dependency,
    DependencyGraph, ImpactAnalysis, RiskAssessment, Report,
    AnalysisStatus, Language, NodeType, RiskLevel,
    AnalyzeRequest, ImpactRequest, ExplainRequest, TestPlanRequest,
    ReportRequest, SimulateRequest, SimulationResult, SearchResult,
    LanguageStat, AIExplanation, TestRecommendation
)
from store import store
from analysis.repository_analyzer import (
    safe_extract_zip, walk_repository, compute_language_stats, count_directories
)
from analysis.graph_engine import build_dependency_graph, get_nx_graph
from analysis.impact_engine import compute_impact
from ai.watsonx_service import explain_impact, generate_test_plan, simulate_change
from demo.demo_data import (
    DEMO_REPO_ID, DEMO_REPO_NAME, DEMO_COMPONENTS, DEMO_DEPENDENCIES
)


# ─── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Dependency Domino API",
    description="Know the blast radius before you touch the code.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.upload_dir, exist_ok=True)


# ─── Demo repository initialization ──────────────────────────────────────────

def _init_demo():
    """Load the demo repository into the store on startup."""
    if store.get_repository(DEMO_REPO_ID):
        return

    lang_stats = {}
    for c in DEMO_COMPONENTS:
        lang = c.language.value
        lang_stats[lang] = lang_stats.get(lang, 0) + 1

    total = len(DEMO_COMPONENTS)
    repo = Repository(
        id=DEMO_REPO_ID,
        name=DEMO_REPO_NAME,
        source="demo",
        total_files=total,
        languages=[
            LanguageStat(language=lang, count=count, percentage=round(count / total * 100, 1))
            for lang, count in sorted(lang_stats.items(), key=lambda x: -x[1])
        ],
        directories=18,
        status=AnalysisStatus.COMPLETE,
        analyzed_at=datetime.utcnow().isoformat(),
        is_demo=True,
    )
    store.save_repository(repo)

    for comp in DEMO_COMPONENTS:
        store.save_component(comp)

    store.save_dependencies(DEMO_REPO_ID, DEMO_DEPENDENCIES)

    # Pre-compute impact for all demo components
    G = get_nx_graph(DEMO_COMPONENTS, DEMO_DEPENDENCIES)
    for comp in DEMO_COMPONENTS:
        impact = compute_impact(comp.id, DEMO_COMPONENTS, DEMO_DEPENDENCIES, G)
        comp.risk_score = impact.impact_score
        comp.risk = impact.risk_level
        comp.direct_dependency_count = len(impact.direct_dependencies)
        comp.indirect_dependency_count = len(impact.indirect_dependencies)
        comp.dependent_count = len(impact.dependents)
        comp.test_count = len(impact.related_tests)
        store.save_component(comp)
        store.save_impact(impact)


@app.on_event("startup")
async def startup():
    _init_demo()


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "backend": "CONNECTED",
        "watsonx_configured": settings.watsonx_configured,
        "watsonx_status": settings.watsonx_status,   # CONFIGURED / NOT_CONFIGURED / NO_MODEL
        "model_configured": settings.watsonx_model_configured,
        "demo_loaded": store.get_repository(DEMO_REPO_ID) is not None,
    }


@app.get("/api/config")
async def get_config():
    """
    Returns safe configuration status.
    NEVER exposes API keys, bearer tokens, or secret values.
    """
    return {
        "backend": "CONNECTED",
        "watsonx": {
            "status": settings.watsonx_status,          # CONFIGURED / NOT_CONFIGURED / NO_MODEL
            "configured": settings.watsonx_configured,
            "model_configured": settings.watsonx_model_configured,
            # Expose URL (not a secret) only when configured
            "url": settings.watsonx_url if settings.watsonx_configured else None,
            # Expose model ID (not a secret) when set
            "model_id": settings.watsonx_model_id if settings.watsonx_model_configured else None,
        },
        "max_upload_size_mb": settings.max_upload_size_mb,
        "app_env": settings.app_env,
    }


# ─── Repository endpoints ─────────────────────────────────────────────────────

@app.post("/api/repositories/upload")
async def upload_repository(file: UploadFile = File(...)):
    """Upload and analyze a ZIP repository."""
    # Validate file type
    if not file.filename.endswith(".zip"):
        raise HTTPException(400, "Only .zip files are supported.")

    # Read and check size
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(413, f"File exceeds {settings.max_upload_size_mb}MB limit.")

    repo_id = str(uuid.uuid4())
    repo_name = Path(file.filename).stem

    # Save zip temporarily
    zip_path = os.path.join(settings.upload_dir, f"{repo_id}.zip")
    with open(zip_path, "wb") as f:
        f.write(content)

    # Create initial repository record
    repo = Repository(
        id=repo_id,
        name=repo_name,
        source="upload",
        status=AnalysisStatus.ANALYZING,
        upload_path=zip_path,
    )
    store.save_repository(repo)

    try:
        # Extract safely
        extract_root, extracted_files = safe_extract_zip(zip_path, settings.upload_dir, repo_id)

        # Analyze all files
        components = walk_repository(extract_root, repo_id)

        if not components:
            repo.status = AnalysisStatus.FAILED
            store.save_repository(repo)
            raise HTTPException(422, "No analyzable source files found in repository.")

        for comp in components:
            store.save_component(comp)

        # Build dependency graph
        graph, dependencies, G = build_dependency_graph(components, repo_id)
        store.save_dependencies(repo_id, dependencies)

        # Compute impact and risk for all components
        for comp in components:
            impact = compute_impact(comp.id, components, dependencies, G)
            comp.risk_score = impact.impact_score
            comp.risk = impact.risk_level
            comp.direct_dependency_count = len(impact.direct_dependencies)
            comp.indirect_dependency_count = len(impact.indirect_dependencies)
            comp.dependent_count = len(impact.dependents)
            comp.test_count = len(impact.related_tests)
            store.save_component(comp)
            store.save_impact(impact)

        lang_stats = compute_language_stats(components)
        dirs = count_directories(components)

        repo.total_files = len(components)
        repo.languages = [LanguageStat(**ls) for ls in lang_stats]
        repo.directories = dirs
        repo.status = AnalysisStatus.COMPLETE
        repo.analyzed_at = datetime.utcnow().isoformat()
        store.save_repository(repo)

        return {"repository": repo, "message": "Repository analyzed successfully."}

    except HTTPException:
        raise
    except Exception as e:
        repo.status = AnalysisStatus.FAILED
        store.save_repository(repo)
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@app.get("/api/repositories")
async def list_repositories():
    return {"repositories": store.list_repositories()}


@app.get("/api/repositories/{repo_id}")
async def get_repository(repo_id: str):
    repo = store.get_repository(repo_id)
    if not repo:
        raise HTTPException(404, "Repository not found.")
    return {"repository": repo}


@app.post("/api/repositories/{repo_id}/analyze")
async def re_analyze_repository(repo_id: str):
    """Trigger a fresh analysis of an already-imported repository."""
    repo = store.get_repository(repo_id)
    if not repo:
        raise HTTPException(404, "Repository not found.")
    if repo.is_demo:
        return {"repository": repo, "message": "Demo repository is pre-analyzed."}
    # For uploaded repos, re-run impact scoring
    components = store.get_components_for_repo(repo_id)
    dependencies = store.get_dependencies(repo_id)
    if not components:
        raise HTTPException(422, "No components found. Re-upload the repository.")
    G = get_nx_graph(components, dependencies)
    for comp in components:
        impact = compute_impact(comp.id, components, dependencies, G)
        comp.risk_score = impact.impact_score
        comp.risk = impact.risk_level
        store.save_component(comp)
        store.save_impact(impact)
    repo.status = AnalysisStatus.COMPLETE
    repo.analyzed_at = datetime.utcnow().isoformat()
    store.save_repository(repo)
    return {"repository": repo, "message": "Re-analysis complete."}


@app.get("/api/repositories/{repo_id}/graph")
async def get_dependency_graph(repo_id: str):
    repo = store.get_repository(repo_id)
    if not repo:
        raise HTTPException(404, "Repository not found.")
    components = store.get_components_for_repo(repo_id)
    if not components:
        raise HTTPException(422, "Repository has no analyzed components.")

    # Use stored dependencies for the graph response (don't re-parse)
    dependencies = store.get_dependencies(repo_id)
    if dependencies:
        # Rebuild graph model from stored data (fast, no re-parsing)
        from models import GraphNode, GraphEdge, DependencyGraph as DG
        nodes = [
            GraphNode(
                id=comp.id,
                name=comp.name,
                path=comp.path,
                type=comp.type,
                language=comp.language,
                risk=comp.risk,
                risk_score=comp.risk_score,
                metadata={
                    "lines": comp.metadata.lines,
                    "functions": comp.metadata.functions[:10],
                    "is_test": comp.metadata.is_test,
                }
            )
            for comp in components
        ]
        edges = [
            GraphEdge(
                source=dep.source,
                target=dep.target,
                relationship=dep.relationship,
                dependency_type=dep.dependency_type,
                confidence=dep.confidence,
            )
            for dep in dependencies
        ]
        return DG(
            repository_id=repo_id,
            nodes=nodes,
            edges=edges,
            node_count=len(nodes),
            edge_count=len(edges),
        )

    # Fallback: build from scratch (for repos analyzed before this fix)
    graph, _deps, _G = build_dependency_graph(components, repo_id)
    return graph


@app.get("/api/repositories/{repo_id}/components")
async def get_components(
    repo_id: str,
    language: Optional[str] = Query(None),
    node_type: Optional[str] = Query(None),
    risk: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    repo = store.get_repository(repo_id)
    if not repo:
        raise HTTPException(404, "Repository not found.")
    components = store.get_components_for_repo(repo_id)

    # Filters
    if language:
        components = [c for c in components if c.language.value == language.lower()]
    if node_type:
        components = [c for c in components if c.type.value == node_type.lower()]
    if risk:
        components = [c for c in components if c.risk.value == risk.lower()]
    if search:
        q = search.lower()
        components = [c for c in components if q in c.name.lower() or q in c.path.lower()]

    total = len(components)
    start = (page - 1) * per_page
    end = start + per_page

    return {
        "components": components[start:end],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@app.get("/api/repositories/{repo_id}/risks")
async def get_risk_assessment(repo_id: str):
    repo = store.get_repository(repo_id)
    if not repo:
        raise HTTPException(404, "Repository not found.")
    components = store.get_components_for_repo(repo_id)
    if not components:
        raise HTTPException(422, "No components analyzed yet.")

    counts = {r: 0 for r in RiskLevel}
    for c in components:
        counts[c.risk] = counts.get(c.risk, 0) + 1

    weak_test = sum(1 for c in components if not c.metadata.is_test and c.test_count == 0)

    top_risk = sorted(
        [c for c in components if not c.metadata.is_test],
        key=lambda c: c.risk_score,
        reverse=True
    )[:20]

    return RiskAssessment(
        repository_id=repo_id,
        total_components=len([c for c in components if not c.metadata.is_test]),
        critical_count=counts.get(RiskLevel.CRITICAL, 0),
        high_count=counts.get(RiskLevel.HIGH, 0),
        medium_count=counts.get(RiskLevel.MEDIUM, 0),
        low_count=counts.get(RiskLevel.LOW, 0),
        unknown_count=counts.get(RiskLevel.UNKNOWN, 0),
        weak_test_coverage_count=weak_test,
        top_risk_components=top_risk,
    )


# ─── Component endpoints ──────────────────────────────────────────────────────

@app.get("/api/components/{component_id}")
async def get_component(component_id: str):
    comp = store.get_component(component_id)
    if not comp:
        raise HTTPException(404, "Component not found.")
    return comp


@app.post("/api/components/{component_id}/impact")
async def get_impact(component_id: str):
    comp = store.get_component(component_id)
    if not comp:
        raise HTTPException(404, "Component not found.")

    # Return cached if available
    cached = store.get_impact(component_id)
    if cached:
        return cached

    components = store.get_components_for_repo(comp.repository_id)
    dependencies = store.get_dependencies(comp.repository_id)
    G = get_nx_graph(components, dependencies)
    impact = compute_impact(component_id, components, dependencies, G)
    store.save_impact(impact)
    return impact


@app.post("/api/components/{component_id}/explain")
async def explain_component(component_id: str, body: ExplainRequest):
    comp = store.get_component(component_id)
    if not comp:
        raise HTTPException(404, "Component not found.")

    impact = store.get_impact(component_id)
    if not impact:
        components = store.get_components_for_repo(comp.repository_id)
        dependencies = store.get_dependencies(comp.repository_id)
        G = get_nx_graph(components, dependencies)
        impact = compute_impact(component_id, components, dependencies, G)
        store.save_impact(impact)

    all_comps = store.get_components_for_repo(comp.repository_id)
    comp_map = {c.id: c for c in all_comps}

    explanation = explain_impact(comp, impact, comp_map, body.change_description)
    return explanation


@app.post("/api/components/{component_id}/test-plan")
async def get_test_plan(component_id: str, body: TestPlanRequest):
    comp = store.get_component(component_id)
    if not comp:
        raise HTTPException(404, "Component not found.")

    impact = store.get_impact(component_id)
    if not impact:
        components = store.get_components_for_repo(comp.repository_id)
        dependencies = store.get_dependencies(comp.repository_id)
        G = get_nx_graph(components, dependencies)
        impact = compute_impact(component_id, components, dependencies, G)
        store.save_impact(impact)

    all_comps = store.get_components_for_repo(comp.repository_id)
    comp_map = {c.id: c for c in all_comps}

    plan = generate_test_plan(comp, impact, comp_map, body.change_description)
    return plan


@app.post("/api/components/{component_id}/simulate")
async def simulate_component_change(component_id: str, body: SimulateRequest):
    comp = store.get_component(component_id)
    if not comp:
        raise HTTPException(404, "Component not found.")

    impact = store.get_impact(component_id)
    if not impact:
        components = store.get_components_for_repo(comp.repository_id)
        dependencies = store.get_dependencies(comp.repository_id)
        G = get_nx_graph(components, dependencies)
        impact = compute_impact(component_id, components, dependencies, G)
        store.save_impact(impact)

    all_comps = store.get_components_for_repo(comp.repository_id)
    comp_map = {c.id: c for c in all_comps}

    result = simulate_change(comp, impact, comp_map, body.change_description)
    return result


# ─── Search ───────────────────────────────────────────────────────────────────

@app.get("/api/search")
async def search(
    q: str = Query(..., min_length=1),
    repo_id: Optional[str] = Query(None),
):
    if not q.strip():
        return {"results": []}

    query = q.lower().strip()

    if repo_id:
        repos = [store.get_repository(repo_id)] if store.get_repository(repo_id) else []
    else:
        repos = store.list_repositories()

    results = []
    seen = set()
    for repo in repos:
        if not repo:
            continue
        components = store.get_components_for_repo(repo.id)
        for comp in components:
            if comp.id in seen:
                continue
            score = 0
            if query in comp.name.lower():
                score += 10
            if query in comp.path.lower():
                score += 5
            for fn in comp.metadata.functions:
                if query in fn.lower():
                    score += 3
                    break
            if score > 0:
                seen.add(comp.id)
                results.append(SearchResult(
                    id=comp.id,
                    name=comp.name,
                    path=comp.path,
                    type=comp.type,
                    language=comp.language,
                    risk_score=comp.risk_score,
                    snippet=f"{comp.path} — {comp.type.value} ({comp.language.value})",
                ))

    # Sort by score (name match first)
    results.sort(key=lambda r: (r.name.lower().startswith(query), query in r.name.lower()), reverse=True)
    return {"results": results[:30]}


# ─── Reports ──────────────────────────────────────────────────────────────────

@app.post("/api/reports")
async def generate_report(body: ReportRequest):
    repo = store.get_repository(body.repository_id)
    if not repo:
        raise HTTPException(404, "Repository not found.")

    comp = store.get_component(body.component_id)
    if not comp:
        raise HTTPException(404, "Component not found.")

    impact = store.get_impact(body.component_id)
    if not impact:
        components = store.get_components_for_repo(body.repository_id)
        dependencies = store.get_dependencies(body.repository_id)
        G = get_nx_graph(components, dependencies)
        impact = compute_impact(body.component_id, components, dependencies, G)
        store.save_impact(impact)

    ai_explanation = None
    if body.include_ai:
        all_comps = store.get_components_for_repo(body.repository_id)
        comp_map = {c.id: c for c in all_comps}
        ai_explanation = explain_impact(comp, impact, comp_map)

    from models import Report
    report = Report(
        repository_id=repo.id,
        repository_name=repo.name,
        component_id=comp.id,
        component_path=comp.path,
        impact_score=impact.impact_score,
        risk_level=impact.risk_level,
        direct_dependencies=[
            store.get_component(cid).path if store.get_component(cid) else cid
            for cid in impact.direct_dependencies[:20]
        ],
        indirect_dependencies=[
            store.get_component(cid).path if store.get_component(cid) else cid
            for cid in impact.indirect_dependencies[:20]
        ],
        affected_components=[
            store.get_component(cid).path if store.get_component(cid) else cid
            for cid in impact.affected_components[:30]
        ],
        related_tests=[
            store.get_component(cid).path if store.get_component(cid) else cid
            for cid in impact.related_tests[:15]
        ],
        risk_factors=[rf.description for rf in impact.risk_factors],
        ai_explanation=ai_explanation,
        recommended_actions=(
            ai_explanation.recommended_actions if ai_explanation and ai_explanation.recommended_actions
            else ["Review all direct dependents.", "Run related tests.", "Verify API contracts."]
        ),
    )
    store.save_report(report)
    return report


@app.get("/api/reports/{report_id}")
async def get_report(report_id: str):
    report = store.get_report(report_id)
    if not report:
        raise HTTPException(404, "Report not found.")
    return report
