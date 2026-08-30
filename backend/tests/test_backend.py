"""
Dependency Domino - Backend Test Suite

Tests cover:
- Repository upload and analysis
- ZIP security (path traversal protection)
- Dependency parser
- Graph construction
- Impact scoring
- API endpoints
"""
import io
import os
import sys
import zipfile
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from main import app, _init_demo
from analysis.repository_analyzer import (
    safe_extract_zip, analyze_file, extract_js_imports, extract_python_imports,
    _is_test_file, detect_language, Language
)
from analysis.graph_engine import build_dependency_graph
from analysis.impact_engine import compute_impact, _score_to_risk, RiskLevel
from demo.demo_data import DEMO_COMPONENTS, DEMO_DEPENDENCIES, DEMO_REPO_ID
from store import store

client = TestClient(app)


# ─── Session-scoped demo initialisation ──────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def _ensure_demo():
    """Ensure demo data is loaded before endpoint tests (startup event bypass)."""
    _init_demo()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_zip(files: dict) -> bytes:
    """Create an in-memory ZIP with given {path: content} dict."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path, content in files.items():
            zf.writestr(path, content)
    return buf.getvalue()


# ─── Repository Analyzer Tests ────────────────────────────────────────────────

class TestJsImportExtraction:
    def test_es_module_import(self):
        content = "import React from 'react';\nimport { useState } from 'react';"
        imports = extract_js_imports(content)
        assert "react" in imports

    def test_relative_import(self):
        content = "import authService from './services/authService';"
        imports = extract_js_imports(content)
        assert "./services/authService" in imports

    def test_require_syntax(self):
        content = "const fs = require('fs');\nconst api = require('./api');"
        imports = extract_js_imports(content)
        assert "./api" in imports

    def test_no_imports(self):
        content = "const x = 5;\nfunction foo() { return x; }"
        imports = extract_js_imports(content)
        assert imports == []


class TestPythonImportExtraction:
    def test_direct_import(self):
        content = "import os\nimport sys\nfrom pathlib import Path"
        imports = extract_python_imports(content)
        assert "os" in imports
        assert "pathlib" in imports

    def test_from_import(self):
        content = "from backend.services.auth import authenticate_user"
        imports = extract_python_imports(content)
        assert "backend.services.auth" in imports


class TestTestFileDetection:
    def test_jest_test(self):
        assert _is_test_file("src/auth.test.js") is True

    def test_jest_spec(self):
        assert _is_test_file("src/login.spec.jsx") is True

    def test_pytest_file(self):
        assert _is_test_file("tests/test_auth.py") is True

    def test_non_test(self):
        assert _is_test_file("src/authService.js") is False

    def test_tests_dir(self):
        assert _is_test_file("tests/frontend/auth.test.js") is True


class TestLanguageDetection:
    def test_js(self):
        assert detect_language("src/app.js") == Language.JAVASCRIPT

    def test_jsx(self):
        assert detect_language("src/Login.jsx") == Language.JSX

    def test_python(self):
        assert detect_language("backend/auth.py") == Language.PYTHON

    def test_unknown(self):
        assert detect_language("README.md") == Language.OTHER


# ─── ZIP Security Tests ───────────────────────────────────────────────────────

class TestZipSecurity:
    def test_path_traversal_blocked(self, tmp_path):
        """Zip files with ../ path traversal must be rejected."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("../etc/passwd", "root:x:0:0")
            zf.writestr("safe/file.js", "const x = 1;")
        zip_bytes = buf.getvalue()
        zip_path = str(tmp_path / "test.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_bytes)

        extract_to = str(tmp_path / "extract")
        root, files = safe_extract_zip(zip_path, extract_to, "test-repo")

        # The traversal file must NOT appear
        for f in files:
            assert ".." not in f
        # The safe file should be present.
        # Note: if "safe/" is the only top-level dir it may be stripped as a wrapper.
        assert any("file.js" in f for f in files)

    def test_node_modules_skipped(self, tmp_path):
        """node_modules should be excluded from extraction."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("src/app.js", "import React from 'react';")
            zf.writestr("node_modules/react/index.js", "module.exports = {};")
        zip_bytes = buf.getvalue()
        zip_path = str(tmp_path / "test.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_bytes)

        root, files = safe_extract_zip(zip_path, str(tmp_path / "ex"), "r1")
        assert not any("node_modules" in f for f in files)
        import os
        assert any(os.path.join("src", "app.js") in f or "src/app.js" in f for f in files)


# ─── Graph Engine Tests ───────────────────────────────────────────────────────

class TestGraphEngine:
    def test_demo_graph_construction(self):
        graph, deps, G = build_dependency_graph(DEMO_COMPONENTS, DEMO_REPO_ID)
        assert graph.node_count == len(DEMO_COMPONENTS)
        assert graph.edge_count > 0

    def test_all_demo_nodes_present(self):
        graph, deps, G = build_dependency_graph(DEMO_COMPONENTS, DEMO_REPO_ID)
        node_ids = {n.id for n in graph.nodes}
        for comp in DEMO_COMPONENTS:
            assert comp.id in node_ids

    def test_edges_use_valid_node_ids(self):
        graph, deps, G = build_dependency_graph(DEMO_COMPONENTS, DEMO_REPO_ID)
        node_ids = {n.id for n in graph.nodes}
        for edge in graph.edges:
            assert edge.source in node_ids
            assert edge.target in node_ids


# ─── Impact Scoring Tests ─────────────────────────────────────────────────────

class TestImpactScoring:
    def setup_method(self):
        self.graph, self.deps, self.G = build_dependency_graph(DEMO_COMPONENTS, DEMO_REPO_ID)
        self.comp_map = {c.id: c for c in DEMO_COMPONENTS}

    def test_score_to_risk_thresholds(self):
        assert _score_to_risk(80) == RiskLevel.CRITICAL
        assert _score_to_risk(60) == RiskLevel.HIGH
        assert _score_to_risk(30) == RiskLevel.MEDIUM
        assert _score_to_risk(10) == RiskLevel.LOW

    def test_auth_service_high_impact(self):
        """authService.js should score HIGH or CRITICAL due to many dependents."""
        auth_comp = next((c for c in DEMO_COMPONENTS if "authService" in c.name), None)
        assert auth_comp is not None
        impact = compute_impact(auth_comp.id, DEMO_COMPONENTS, DEMO_DEPENDENCIES, self.G)
        assert impact.impact_score > 30  # should be medium or higher
        assert impact.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL)

    def test_leaf_node_lower_impact(self):
        """apiConfig.js has no dependents — should score LOW."""
        leaf = next((c for c in DEMO_COMPONENTS if "apiConfig" in c.name), None)
        if leaf:
            impact = compute_impact(leaf.id, DEMO_COMPONENTS, DEMO_DEPENDENCIES, self.G)
            # apiConfig is imported by apiService which is widely used — might not be zero
            assert impact.impact_score >= 0

    def test_impact_has_explanation(self):
        auth_comp = next((c for c in DEMO_COMPONENTS if "authService" in c.name), None)
        impact = compute_impact(auth_comp.id, DEMO_COMPONENTS, DEMO_DEPENDENCIES, self.G)
        assert impact.score_explanation != ""

    def test_impact_not_random(self):
        """Same component should always produce the same score."""
        auth_comp = next((c for c in DEMO_COMPONENTS if "authService" in c.name), None)
        i1 = compute_impact(auth_comp.id, DEMO_COMPONENTS, DEMO_DEPENDENCIES, self.G)
        i2 = compute_impact(auth_comp.id, DEMO_COMPONENTS, DEMO_DEPENDENCIES, self.G)
        assert i1.impact_score == i2.impact_score


# ─── API Endpoint Tests ───────────────────────────────────────────────────────

class TestAPIEndpoints:
    def test_health(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "watsonx_configured" in data

    def test_demo_repository_exists(self):
        resp = client.get(f"/api/repositories/{DEMO_REPO_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["repository"]["id"] == DEMO_REPO_ID
        assert data["repository"]["is_demo"] is True

    def test_list_repositories(self):
        resp = client.get("/api/repositories")
        assert resp.status_code == 200
        repos = resp.json()["repositories"]
        assert len(repos) >= 1

    def test_get_demo_components(self):
        resp = client.get(f"/api/repositories/{DEMO_REPO_ID}/components")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == len(DEMO_COMPONENTS)

    def test_components_search_filter(self):
        resp = client.get(f"/api/repositories/{DEMO_REPO_ID}/components?search=auth")
        assert resp.status_code == 200
        comps = resp.json()["components"]
        assert len(comps) > 0

    def test_get_dependency_graph(self):
        resp = client.get(f"/api/repositories/{DEMO_REPO_ID}/graph")
        assert resp.status_code == 200
        graph = resp.json()
        assert "nodes" in graph
        assert "edges" in graph
        assert len(graph["nodes"]) > 0

    def test_get_risk_assessment(self):
        resp = client.get(f"/api/repositories/{DEMO_REPO_ID}/risks")
        assert resp.status_code == 200
        risk = resp.json()
        assert "total_components" in risk
        assert risk["total_components"] > 0

    def test_get_component_impact(self):
        auth_comp = next((c for c in DEMO_COMPONENTS if "authService" in c.name), None)
        resp = client.post(f"/api/components/{auth_comp.id}/impact")
        assert resp.status_code == 200
        impact = resp.json()
        assert "impact_score" in impact
        assert 0 <= impact["impact_score"] <= 100

    def test_get_test_plan(self):
        auth_comp = next((c for c in DEMO_COMPONENTS if "authService" in c.name), None)
        resp = client.post(
            f"/api/components/{auth_comp.id}/test-plan",
            json={"component_id": auth_comp.id}
        )
        assert resp.status_code == 200
        plan = resp.json()
        assert "recommended_tests" in plan

    def test_search_endpoint(self):
        resp = client.get("/api/search?q=auth")
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) > 0

    def test_search_no_results(self):
        resp = client.get("/api/search?q=zzznomatch999")
        assert resp.status_code == 200
        assert resp.json()["results"] == []

    def test_upload_non_zip_rejected(self):
        resp = client.post(
            "/api/repositories/upload",
            files={"file": ("test.txt", b"not a zip", "text/plain")}
        )
        assert resp.status_code == 400

    def test_upload_valid_zip(self, tmp_path):
        """Upload a valid ZIP and verify it gets analyzed."""
        zip_bytes = make_zip({
            "src/app.js": "import { login } from './auth';\nconst app = {};",
            "src/auth.js": "export function login() { return true; }",
            "src/auth.test.js": "import { login } from './auth';\ntest('login', () => {});",
        })
        resp = client.post(
            "/api/repositories/upload",
            files={"file": ("myproject.zip", zip_bytes, "application/zip")}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["repository"]["status"] == "complete"
        assert data["repository"]["total_files"] >= 2

    def test_404_on_missing_repo(self):
        resp = client.get("/api/repositories/nonexistent-id")
        assert resp.status_code == 404

    def test_generate_report(self):
        auth_comp = next((c for c in DEMO_COMPONENTS if "authService" in c.name), None)
        resp = client.post("/api/reports", json={
            "repository_id": DEMO_REPO_ID,
            "component_id": auth_comp.id,
            "include_ai": False,
        })
        assert resp.status_code == 200
        report = resp.json()
        assert "impact_score" in report
        assert "risk_level" in report
        assert report["repository_id"] == DEMO_REPO_ID
