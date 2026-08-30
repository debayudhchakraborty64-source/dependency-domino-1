"""
Dependency Domino – IBM watsonx.ai Service
===========================================

Integrates IBM watsonx.ai (via the official `ibm-watsonx-ai` Python SDK) to
produce structured AI explanations, test plans, and change-simulation analyses.

Design principles
-----------------
* The deterministic analysis engine runs FIRST; AI augments, not replaces it.
* The AI receives ONLY a structured context – never raw repo files, secrets,
  .env contents, binary files, node_modules, or .venv.
* If watsonx.ai is unavailable for any reason the app continues with the
  rule-based (deterministic) fallback and clearly labels the output.
* API keys are NEVER logged, returned in responses, or sent to the frontend.

Environment variables required
-------------------------------
    WATSONX_APIKEY        – IBM Cloud API key
    WATSONX_PROJECT_ID    – watsonx.ai project identifier
    WATSONX_URL           – service endpoint (default: https://us-south.ml.cloud.ibm.com)
    WATSONX_MODEL_ID      – model to use (e.g. ibm/granite-13b-instruct-v2)
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional

from config import settings
from models import (
    Component,
    ImpactAnalysis,
    AIExplanation,
    TestRecommendation,
    SimulationResult,
    RiskLevel,
)

logger = logging.getLogger(__name__)

# ─── SDK import (optional – app works without it) ────────────────────────────

try:
    from ibm_watsonx_ai import Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False
    logger.warning(
        "ibm-watsonx-ai SDK is not installed. "
        "Install it with: pip install ibm-watsonx-ai  "
        "AI features will fall back to rule-based analysis."
    )

# ─── Module-level cached model client ────────────────────────────────────────

_model_client: Optional[object] = None
_client_error: str = ""


def _get_model_client():
    """
    Return a cached ModelInference instance, creating it on first call.

    Returns None (and logs a warning) if configuration is incomplete or SDK
    initialisation fails.  Never raises – callers must handle None.
    """
    global _model_client, _client_error

    if _model_client is not None:
        return _model_client

    if not _SDK_AVAILABLE:
        _client_error = "ibm-watsonx-ai SDK not installed"
        return None

    if not settings.watsonx_configured:
        _client_error = "WATSONX_APIKEY or WATSONX_PROJECT_ID not set"
        return None

    if not settings.watsonx_model_configured:
        _client_error = "WATSONX_MODEL_ID not set"
        return None

    try:
        credentials = Credentials(
            url=settings.watsonx_url,
            api_key=settings.effective_api_key,  # never logged
        )
        # validate=False defers credential/model validation to the first
        # generate_text call, avoiding an upfront HTTP round-trip that can
        # fail even with valid credentials (SDK >= 1.0).
        _model_client = ModelInference(
            model_id=settings.watsonx_model_id,
            credentials=credentials,
            project_id=settings.watsonx_project_id,
            params={
                GenParams.DECODING_METHOD: "greedy",
                GenParams.MAX_NEW_TOKENS: 700,
                GenParams.TEMPERATURE: 0.1,
                GenParams.STOP_SEQUENCES: ["---END---"],
            },
            validate=False,
        )
        _client_error = ""
        logger.info(
            "watsonx.ai client initialised (model=%s, url=%s)",
            settings.watsonx_model_id,
            settings.watsonx_url,
        )
        return _model_client
    except Exception as exc:
        # Log WITHOUT exposing the API key
        safe_msg = str(exc).replace(settings.effective_api_key, "***") if settings.effective_api_key else str(exc)
        logger.warning("Failed to initialise watsonx.ai client: %s", safe_msg)
        _client_error = safe_msg
        return None


def _reset_client():
    """Force re-initialisation on next call (used in tests)."""
    global _model_client, _client_error
    _model_client = None
    _client_error = ""


def _call_watsonx(prompt: str, max_tokens: int = 700) -> tuple[Optional[str], str]:
    """
    Make a text-generation request to watsonx.ai.

    Returns (generated_text, failure_reason).
    On success failure_reason is "".
    On any failure returns (None, human-readable reason).

    API keys are NEVER included in the returned failure reason.
    """
    model = _get_model_client()
    if model is None:
        reason = _client_error or _fallback_reason()
        return None, reason

    try:
        response = model.generate_text(prompt=prompt)
        if response:
            return response.strip(), ""
        return None, "Empty response from watsonx.ai"
    except Exception as exc:
        safe_msg = _sanitise_error(str(exc))
        logger.warning("watsonx.ai generate_text failed: %s", safe_msg)
        return None, safe_msg


def _sanitise_error(msg: str) -> str:
    """Remove any API key value from an error string before logging/returning."""
    key = settings.effective_api_key
    if key and key in msg:
        msg = msg.replace(key, "***")
    return msg


def _fallback_reason() -> str:
    """Produce a safe human-readable reason for unavailability."""
    if not _SDK_AVAILABLE:
        return "ibm-watsonx-ai SDK not installed"
    if not settings.effective_api_key:
        return "WATSONX_APIKEY not set"
    if not settings.watsonx_project_id:
        return "WATSONX_PROJECT_ID not set"
    if not settings.watsonx_model_id:
        return "WATSONX_MODEL_ID not set – watsonx.ai model is not configured."
    return "watsonx.ai is unavailable"


# ─── Context builder ─────────────────────────────────────────────────────────

def _build_impact_context(
    component: Component,
    impact: ImpactAnalysis,
    all_components_map: dict,
) -> str:
    """
    Build a concise, structured context string for the AI prompt.

    Only sends: component metadata, impact scores, dependency names, risk
    factors.  Never sends: file content, secrets, env values, or binary data.
    """
    dep_names = [
        all_components_map[cid].path if cid in all_components_map else cid
        for cid in impact.direct_dependencies[:8]
    ]
    indirect_names = [
        all_components_map[cid].path if cid in all_components_map else cid
        for cid in impact.indirect_dependencies[:6]
    ]
    dependent_names = [
        all_components_map[cid].path if cid in all_components_map else cid
        for cid in impact.dependents[:8]
    ]
    affected_names = [
        all_components_map[cid].path if cid in all_components_map else cid
        for cid in impact.affected_components[:10]
    ]
    test_names = [
        all_components_map[cid].path if cid in all_components_map else cid
        for cid in impact.related_tests[:6]
    ]
    risk_desc = [rf.description for rf in impact.risk_factors[:5]]

    confidence_note = (
        "Note: static analysis – relationships are inferred from imports, not runtime behaviour."
    )
    if impact.insufficient_data:
        confidence_note = "Note: insufficient repository data for a reliable risk estimate."

    ctx = (
        f"Component: {component.path}\n"
        f"Language: {component.language.value}\n"
        f"Type: {component.type.value}\n"
        f"Impact Score (deterministic): {impact.impact_score}/100\n"
        f"Risk Level (deterministic): {impact.risk_level.value.upper()}\n"
        f"Direct Dependencies ({len(impact.direct_dependencies)}): {', '.join(dep_names) or 'none'}\n"
        f"Indirect Dependencies ({len(impact.indirect_dependencies)}): {', '.join(indirect_names) or 'none'}\n"
        f"Dependents – files that import this ({len(impact.dependents)}): {', '.join(dependent_names) or 'none'}\n"
        f"Affected Components ({len(impact.affected_components)}): {', '.join(affected_names) or 'none'}\n"
        f"Related Tests ({len(impact.related_tests)}): {', '.join(test_names) or 'none'}\n"
        f"Risk Factors: {'; '.join(risk_desc) or 'none'}\n"
        f"Functions in file: {', '.join(component.metadata.functions[:8]) or 'none'}\n"
        f"Deterministic score explanation: {impact.score_explanation}\n"
        f"{confidence_note}"
    )
    return ctx


# ─── Explain endpoint ─────────────────────────────────────────────────────────

def explain_impact(
    component: Component,
    impact: ImpactAnalysis,
    all_components_map: dict,
    change_description: Optional[str] = None,
) -> AIExplanation:
    """
    Generate a structured AI explanation for the deterministic impact analysis.

    watsonx.ai is asked to EXPLAIN the deterministic findings, not invent new
    dependency relationships.  The model is instructed to distinguish between
    detected, inferred, and possible impacts.

    Falls back to rule-based explanation if AI is unavailable.
    """
    if not settings.watsonx_configured or not settings.watsonx_model_configured:
        reason = _fallback_reason()
        return _rule_based_explanation(component, impact, all_components_map, fallback_reason=reason)

    ctx = _build_impact_context(component, impact, all_components_map)
    change_ctx = f"\nProposed change: {change_description}" if change_description else ""

    prompt = (
        "You are a senior software architect. "
        "The following is a DETERMINISTIC static-analysis result for a software component. "
        "Your task is to EXPLAIN these findings clearly to a developer. "
        "Do NOT invent dependency relationships that are not listed here. "
        "Clearly distinguish: (a) detected dependencies, (b) inferred relationships, "
        "(c) possible impacts, (d) things that are unknown or uncertain.\n\n"
        f"{ctx}{change_ctx}\n\n"
        "Respond with EXACTLY this structure (fill in every section, be concise):\n"
        "SUMMARY: [1-2 sentence summary of the impact]\n"
        "WHY_IT_MATTERS: [Why this component is important in the codebase]\n"
        "POTENTIAL_IMPACT: [What could break or be affected]\n"
        "RISK_FACTORS:\n- [risk factor 1]\n- [risk factor 2]\n"
        "RECOMMENDED_ACTIONS:\n- [action 1]\n- [action 2]\n"
        "TEST_RECOMMENDATIONS:\n- [test recommendation 1]\n- [test recommendation 2]\n"
        "UNCERTAINTIES:\n- [thing that is uncertain or unknown]\n"
        "---END---"
    )

    ai_text, failure_reason = _call_watsonx(prompt, max_tokens=700)

    if ai_text:
        return _parse_ai_explanation(ai_text, component.id, settings.watsonx_model_id)
    else:
        logger.info("watsonx.ai unavailable, using rule-based fallback: %s", failure_reason)
        return _rule_based_explanation(
            component, impact, all_components_map, fallback_reason=failure_reason
        )


def _parse_ai_explanation(text: str, component_id: str, model_id: str) -> AIExplanation:
    """Parse the structured AI response into an AIExplanation model."""

    def _extract_section(label: str, full_text: str) -> str:
        pattern = rf"{label}:\s*(.*?)(?=\n[A-Z_]{{3,}}:|$)"
        m = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else ""

    def _extract_bullets(label: str, full_text: str) -> List[str]:
        section = _extract_section(label, full_text)
        lines = [ln.strip().lstrip("-•*").strip() for ln in section.split("\n") if ln.strip()]
        return [ln for ln in lines if ln and not ln.lower().startswith("---")]

    # Provenance fields – populated from context (deterministic, not AI-invented)
    return AIExplanation(
        component_id=component_id,
        summary=_extract_section("SUMMARY", text),
        why_it_matters=_extract_section("WHY_IT_MATTERS", text) or _extract_section("WHY IT MATTERS", text),
        potential_impact=_extract_section("POTENTIAL_IMPACT", text) or _extract_section("POTENTIAL IMPACT", text),
        risk_factors=_extract_bullets("RISK_FACTORS", text) or _extract_bullets("RISK FACTORS", text),
        recommended_actions=_extract_bullets("RECOMMENDED_ACTIONS", text) or _extract_bullets("RECOMMENDED ACTIONS", text),
        test_recommendations=_extract_bullets("TEST_RECOMMENDATIONS", text) or _extract_bullets("TEST RECOMMENDATIONS", text),
        uncertainties=_extract_bullets("UNCERTAINTIES", text),
        ai_available=True,
        ai_source="watsonx",
        model_used=model_id,
        fallback_reason="",
    )


def _rule_based_explanation(
    component: Component,
    impact: ImpactAnalysis,
    all_components_map: dict,
    fallback_reason: str = "",
) -> AIExplanation:
    """
    Deterministic, rule-based fallback explanation when AI is unavailable.
    Clearly labelled so the frontend can display the appropriate message.
    """
    dep_count = len(impact.direct_dependencies)
    affected_count = len(impact.affected_components)
    test_count = len(impact.related_tests)
    risk = impact.risk_level.value.upper()

    summary = (
        f"{component.name} has a {risk} deterministic impact score of "
        f"{impact.impact_score}/100. "
        f"Changes may affect up to {affected_count} other components. "
        "IBM watsonx.ai is unavailable. Showing rule-based analysis."
    )

    why = f"This component is imported by {len(impact.dependents)} other file(s)."
    if dep_count > 0:
        why += f" It directly imports {dep_count} dependencies."
    if component.type.value in ("service", "api"):
        why += " As a service/API component it has broad system-wide reach."

    potential = f"Modifying this component could cascade to {affected_count} affected component(s)."
    if test_count > 0:
        potential += f" {test_count} related test file(s) should be re-run."
    else:
        potential += " No related tests were detected – regression risk is elevated."

    risk_factors = [rf.description for rf in impact.risk_factors]
    if not risk_factors:
        risk_factors = ["No significant risk factors detected by static analysis."]

    actions = [
        "Review all direct dependents before committing.",
        "Run the full test suite for related modules.",
        "Verify API contracts remain unchanged.",
    ]
    if affected_count > 5:
        actions.append("Consider a staged rollout or feature flag to reduce blast radius.")

    tests = [
        all_components_map[cid].path
        for cid in impact.related_tests[:6]
        if cid in all_components_map
    ]
    if not tests:
        tests = ["No test files detected for this component – consider adding coverage."]

    uncertainties = [
        "Relationships are inferred from static import analysis, not runtime behaviour.",
        "Dynamic imports and runtime dependencies may not be fully captured.",
    ]
    if impact.insufficient_data:
        uncertainties.append("Insufficient repository data for a reliable risk estimate.")

    return AIExplanation(
        component_id=component.id,
        summary=summary,
        why_it_matters=why,
        potential_impact=potential,
        risk_factors=risk_factors,
        recommended_actions=actions,
        test_recommendations=tests,
        uncertainties=uncertainties,
        detected_dependencies=[
            all_components_map[cid].path
            for cid in impact.direct_dependencies[:8]
            if cid in all_components_map
        ],
        inferred_relationships=[
            all_components_map[cid].path
            for cid in impact.indirect_dependencies[:6]
            if cid in all_components_map
        ],
        possible_impacts=[
            all_components_map[cid].path
            for cid in impact.affected_components[:8]
            if cid in all_components_map
        ],
        ai_available=False,
        ai_source="rule-based",
        model_used="rule-based",
        fallback_reason=fallback_reason,
    )


# ─── Test-plan endpoint ───────────────────────────────────────────────────────

def generate_test_plan(
    component: Component,
    impact: ImpactAnalysis,
    all_components_map: dict,
    change_description: Optional[str] = None,
) -> TestRecommendation:
    """
    Generate a recommended test plan.

    Uses watsonx.ai when available; falls back to rule-based analysis.
    The output is clearly labelled as AI-generated and not guaranteed complete.
    """
    existing_tests = [
        all_components_map[cid].path
        for cid in impact.related_tests
        if cid in all_components_map
    ]

    if not settings.watsonx_configured or not settings.watsonx_model_configured:
        reason = _fallback_reason()
        plan = _rule_based_test_plan(component, impact, all_components_map)
        plan.fallback_reason = reason
        return plan

    ctx = _build_impact_context(component, impact, all_components_map)
    change_ctx = f"\nProposed change: {change_description}" if change_description else ""

    prompt = (
        "You are a QA engineer reviewing a software change-impact report. "
        "Based ONLY on the repository evidence provided below, produce a specific "
        "test plan. Do NOT invent test scenarios that have no basis in the analysis.\n\n"
        f"{ctx}{change_ctx}\n"
        f"Existing detected tests: {', '.join(existing_tests) or 'none'}\n\n"
        "For each test area produce one line in this format:\n"
        "- [TEST AREA] | Reason: [why] | Existing: [yes/no] | Priority: [high/medium/low]\n"
        "Then list POTENTIAL GAPS (untested areas) as:\n"
        "GAPS:\n- [gap description]\n"
        "---END---"
    )

    ai_text, failure_reason = _call_watsonx(prompt, max_tokens=500)

    if ai_text:
        lines = [
            ln.strip().lstrip("-•*").strip()
            for ln in ai_text.split("\n")
            if ln.strip() and not ln.strip().startswith("---")
        ]
        # Separate gaps section
        gap_start = next(
            (i for i, ln in enumerate(lines) if ln.upper().startswith("GAP")), len(lines)
        )
        test_lines = [ln for ln in lines[:gap_start] if ln]
        gap_lines = [ln.lstrip("GAPS:").strip() for ln in lines[gap_start + 1:] if ln]

        return TestRecommendation(
            component_id=component.id,
            existing_tests=existing_tests,
            recommended_tests=test_lines[:15],
            coverage_gaps=gap_lines[:8] or _detect_coverage_gaps(component, impact, all_components_map),
            ai_generated=True,
            ai_available=True,
            ai_source="watsonx",
            fallback_reason="",
            label="AI-generated test recommendation",
            disclaimer=(
                "This test plan is AI-generated and not guaranteed to be complete. "
                "Review and supplement with domain knowledge."
            ),
        )
    else:
        logger.info("watsonx.ai unavailable for test plan, using fallback: %s", failure_reason)
        plan = _rule_based_test_plan(component, impact, all_components_map)
        plan.fallback_reason = failure_reason
        return plan


def _detect_coverage_gaps(
    component: Component,
    impact: ImpactAnalysis,
    all_components_map: dict,
) -> List[str]:
    """Identify likely coverage gaps: affected components with no detected test."""
    gaps = []
    for cid in impact.affected_components[:20]:
        if cid not in all_components_map:
            continue
        comp = all_components_map[cid]
        if comp.metadata.is_test:
            continue
        has_test = any(
            comp.name.lower()
            .replace(".js", "").replace(".jsx", "").replace(".py", "")
            .replace(".ts", "").replace(".tsx", "")
            in all_components_map[t].name.lower()
            for t in impact.related_tests
            if t in all_components_map
        )
        if not has_test:
            gaps.append(f"No detected test covering {comp.path}")
    return gaps[:8]


def _rule_based_test_plan(
    component: Component,
    impact: ImpactAnalysis,
    all_components_map: dict,
) -> TestRecommendation:
    """Deterministic test plan based on component type and impact."""
    existing = [
        all_components_map[cid].path
        for cid in impact.related_tests
        if cid in all_components_map
    ]
    gaps = _detect_coverage_gaps(component, impact, all_components_map)

    base = (
        component.name
        .replace(".js", "").replace(".jsx", "")
        .replace(".ts", "").replace(".tsx", "").replace(".py", "")
    )

    recommended: List[str] = [f"Run unit tests for {component.path}"]
    if component.type.value == "service":
        recommended.append(f"Run integration tests for {base} service")
        recommended.append(f"Verify all API contracts consumed by {base}")
    if len(impact.dependents) > 0:
        recommended.append(
            f"Run regression tests for {len(impact.dependents)} dependent component(s)"
        )
    if impact.impact_score > 50:
        recommended.append("Run full end-to-end test suite")
    if not existing:
        recommended.append(f"Create new test file: {base}.test.js (or equivalent)")

    return TestRecommendation(
        component_id=component.id,
        existing_tests=existing,
        recommended_tests=recommended,
        coverage_gaps=gaps,
        ai_generated=False,
        ai_available=False,
        ai_source="rule-based",
        label="Rule-based test recommendation",
        disclaimer=(
            "IBM watsonx.ai is unavailable. Showing rule-based analysis. "
            "This test plan is based on static analysis only."
        ),
    )


# ─── Change-simulation endpoint ───────────────────────────────────────────────

def simulate_change(
    component: Component,
    impact: ImpactAnalysis,
    all_components_map: dict,
    change_description: str,
) -> SimulationResult:
    """
    Simulate a proposed change and explain likely consequences.

    The AI is asked to reason ONLY from the provided repository-analysis
    evidence, not to invent new relationships.
    """
    affected_names = [
        all_components_map[cid].path
        for cid in impact.affected_components[:10]
        if cid in all_components_map
    ]
    test_names = [
        all_components_map[cid].path
        for cid in impact.related_tests[:8]
        if cid in all_components_map
    ]

    ai_available = False
    consequence_summary = ""

    if settings.watsonx_configured and settings.watsonx_model_configured:
        ctx = _build_impact_context(component, impact, all_components_map)

        prompt = (
            "A developer is planning the following change to a software codebase.\n\n"
            f"File: {component.path}\n"
            f"Proposed change: {change_description}\n\n"
            "Repository analysis context (deterministic static analysis):\n"
            f"{ctx}\n\n"
            "Based ONLY on the evidence above, describe the likely consequences. "
            "Structure your answer with these headings:\n"
            "CURRENT_IMPACT: [current deterministic risk]\n"
            "POTENTIAL_AFFECTED_COMPONENTS:\n- [component]\n"
            "RISK_FACTORS:\n- [factor]\n"
            "RECOMMENDED_TESTS:\n- [test]\n"
            "LIKELY_CONSEQUENCES: [2-4 sentences]\n"
            "Do NOT claim certainty for impacts not supported by the evidence.\n"
            "---END---"
        )

        ai_text, failure_reason = _call_watsonx(prompt, max_tokens=500)

        if ai_text:
            consequence_summary = ai_text.replace("---END---", "").strip()
            ai_available = True
        else:
            logger.info(
                "watsonx.ai unavailable for simulation, using fallback: %s", failure_reason
            )

    if not ai_available:
        consequence_summary = (
            f"Changing {component.name} could affect {len(impact.affected_components)} "
            f"component(s) based on static analysis. "
            "IBM watsonx.ai is unavailable. Showing rule-based analysis. "
            f"Ensure all {len(impact.related_tests)} related test(s) pass after the change."
        )

    return SimulationResult(
        component_id=component.id,
        change_description=change_description,
        affected_components=affected_names,
        risk_level=impact.risk_level,
        risk_factors=[rf.description for rf in impact.risk_factors],
        recommended_tests=test_names,
        ai_consequence_summary=consequence_summary,
        ai_available=ai_available,
    )
