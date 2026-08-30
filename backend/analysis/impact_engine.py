"""
Dependency Domino - Impact Scoring Engine

SCORING FORMULA (deterministic, explainable):

  impact_score = weighted sum of normalized signals, capped at 100

  Signals and weights:
  1. Dependent count (how many files depend ON this):  30 points max
  2. Direct dependency count:                          15 points max
  3. Indirect dependency count:                        15 points max
  4. Betweenness centrality in graph:                  20 points max
  5. Test coverage signal (inverse - lower = higher risk): 10 points max
  6. Entry-point / service / API bonus:                10 points max

  Total max: 100

  Risk Level thresholds:
    CRITICAL: score >= 75
    HIGH:     score >= 50
    MEDIUM:   score >= 25
    LOW:      score < 25
"""
import math
from typing import List, Dict, Optional, Set, Tuple
import networkx as nx

from models import (
    Component, Dependency, ImpactAnalysis, RiskFactor,
    RiskLevel, NodeType
)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _score_to_risk(score: float) -> RiskLevel:
    if score >= 75:
        return RiskLevel.CRITICAL
    if score >= 50:
        return RiskLevel.HIGH
    if score >= 25:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def get_direct_dependencies(component_id: str, dependencies: List[Dependency]) -> List[str]:
    """Components that this component directly imports."""
    return [d.target for d in dependencies if d.source == component_id]


def get_dependents(component_id: str, dependencies: List[Dependency]) -> List[str]:
    """Components that import THIS component (reverse direction)."""
    return [d.source for d in dependencies if d.target == component_id]


def get_indirect_dependencies(
    component_id: str,
    G: nx.DiGraph,
    direct_deps: List[str]
) -> List[str]:
    """
    All reachable nodes from this component excluding direct deps
    (i.e., depth >= 2 in outgoing direction).
    """
    if component_id not in G:
        return []
    try:
        all_reachable = set(nx.descendants(G, component_id))
    except Exception:
        all_reachable = set()
    direct_set = set(direct_deps)
    return list(all_reachable - direct_set - {component_id})


def get_all_affected(
    component_id: str,
    G: nx.DiGraph,
) -> List[str]:
    """
    Everything affected if this component changes:
    = all nodes that transitively depend ON this component
    (reverse reachability).
    """
    if component_id not in G:
        return []
    G_rev = G.reverse(copy=True)
    try:
        affected = set(nx.descendants(G_rev, component_id))
    except Exception:
        affected = set()
    return list(affected - {component_id})


def find_related_tests(
    component_id: str,
    affected_ids: List[str],
    components: List[Component],
) -> List[str]:
    """Find test components related to the component or its affected set."""
    test_components = [c for c in components if c.metadata.is_test]
    target_ids = set(affected_ids) | {component_id}
    related = []
    for tc in test_components:
        # Test is related if its imports include any affected path fragments
        # or if the test name matches any affected component name
        for affected_id in target_ids:
            if tc.id == affected_id:
                related.append(tc.id)
                break
    return list(set(related))


def find_related_tests_by_name(
    component_id: str,
    affected_ids: List[str],
    all_components: List[Component],
    dependencies: List[Dependency],
) -> List[str]:
    """
    Improved test finder: matches tests by name proximity and by dependency edges.
    """
    comp_map = {c.id: c for c in all_components}
    target_comp = comp_map.get(component_id)
    if not target_comp:
        return []

    affected_set = set(affected_ids) | {component_id}
    affected_names = {
        comp_map[cid].name.lower().replace(".jsx", "").replace(".js", "").replace(".py", "").replace(".ts", "").replace(".tsx", "")
        for cid in affected_set if cid in comp_map
    }

    test_ids = []
    for comp in all_components:
        if not comp.metadata.is_test:
            continue
        test_base = comp.name.lower().replace(".test.js", "").replace(".spec.js", "").replace(".test.jsx", "").replace(".spec.jsx", "").replace(".test.ts", "").replace(".spec.ts", "").replace("test_", "").replace("_test", "")
        if any(name in test_base or test_base in name for name in affected_names):
            test_ids.append(comp.id)
            continue
        # Also check if test directly depends on any affected component
        test_imports = {d.target for d in dependencies if d.source == comp.id}
        if test_imports & affected_set:
            test_ids.append(comp.id)

    return list(set(test_ids))


def compute_betweenness(component_id: str, G: nx.DiGraph) -> float:
    """Normalized betweenness centrality for the given node."""
    if len(G.nodes) < 3:
        return 0.0
    try:
        centrality = nx.betweenness_centrality(G, normalized=True)
        return centrality.get(component_id, 0.0)
    except Exception:
        return 0.0


def compute_impact(
    component_id: str,
    components: List[Component],
    dependencies: List[Dependency],
    G: nx.DiGraph,
) -> ImpactAnalysis:
    """
    Compute a deterministic, explainable impact analysis for a component.

    Scoring is always attempted. UNKNOWN risk is only used when the component
    is genuinely not found.
    """
    comp_map = {c.id: c for c in components}
    target = comp_map.get(component_id)

    if not target:
        return ImpactAnalysis(
            component_id=component_id,
            component_path="unknown",
            impact_score=0,
            risk_level=RiskLevel.UNKNOWN,
            insufficient_data=True,
            score_explanation="Component not found in repository.",
        )

    # ── Gather signals ────────────────────────────────────────────────────────
    direct_deps = get_direct_dependencies(component_id, dependencies)
    indirect_deps = get_indirect_dependencies(component_id, G, direct_deps)
    dependents = get_dependents(component_id, dependencies)
    affected = get_all_affected(component_id, G)
    related_tests = find_related_tests_by_name(component_id, affected + dependents, components, dependencies)

    total_non_test = max(len([c for c in components if not c.metadata.is_test]), 1)
    test_components = [c for c in components if c.metadata.is_test]
    total_tests = len(test_components)

    # ── Signal 1: Dependent count (30 pts max) ────────────────────────────────
    # Normalize against total component count
    dep_ratio = len(dependents) / total_non_test
    s1 = _clamp(dep_ratio * 200, 0, 30)  # generous scaling

    # ── Signal 2: Direct dependency count (15 pts max) ────────────────────────
    dd_ratio = len(direct_deps) / max(total_non_test, 1)
    s2 = _clamp(dd_ratio * 150, 0, 15)

    # ── Signal 3: Indirect dependency count (15 pts max) ─────────────────────
    id_ratio = len(indirect_deps) / max(total_non_test, 1)
    s3 = _clamp(id_ratio * 100, 0, 15)

    # ── Signal 4: Betweenness centrality (20 pts max) ─────────────────────────
    centrality = compute_betweenness(component_id, G)
    s4 = _clamp(centrality * 200, 0, 20)

    # ── Signal 5: Test coverage inverse (10 pts max) ─────────────────────────
    # If 0 tests cover this component → full 10 pts risk
    # If tests exist → proportionally lower
    if total_tests == 0 or len(related_tests) == 0:
        s5 = 10.0
    else:
        test_ratio = len(related_tests) / max(len(dependents) + 1, 1)
        s5 = _clamp(10 - (test_ratio * 20), 0, 10)

    # ── Signal 6: Entry-point / service bonus (10 pts max) ────────────────────
    s6 = 0.0
    if target.type in (NodeType.SERVICE, NodeType.API):
        s6 += 5.0
    if target.metadata.is_entry_point or "index" in target.name.lower():
        s6 += 5.0

    raw_score = s1 + s2 + s3 + s4 + s5 + s6
    impact_score = round(_clamp(raw_score, 0, 100), 1)
    risk_level = _score_to_risk(impact_score)

    # ── Build risk factor list ────────────────────────────────────────────────
    risk_factors: List[RiskFactor] = []
    if len(dependents) > 3:
        risk_factors.append(RiskFactor(
            factor="High dependent count",
            weight=s1,
            description=f"{len(dependents)} components depend on this file"
        ))
    if len(direct_deps) > 5:
        risk_factors.append(RiskFactor(
            factor="High direct dependency count",
            weight=s2,
            description=f"Imports {len(direct_deps)} other components"
        ))
    if len(indirect_deps) > 5:
        risk_factors.append(RiskFactor(
            factor="Wide indirect blast radius",
            weight=s3,
            description=f"{len(indirect_deps)} indirectly reachable components"
        ))
    if centrality > 0.05:
        risk_factors.append(RiskFactor(
            factor="High graph centrality",
            weight=s4,
            description=f"Acts as a hub in the dependency graph (centrality={centrality:.2f})"
        ))
    if s5 > 5:
        risk_factors.append(RiskFactor(
            factor="Limited test coverage",
            weight=s5,
            description="Few or no tests detected that cover this component"
        ))
    if target.type in (NodeType.SERVICE, NodeType.API):
        risk_factors.append(RiskFactor(
            factor="Critical service/API component",
            weight=s6,
            description="Service or API components affect multiple consumers"
        ))

    explanation_parts = [
        f"Impact score {impact_score}/100 computed from {len(dependents)} dependents, "
        f"{len(direct_deps)} direct deps, {len(indirect_deps)} indirect deps, "
        f"centrality={centrality:.3f}, test coverage signal={s5:.1f}/10."
    ]
    if not risk_factors:
        explanation_parts.append("No significant risk factors detected.")

    all_affected = list(set(affected + dependents))

    return ImpactAnalysis(
        component_id=component_id,
        component_path=target.path,
        impact_score=impact_score,
        risk_level=risk_level,
        direct_dependencies=direct_deps[:50],
        indirect_dependencies=indirect_deps[:50],
        dependents=dependents[:50],
        affected_components=all_affected[:100],
        related_tests=related_tests[:30],
        risk_factors=risk_factors,
        score_explanation=" ".join(explanation_parts),
        insufficient_data=False,
    )
