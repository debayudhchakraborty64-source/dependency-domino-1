"""
Dependency Domino - Dependency Graph Engine
Constructs a NetworkX directed graph from analyzed components.
Resolves import paths to actual repository files where possible.

Edge direction: source → target means "source IMPORTS target"
  i.e., source depends on target.

Impact traversal direction:
  To find what is AFFECTED by changing X:
    → reverse the graph and find all descendants of X.
  This gives all nodes that import X (directly or transitively).
"""
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import networkx as nx

from models import (
    Component, Dependency, DependencyGraph, GraphNode, GraphEdge,
    Language, NodeType, RiskLevel, RelationshipType, DependencyType
)

logger = logging.getLogger(__name__)

# ─── Import resolution helpers ────────────────────────────────────────────────

JS_EXTENSIONS = [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]
PY_EXTENSIONS = [".py"]


def _resolve_js_import(raw_import: str, source_path: str, all_paths_set: set) -> Optional[str]:
    """
    Try to resolve a JS/TS import string to an actual file in the repo.

    Only resolves relative imports (starting with ./ or ../).
    Third-party imports (no leading dot) are external packages — unresolvable.

    Resolution order for './foo':
    1. src/foo  (exact match, no extension)
    2. src/foo.js / src/foo.jsx / src/foo.ts / src/foo.tsx ...
    3. src/foo/index.js / src/foo/index.jsx / ...

    All paths must use forward slashes.
    """
    if not raw_import.startswith("."):
        return None  # external / third-party package

    source_dir = str(Path(source_path).parent).replace("\\", "/")
    # Normalize the candidate path
    if source_dir == ".":
        candidate_base = raw_import.lstrip("./")
        # Actually join properly
        candidate_base = _normalize_path(os.path.join(".", raw_import))
    else:
        candidate_base = _normalize_path(os.path.join(source_dir, raw_import))

    # 1. Exact match (import already includes extension)
    if candidate_base in all_paths_set:
        return candidate_base

    # 2. Try adding each extension
    for ext in JS_EXTENSIONS:
        with_ext = candidate_base + ext
        if with_ext in all_paths_set:
            return with_ext

    # 3. Try index files inside the directory
    for ext in JS_EXTENSIONS:
        index_path = _normalize_path(os.path.join(candidate_base, "index" + ext))
        if index_path in all_paths_set:
            return index_path

    return None  # unresolvable — external or missing file


def _resolve_python_import(raw_import: str, source_path: str, all_paths_set: set) -> Optional[str]:
    """
    Try to resolve a Python import to a repo file.

    Strategy:
    1. Direct path: foo.bar.baz → foo/bar/baz.py
    2. Package: foo.bar → foo/bar/__init__.py
    3. Relative to source directory
    """
    # Strategy 1: module path → file path
    candidate = raw_import.replace(".", "/") + ".py"
    if candidate in all_paths_set:
        return candidate

    # Strategy 2: treat as package (foo/bar/__init__.py)
    pkg_init = raw_import.replace(".", "/") + "/__init__.py"
    if pkg_init in all_paths_set:
        return pkg_init

    # Strategy 3: relative to source file directory
    source_dir = str(Path(source_path).parent).replace("\\", "/")
    parts = raw_import.split(".")

    if source_dir and source_dir != ".":
        candidate2 = _normalize_path(os.path.join(source_dir, "/".join(parts) + ".py"))
        if candidate2 in all_paths_set:
            return candidate2

        # Try package init relative to source dir
        pkg2 = _normalize_path(os.path.join(source_dir, "/".join(parts) + "/__init__.py"))
        if pkg2 in all_paths_set:
            return pkg2

    # Strategy 4: if the module starts with the repo's top-level package,
    # strip the leading package name and try again
    # e.g. "backend.services.auth_service" → try "services/auth_service.py"
    if len(parts) > 1:
        for start in range(1, len(parts)):
            sub_candidate = "/".join(parts[start:]) + ".py"
            if sub_candidate in all_paths_set:
                return sub_candidate
            # also check in subdirs
            for path in all_paths_set:
                if path.endswith(sub_candidate):
                    return path

    return None


def _normalize_path(path: str) -> str:
    """Normalize a path to use forward slashes and resolve . and .."""
    return os.path.normpath(path).replace("\\", "/")


def _infer_confidence(raw_import: str, lang: Language, resolved: bool) -> float:
    """Assign a confidence score to a dependency edge."""
    if not resolved:
        return 0.4  # unresolved = possible
    if lang in (Language.JAVASCRIPT, Language.JSX, Language.TYPESCRIPT, Language.TSX):
        if raw_import.startswith("."):
            return 0.95  # relative import resolved = high confidence
        return 0.6   # absolute/bare import resolved = medium
    elif lang == Language.PYTHON:
        return 0.9
    return 0.7


def build_dependency_graph(
    components: List[Component],
    repo_id: str
) -> Tuple[DependencyGraph, List[Dependency], nx.DiGraph]:
    """
    Build a directed dependency graph from repository components.

    Edge direction: A → B means "A imports B" (A depends on B).

    Returns (DependencyGraph model, List[Dependency], nx.DiGraph).
    """
    if not components:
        empty = DependencyGraph(
            repository_id=repo_id, nodes=[], edges=[], node_count=0, edge_count=0
        )
        return empty, [], nx.DiGraph()

    # Build lookup maps
    path_to_comp: Dict[str, Component] = {c.path: c for c in components}
    all_paths_set = set(path_to_comp.keys())

    G = nx.DiGraph()

    # Add all nodes
    for comp in components:
        G.add_node(comp.id, component=comp)

    dependencies: List[Dependency] = []
    resolved_count = 0
    unresolved_count = 0

    for comp in components:
        raw_imports = comp.metadata.imports or []

        for raw_import in raw_imports:
            resolved_path: Optional[str] = None
            dep_type = DependencyType.POSSIBLE
            confidence = 0.4
            relationship = RelationshipType.IMPORT

            if comp.language in (Language.JAVASCRIPT, Language.JSX, Language.TYPESCRIPT, Language.TSX):
                resolved_path = _resolve_js_import(raw_import, comp.path, all_paths_set)
            elif comp.language == Language.PYTHON:
                resolved_path = _resolve_python_import(raw_import, comp.path, all_paths_set)
            # OTHER languages: no resolution attempt

            if resolved_path and resolved_path in path_to_comp:
                target_comp = path_to_comp[resolved_path]
                confidence = _infer_confidence(raw_import, comp.language, True)
                dep_type = DependencyType.DIRECT
                resolved_count += 1

                # Avoid self-loops
                if target_comp.id == comp.id:
                    continue

                dep = Dependency(
                    source=comp.id,
                    target=target_comp.id,
                    source_path=comp.path,
                    target_path=target_comp.path,
                    relationship=relationship,
                    dependency_type=dep_type,
                    confidence=confidence,
                    raw_import=raw_import,
                )
                dependencies.append(dep)
                G.add_edge(comp.id, target_comp.id, dependency=dep)
            else:
                if raw_import.startswith("."):
                    # Relative import that didn't resolve — log it
                    unresolved_count += 1
                    logger.debug(
                        "Unresolved relative import: %s in %s (tried %s)",
                        raw_import, comp.path, resolved_path
                    )
                # External/third-party: silently skip (not a bug, not a graph edge)

    logger.info(
        "Graph built: %d nodes, %d edges (%d resolved, %d unresolved relative imports)",
        len(components), len(dependencies), resolved_count, unresolved_count
    )

    # Build graph model for API response
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

    graph = DependencyGraph(
        repository_id=repo_id,
        nodes=nodes,
        edges=edges,
        node_count=len(nodes),
        edge_count=len(edges),
    )

    return graph, dependencies, G


def get_nx_graph(components: List[Component], dependencies: List[Dependency]) -> nx.DiGraph:
    """Reconstruct a NetworkX graph from stored components + dependencies."""
    G = nx.DiGraph()
    for comp in components:
        G.add_node(comp.id)
    for dep in dependencies:
        G.add_edge(dep.source, dep.target)
    return G
