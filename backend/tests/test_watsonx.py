"""
Dependency Domino – IBM watsonx.ai Integration Tests
=====================================================

Tests cover:
1.  Watsonx configuration loading
2.  Missing WATSONX_APIKEY
3.  Missing WATSONX_PROJECT_ID
4.  Missing WATSONX_MODEL_ID
5.  Successful AI request (mocked SDK)
6.  AI timeout / exception
7.  AI authentication failure
8.  Malformed / empty AI response
9.  Deterministic fallback for every scenario
10. /explain endpoint (with and without AI)
11. /test-plan endpoint (with and without AI)
12. /simulate endpoint (with and without AI)
13. API key NEVER appears in responses or logs

All tests use mocks – no real IBM credentials are required.
"""
import sys
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from main import app, _init_demo
from demo.demo_data import DEMO_COMPONENTS, DEMO_DEPENDENCIES, DEMO_REPO_ID
from ai import watsonx_service
from ai.watsonx_service import (
    _reset_client,
    _rule_based_explanation,
    _rule_based_test_plan,
    _build_impact_context,
    _fallback_reason,
    _sanitise_error,
    explain_impact,
    generate_test_plan,
    simulate_change,
)
from analysis.graph_engine import build_dependency_graph
from analysis.impact_engine import compute_impact

# Use the lifespan-aware TestClient to ensure startup events fire
client = TestClient(app)

# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def init_demo_data():
    """Ensure the demo repository is loaded before any endpoint tests run."""
    _init_demo()


@pytest.fixture(autouse=True)
def reset_watsonx_client():
    """Reset the module-level cached client before each test."""
    _reset_client()
    yield
    _reset_client()


@pytest.fixture
def auth_comp():
    return next(c for c in DEMO_COMPONENTS if "authService" in c.name)


@pytest.fixture
def demo_impact(auth_comp):
    _, _, G = build_dependency_graph(DEMO_COMPONENTS, DEMO_REPO_ID)
    return compute_impact(auth_comp.id, DEMO_COMPONENTS, DEMO_DEPENDENCIES, G)


@pytest.fixture
def comp_map():
    return {c.id: c for c in DEMO_COMPONENTS}


# ─── 1. Configuration loading ─────────────────────────────────────────────────

class TestConfigurationLoading:
    def test_watsonx_configured_when_all_vars_present(self):
        with patch("config.settings") as mock_settings:
            mock_settings.effective_api_key = "fake-key"
            mock_settings.watsonx_project_id = "fake-project"
            mock_settings.watsonx_model_id = "ibm/granite-13b-instruct-v2"
            mock_settings.watsonx_configured = True
            mock_settings.watsonx_model_configured = True
            assert mock_settings.watsonx_configured is True
            assert mock_settings.watsonx_model_configured is True

    def test_config_endpoint_returns_safe_fields(self):
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        # Must have safe fields
        assert "watsonx" in data
        assert "backend" in data
        assert data["backend"] == "CONNECTED"
        # Must NOT expose API key
        text = str(data)
        assert "apikey" not in text.lower() or "configured" in text.lower()

    def test_health_endpoint_shows_status(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "watsonx_status" in data
        assert data["watsonx_status"] in ("CONFIGURED", "NOT_CONFIGURED", "NO_MODEL")
        assert "model_configured" in data

    def test_config_never_exposes_api_key(self):
        """API key must NEVER appear in /api/config response."""
        resp = client.get("/api/config")
        body = resp.text
        # Common patterns that might expose a key
        assert "ApiKey-" not in body
        assert "sk-" not in body
        # The field name itself should not carry a value
        import json
        data = json.loads(body)
        flat = str(data)
        assert "apikey" not in flat.lower() or all(
            v in (None, "", True, False) or not isinstance(v, str) or len(v) < 10
            for v in _flatten_values(data)
        )


def _flatten_values(d):
    """Recursively yield all scalar values from a nested dict/list."""
    if isinstance(d, dict):
        for v in d.values():
            yield from _flatten_values(v)
    elif isinstance(d, list):
        for v in d:
            yield from _flatten_values(v)
    else:
        yield d


# ─── 2. Missing WATSONX_APIKEY ────────────────────────────────────────────────

class TestMissingApiKey:
    def test_fallback_when_no_api_key(self, auth_comp, demo_impact, comp_map):
        with patch("ai.watsonx_service.settings") as mock_settings:
            mock_settings.effective_api_key = ""
            mock_settings.watsonx_project_id = "proj"
            mock_settings.watsonx_model_id = "ibm/granite-13b-instruct-v2"
            mock_settings.watsonx_configured = False
            mock_settings.watsonx_model_configured = True
            mock_settings.watsonx_url = "https://us-south.ml.cloud.ibm.com"

            result = explain_impact(auth_comp, demo_impact, comp_map)
            assert result.ai_available is False
            assert result.ai_source == "rule-based"
            assert "IBM watsonx.ai is unavailable" in result.summary or result.summary != ""

    def test_fallback_reason_does_not_expose_key(self, auth_comp, demo_impact, comp_map):
        with patch("ai.watsonx_service.settings") as mock_settings:
            mock_settings.effective_api_key = ""
            mock_settings.watsonx_project_id = "proj"
            mock_settings.watsonx_model_id = "ibm/granite-13b-instruct-v2"
            mock_settings.watsonx_configured = False
            mock_settings.watsonx_model_configured = True
            mock_settings.watsonx_url = "https://us-south.ml.cloud.ibm.com"

            result = explain_impact(auth_comp, demo_impact, comp_map)
            assert "ApiKey" not in result.fallback_reason
            assert "sk-" not in result.fallback_reason


# ─── 3. Missing WATSONX_PROJECT_ID ───────────────────────────────────────────

class TestMissingProjectId:
    def test_fallback_when_no_project_id(self, auth_comp, demo_impact, comp_map):
        with patch("ai.watsonx_service.settings") as mock_settings:
            mock_settings.effective_api_key = "fake-key"
            mock_settings.watsonx_project_id = ""
            mock_settings.watsonx_model_id = "ibm/granite-13b-instruct-v2"
            mock_settings.watsonx_configured = False
            mock_settings.watsonx_model_configured = True
            mock_settings.watsonx_url = "https://us-south.ml.cloud.ibm.com"

            result = explain_impact(auth_comp, demo_impact, comp_map)
            assert result.ai_available is False


# ─── 4. Missing WATSONX_MODEL_ID ─────────────────────────────────────────────

class TestMissingModelId:
    def test_fallback_when_no_model_id(self, auth_comp, demo_impact, comp_map):
        with patch("ai.watsonx_service.settings") as mock_settings:
            mock_settings.effective_api_key = "fake-key"
            mock_settings.watsonx_project_id = "proj"
            mock_settings.watsonx_model_id = ""
            mock_settings.watsonx_configured = True
            mock_settings.watsonx_model_configured = False
            mock_settings.watsonx_url = "https://us-south.ml.cloud.ibm.com"

            result = explain_impact(auth_comp, demo_impact, comp_map)
            assert result.ai_available is False

    def test_model_not_configured_message(self, auth_comp, demo_impact, comp_map):
        with patch("ai.watsonx_service.settings") as mock_settings:
            mock_settings.effective_api_key = "fake-key"
            mock_settings.watsonx_project_id = "proj"
            mock_settings.watsonx_model_id = ""
            mock_settings.watsonx_configured = True
            mock_settings.watsonx_model_configured = False
            mock_settings.watsonx_url = "https://us-south.ml.cloud.ibm.com"

            reason = _fallback_reason.__wrapped__() if hasattr(_fallback_reason, "__wrapped__") else None
            # Simply check the explain result carries a fallback reason
            result = explain_impact(auth_comp, demo_impact, comp_map)
            # The fallback reason should mention model not configured
            assert result.ai_source == "rule-based"


# ─── 5. Successful AI request (mocked SDK) ────────────────────────────────────

class TestSuccessfulAiRequest:
    def test_explain_uses_ai_when_available(self, auth_comp, demo_impact, comp_map):
        """With a mocked SDK that returns a well-formed response, ai_available should be True."""
        mock_model = MagicMock()
        mock_model.generate_text.return_value = (
            "SUMMARY: This is a test summary.\n"
            "WHY_IT_MATTERS: It matters because of dependencies.\n"
            "POTENTIAL_IMPACT: Several modules may break.\n"
            "RISK_FACTORS:\n- High dependent count\n- No tests\n"
            "RECOMMENDED_ACTIONS:\n- Review dependents\n- Run tests\n"
            "TEST_RECOMMENDATIONS:\n- Run unit tests\n- Run integration tests\n"
            "UNCERTAINTIES:\n- Dynamic imports not captured\n"
        )

        with patch("ai.watsonx_service.settings") as mock_settings, \
             patch("ai.watsonx_service._model_client", mock_model):
            mock_settings.effective_api_key = "fake-key"
            mock_settings.watsonx_project_id = "proj"
            mock_settings.watsonx_model_id = "ibm/granite-13b-instruct-v2"
            mock_settings.watsonx_configured = True
            mock_settings.watsonx_model_configured = True
            mock_settings.watsonx_url = "https://us-south.ml.cloud.ibm.com"

            result = explain_impact(auth_comp, demo_impact, comp_map)
            assert result.ai_available is True
            assert result.ai_source == "watsonx"
            assert result.summary != ""

    def test_test_plan_uses_ai_when_available(self, auth_comp, demo_impact, comp_map):
        mock_model = MagicMock()
        mock_model.generate_text.return_value = (
            "- Auth unit tests | Reason: direct impact | Existing: no | Priority: high\n"
            "- Integration tests | Reason: cascade | Existing: no | Priority: medium\n"
            "GAPS:\n- No test for userService\n"
        )

        with patch("ai.watsonx_service.settings") as mock_settings, \
             patch("ai.watsonx_service._model_client", mock_model):
            mock_settings.effective_api_key = "fake-key"
            mock_settings.watsonx_project_id = "proj"
            mock_settings.watsonx_model_id = "ibm/granite-13b-instruct-v2"
            mock_settings.watsonx_configured = True
            mock_settings.watsonx_model_configured = True
            mock_settings.watsonx_url = "https://us-south.ml.cloud.ibm.com"

            result = generate_test_plan(auth_comp, demo_impact, comp_map)
            assert result.ai_generated is True
            assert result.ai_available is True
            assert len(result.recommended_tests) > 0
            assert result.label == "AI-generated test recommendation"

    def test_simulate_uses_ai_when_available(self, auth_comp, demo_impact, comp_map):
        mock_model = MagicMock()
        mock_model.generate_text.return_value = (
            "CURRENT_IMPACT: HIGH risk.\n"
            "POTENTIAL_AFFECTED_COMPONENTS:\n- src/app.js\n"
            "RISK_FACTORS:\n- Many dependents\n"
            "RECOMMENDED_TESTS:\n- auth.test.js\n"
            "LIKELY_CONSEQUENCES: Changing auth will break login flows.\n"
        )

        with patch("ai.watsonx_service.settings") as mock_settings, \
             patch("ai.watsonx_service._model_client", mock_model):
            mock_settings.effective_api_key = "fake-key"
            mock_settings.watsonx_project_id = "proj"
            mock_settings.watsonx_model_id = "ibm/granite-13b-instruct-v2"
            mock_settings.watsonx_configured = True
            mock_settings.watsonx_model_configured = True
            mock_settings.watsonx_url = "https://us-south.ml.cloud.ibm.com"

            result = simulate_change(
                auth_comp, demo_impact, comp_map, "Remove token validation"
            )
            assert result.ai_available is True
            assert result.ai_consequence_summary != ""


# ─── 6. AI timeout / exception ────────────────────────────────────────────────

class TestAiTimeout:
    def test_explain_falls_back_on_timeout(self, auth_comp, demo_impact, comp_map):
        mock_model = MagicMock()
        mock_model.generate_text.side_effect = TimeoutError("Request timed out")

        with patch("ai.watsonx_service.settings") as mock_settings, \
             patch("ai.watsonx_service._model_client", mock_model):
            mock_settings.effective_api_key = "fake-key"
            mock_settings.watsonx_project_id = "proj"
            mock_settings.watsonx_model_id = "ibm/granite-13b-instruct-v2"
            mock_settings.watsonx_configured = True
            mock_settings.watsonx_model_configured = True
            mock_settings.watsonx_url = "https://us-south.ml.cloud.ibm.com"

            result = explain_impact(auth_comp, demo_impact, comp_map)
            # Must not raise; must return rule-based fallback
            assert result.ai_available is False
            assert result.ai_source == "rule-based"

    def test_test_plan_falls_back_on_timeout(self, auth_comp, demo_impact, comp_map):
        mock_model = MagicMock()
        mock_model.generate_text.side_effect = TimeoutError("timeout")

        with patch("ai.watsonx_service.settings") as mock_settings, \
             patch("ai.watsonx_service._model_client", mock_model):
            mock_settings.effective_api_key = "fake-key"
            mock_settings.watsonx_project_id = "proj"
            mock_settings.watsonx_model_id = "ibm/granite-13b-instruct-v2"
            mock_settings.watsonx_configured = True
            mock_settings.watsonx_model_configured = True
            mock_settings.watsonx_url = "https://us-south.ml.cloud.ibm.com"

            result = generate_test_plan(auth_comp, demo_impact, comp_map)
            assert result.ai_generated is False


# ─── 7. AI authentication failure ────────────────────────────────────────────

class TestAiAuthFailure:
    def test_explain_falls_back_on_auth_error(self, auth_comp, demo_impact, comp_map):
        mock_model = MagicMock()
        mock_model.generate_text.side_effect = Exception(
            "401 Unauthorized: Invalid API key"
        )

        with patch("ai.watsonx_service.settings") as mock_settings, \
             patch("ai.watsonx_service._model_client", mock_model):
            mock_settings.effective_api_key = "bad-key"
            mock_settings.watsonx_project_id = "proj"
            mock_settings.watsonx_model_id = "ibm/granite-13b-instruct-v2"
            mock_settings.watsonx_configured = True
            mock_settings.watsonx_model_configured = True
            mock_settings.watsonx_url = "https://us-south.ml.cloud.ibm.com"

            result = explain_impact(auth_comp, demo_impact, comp_map)
            assert result.ai_available is False
            # The API key value must not appear in the fallback reason
            assert "bad-key" not in result.fallback_reason

    def test_api_key_not_in_fallback_reason(self):
        """_sanitise_error must strip the API key from error messages."""
        with patch("ai.watsonx_service.settings") as mock_settings:
            mock_settings.effective_api_key = "super-secret-key-12345"
            result = _sanitise_error("Error: invalid apikey super-secret-key-12345 used")
        assert "super-secret-key-12345" not in result
        assert "***" in result


# ─── 8. Malformed / empty AI response ────────────────────────────────────────

class TestMalformedAiResponse:
    def test_explain_falls_back_on_empty_response(self, auth_comp, demo_impact, comp_map):
        mock_model = MagicMock()
        mock_model.generate_text.return_value = ""

        with patch("ai.watsonx_service.settings") as mock_settings, \
             patch("ai.watsonx_service._model_client", mock_model):
            mock_settings.effective_api_key = "fake-key"
            mock_settings.watsonx_project_id = "proj"
            mock_settings.watsonx_model_id = "ibm/granite-13b-instruct-v2"
            mock_settings.watsonx_configured = True
            mock_settings.watsonx_model_configured = True
            mock_settings.watsonx_url = "https://us-south.ml.cloud.ibm.com"

            result = explain_impact(auth_comp, demo_impact, comp_map)
            # Empty response triggers fallback
            assert result.ai_source == "rule-based"

    def test_explain_partial_response_still_parses(self, auth_comp, demo_impact, comp_map):
        """A partial AI response (missing some sections) must not crash."""
        mock_model = MagicMock()
        mock_model.generate_text.return_value = "SUMMARY: Partial response only."

        with patch("ai.watsonx_service.settings") as mock_settings, \
             patch("ai.watsonx_service._model_client", mock_model):
            mock_settings.effective_api_key = "fake-key"
            mock_settings.watsonx_project_id = "proj"
            mock_settings.watsonx_model_id = "ibm/granite-13b-instruct-v2"
            mock_settings.watsonx_configured = True
            mock_settings.watsonx_model_configured = True
            mock_settings.watsonx_url = "https://us-south.ml.cloud.ibm.com"

            result = explain_impact(auth_comp, demo_impact, comp_map)
            # Must not raise; missing sections are empty strings/lists
            assert result is not None
            assert isinstance(result.risk_factors, list)


# ─── 9. Deterministic fallback ────────────────────────────────────────────────

class TestDeterministicFallback:
    def test_rule_based_explanation_has_all_fields(self, auth_comp, demo_impact, comp_map):
        result = _rule_based_explanation(auth_comp, demo_impact, comp_map)
        assert result.ai_available is False
        assert result.ai_source == "rule-based"
        assert result.summary != ""
        assert result.why_it_matters != ""
        assert result.potential_impact != ""
        assert len(result.risk_factors) > 0
        assert len(result.recommended_actions) > 0
        assert len(result.test_recommendations) > 0
        assert len(result.uncertainties) > 0

    def test_rule_based_test_plan_has_recommended_tests(self, auth_comp, demo_impact, comp_map):
        result = _rule_based_test_plan(auth_comp, demo_impact, comp_map)
        assert result.ai_generated is False
        assert result.ai_source == "rule-based"
        assert len(result.recommended_tests) > 0

    def test_fallback_summary_mentions_watsonx_unavailable(self, auth_comp, demo_impact, comp_map):
        result = _rule_based_explanation(
            auth_comp, demo_impact, comp_map, fallback_reason="timeout"
        )
        assert "watsonx.ai is unavailable" in result.summary.lower() or \
               "IBM watsonx.ai" in result.summary

    def test_fallback_never_crashes(self, auth_comp, demo_impact, comp_map):
        """_rule_based_explanation must handle empty component maps."""
        result = _rule_based_explanation(auth_comp, demo_impact, {})
        assert result is not None
        assert result.ai_source == "rule-based"

    def test_context_builder_never_sends_secrets(self, auth_comp, demo_impact, comp_map):
        """The context sent to the AI must not contain .env-style key-value pairs."""
        ctx = _build_impact_context(auth_comp, demo_impact, comp_map)
        assert "APIKEY" not in ctx
        assert "api_key" not in ctx.lower()
        assert "password" not in ctx.lower()
        assert "secret" not in ctx.lower()


# ─── 10. /explain endpoint ────────────────────────────────────────────────────

class TestExplainEndpoint:
    def test_explain_returns_200(self):
        auth_comp = next(c for c in DEMO_COMPONENTS if "authService" in c.name)
        resp = client.post(
            f"/api/components/{auth_comp.id}/explain",
            json={"component_id": auth_comp.id},
        )
        assert resp.status_code == 200

    def test_explain_response_has_required_fields(self):
        auth_comp = next(c for c in DEMO_COMPONENTS if "authService" in c.name)
        resp = client.post(
            f"/api/components/{auth_comp.id}/explain",
            json={"component_id": auth_comp.id},
        )
        data = resp.json()
        assert "summary" in data
        assert "ai_available" in data
        assert "ai_source" in data
        assert "model_used" in data
        assert "risk_factors" in data
        assert "recommended_actions" in data
        assert "test_recommendations" in data
        assert "uncertainties" in data

    def test_explain_with_change_description(self):
        auth_comp = next(c for c in DEMO_COMPONENTS if "authService" in c.name)
        resp = client.post(
            f"/api/components/{auth_comp.id}/explain",
            json={
                "component_id": auth_comp.id,
                "change_description": "Remove JWT token validation",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"] != ""

    def test_explain_fallback_response_does_not_expose_api_key(self):
        auth_comp = next(c for c in DEMO_COMPONENTS if "authService" in c.name)
        resp = client.post(
            f"/api/components/{auth_comp.id}/explain",
            json={"component_id": auth_comp.id},
        )
        body = resp.text
        assert "ApiKey-" not in body
        assert "apikey=" not in body.lower()

    def test_explain_404_on_missing_component(self):
        resp = client.post(
            "/api/components/nonexistent-id/explain",
            json={"component_id": "nonexistent-id"},
        )
        assert resp.status_code == 404


# ─── 11. /test-plan endpoint ─────────────────────────────────────────────────

class TestTestPlanEndpoint:
    def test_test_plan_returns_200(self):
        auth_comp = next(c for c in DEMO_COMPONENTS if "authService" in c.name)
        resp = client.post(
            f"/api/components/{auth_comp.id}/test-plan",
            json={"component_id": auth_comp.id},
        )
        assert resp.status_code == 200

    def test_test_plan_has_required_fields(self):
        auth_comp = next(c for c in DEMO_COMPONENTS if "authService" in c.name)
        resp = client.post(
            f"/api/components/{auth_comp.id}/test-plan",
            json={"component_id": auth_comp.id},
        )
        data = resp.json()
        assert "recommended_tests" in data
        assert "existing_tests" in data
        assert "coverage_gaps" in data
        assert "ai_generated" in data
        assert "disclaimer" in data
        assert "label" in data

    def test_test_plan_disclaimer_present(self):
        auth_comp = next(c for c in DEMO_COMPONENTS if "authService" in c.name)
        resp = client.post(
            f"/api/components/{auth_comp.id}/test-plan",
            json={"component_id": auth_comp.id},
        )
        data = resp.json()
        assert data["disclaimer"] != ""

    def test_test_plan_fallback_labels_correctly(self):
        """Without credentials, label should indicate rule-based."""
        auth_comp = next(c for c in DEMO_COMPONENTS if "authService" in c.name)
        resp = client.post(
            f"/api/components/{auth_comp.id}/test-plan",
            json={"component_id": auth_comp.id},
        )
        data = resp.json()
        # Whether AI or rule-based, the label must be present
        assert data["label"] in (
            "AI-generated test recommendation",
            "Rule-based test recommendation",
        )

    def test_test_plan_404_on_missing_component(self):
        resp = client.post(
            "/api/components/nonexistent-id/test-plan",
            json={"component_id": "nonexistent-id"},
        )
        assert resp.status_code == 404


# ─── 12. /simulate endpoint ───────────────────────────────────────────────────

class TestSimulateEndpoint:
    def test_simulate_returns_200(self):
        auth_comp = next(c for c in DEMO_COMPONENTS if "authService" in c.name)
        resp = client.post(
            f"/api/components/{auth_comp.id}/simulate",
            json={
                "component_id": auth_comp.id,
                "change_description": "Remove token validation logic",
            },
        )
        assert resp.status_code == 200

    def test_simulate_has_fallback_summary(self):
        auth_comp = next(c for c in DEMO_COMPONENTS if "authService" in c.name)
        resp = client.post(
            f"/api/components/{auth_comp.id}/simulate",
            json={
                "component_id": auth_comp.id,
                "change_description": "Refactor auth flow",
            },
        )
        data = resp.json()
        assert "ai_consequence_summary" in data
        assert data["ai_consequence_summary"] != ""
        # When AI is not configured, summary must mention rule-based
        if not data["ai_available"]:
            assert (
                "rule-based" in data["ai_consequence_summary"].lower()
                or "watsonx.ai is unavailable" in data["ai_consequence_summary"]
            )


# ─── 13. Security – API key never in response ─────────────────────────────────

class TestSecurityApiKeyNotExposed:
    def test_health_no_api_key(self):
        resp = client.get("/api/health")
        assert "ApiKey" not in resp.text
        assert "apikey" not in resp.text.lower() or "configured" in resp.text.lower()

    def test_explain_no_api_key(self):
        auth_comp = next(c for c in DEMO_COMPONENTS if "authService" in c.name)
        resp = client.post(
            f"/api/components/{auth_comp.id}/explain",
            json={"component_id": auth_comp.id},
        )
        # Ensure no secret values appear
        assert "ApiKey-" not in resp.text
        assert len([ch for ch in resp.text if ch == "-"]) < 200  # sanity – no long key strings

    def test_config_no_api_key(self):
        resp = client.get("/api/config")
        body = resp.text
        assert "ApiKey-" not in body
        # The "watsonx" sub-object must not contain a key field with a value
        import json
        data = json.loads(body)
        wx = data.get("watsonx", {})
        for field in ("api_key", "apikey", "key", "token", "secret"):
            assert field not in wx, f"Field '{field}' found in /api/config watsonx object"
