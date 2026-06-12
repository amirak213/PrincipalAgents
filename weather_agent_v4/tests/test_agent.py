"""
Tests unitaires — WeatherAgent v4
Chaque module testé indépendamment (pas de mocks LLM nécessaires pour les tests déterministes).
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from dataclasses import dataclass


# ──────────────────────────────────────────────────────────────
# TESTS : PLANNER (fallback déterministe — zéro LLM)
# ──────────────────────────────────────────────────────────────

class TestPlannerFallback(unittest.TestCase):
    """Le fallback déterministe doit fonctionner sans aucun LLM."""

    def setUp(self):
        from core.planner import AgentPlanner
        mock_factory = MagicMock(side_effect=RuntimeError("LLM indisponible"))
        self.planner = AgentPlanner(llm_client_factory=mock_factory)
        self.ctx = {"last_city": "Tunis", "recent_turns": []}

    def test_forecast_demain(self):
        plan = self.planner.plan("météo demain à Sfax", self.ctx, [], "")
        self.assertEqual(plan.intent, "prévision")
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].tool_name, "get_forecast")
        self.assertEqual(plan.steps[0].tool_args.get("target_day"), "demain")

    def test_forecast_weekend(self):
        plan = self.planner.plan("qu'est-ce que ça donne ce week-end", self.ctx, [], "")
        self.assertEqual(plan.steps[0].tool_name, "get_forecast")

    def test_comparison(self):
        plan = self.planner.plan("compare tunis et sfax", self.ctx, [], "")
        self.assertEqual(plan.intent, "comparaison")
        self.assertEqual(plan.steps[0].tool_name, "compare_cities")

    def test_meteo_actuelle_default(self):
        plan = self.planner.plan("il fait quel temps ?", self.ctx, [], "")
        self.assertEqual(plan.steps[0].tool_name, "get_weather")

    def test_uses_last_city_from_context(self):
        ctx = {"last_city": "Djerba", "recent_turns": []}
        plan = self.planner.plan("et demain ?", ctx, [], "")
        self.assertEqual(plan.steps[0].tool_args.get("city_name"), "Djerba")

    def test_no_crash_on_empty_query(self):
        plan = self.planner.plan("", self.ctx, [], "")
        self.assertIsNotNone(plan)


# ──────────────────────────────────────────────────────────────
# TESTS : EVALUATOR (fallback déterministe)
# ──────────────────────────────────────────────────────────────

class TestEvaluatorFallback(unittest.TestCase):

    def setUp(self):
        from core.evaluator import ResponseEvaluator
        from core.planner import ExecutionPlan, PlanStep
        mock_factory = MagicMock(side_effect=RuntimeError("LLM indisponible"))
        self.evaluator = ResponseEvaluator(llm_client_factory=mock_factory)
        self.plan = ExecutionPlan(
            intent="météo_actuelle", steps=[], city="Tunis",
            time_horizon="now", language="fr", confidence=0.9,
        )

    def test_empty_results_not_sufficient(self):
        result = self.evaluator.evaluate("météo Tunis", [], self.plan)
        self.assertFalse(result.is_sufficient)
        self.assertEqual(result.score, 0.0)

    def test_valid_results_sufficient(self):
        tool_results = [{"tool_name": "get_weather", "result": {"temperature_c": 25}}]
        result = self.evaluator.evaluate("météo Tunis", tool_results, self.plan)
        self.assertTrue(result.is_sufficient)
        self.assertGreaterEqual(result.score, 0.7)

    def test_all_errors_not_sufficient(self):
        tool_results = [{"tool_name": "get_weather", "result": {"error": "timeout"}}]
        result = self.evaluator.evaluate("météo Tunis", tool_results, self.plan)
        self.assertFalse(result.is_sufficient)


# ──────────────────────────────────────────────────────────────
# TESTS : TOOL EXECUTOR — validation des args
# ──────────────────────────────────────────────────────────────

class TestToolExecutorArgValidation(unittest.TestCase):

    def test_validate_args_integer_cast(self):
        from tools.executor import _validate_args
        schema = {
            "properties": {"days": {"type": "integer", "default": 3}},
            "required": [],
        }
        result = _validate_args({"days": "5"}, schema)
        self.assertEqual(result["days"], 5)

    def test_validate_args_null_string_to_none(self):
        from tools.executor import _validate_args
        schema = {
            "properties": {"target_day": {"type": "string"}},
            "required": [],
        }
        result = _validate_args({"target_day": "null"}, schema)
        self.assertIsNone(result["target_day"])

    def test_validate_args_missing_required_raises(self):
        from tools.executor import _validate_args
        schema = {
            "properties": {"city_name": {"type": "string"}},
            "required": ["city_name"],
        }
        with self.assertRaises(ValueError):
            _validate_args({}, schema)

    def test_validate_args_uses_default(self):
        from tools.executor import _validate_args
        schema = {
            "properties": {"days": {"type": "integer", "default": 3}},
            "required": [],
        }
        result = _validate_args({}, schema)
        self.assertEqual(result["days"], 3)


# ──────────────────────────────────────────────────────────────
# TESTS : CONTEXT MANAGER
# ──────────────────────────────────────────────────────────────

class TestContextManager(unittest.TestCase):

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mktemp(suffix=".json"))
        from memory.context import ContextManager
        self.ctx = ContextManager(self.tmp)

    def tearDown(self):
        if self.tmp.exists():
            self.tmp.unlink()

    def test_session_isolation(self):
        self.ctx.add_user_turn("session_A", "Météo Tunis")
        self.ctx.add_user_turn("session_B", "Météo Djerba")
        ctx_a = self.ctx.build_context("session_A", "")
        ctx_b = self.ctx.build_context("session_B", "")
        turns_a = [t["content"] for t in ctx_a["recent_turns"]]
        turns_b = [t["content"] for t in ctx_b["recent_turns"]]
        self.assertIn("Météo Tunis",  turns_a)
        self.assertNotIn("Météo Djerba", turns_a)
        self.assertIn("Météo Djerba", turns_b)

    def test_last_city_from_metadata(self):
        self.ctx.add_turn("sess1", "user", "Météo Sfax", metadata={"city": "Sfax"})
        ctx = self.ctx.build_context("sess1", "")
        self.assertEqual(ctx["last_city"], "Sfax")

    def test_session_turn_limit(self):
        for i in range(25):
            self.ctx.add_user_turn("sess_limit", f"message {i}")
        ctx = self.ctx.build_context("sess_limit", "")
        self.assertLessEqual(len(ctx["recent_turns"]), 6)

    def test_long_term_persistence(self):
        self.ctx.add_turn("s1", "assistant", "réponse", metadata={"city": "Tozeur"})
        # Recharge depuis fichier
        from memory.context import ContextManager
        ctx2 = ContextManager(self.tmp)
        self.assertIn("Tozeur", ctx2._long_term.favorite_cities)

    def test_reset_session(self):
        self.ctx.add_user_turn("to_reset", "message")
        self.ctx.reset_session("to_reset")
        ctx = self.ctx.build_context("to_reset", "")
        self.assertEqual(ctx["recent_turns"], [])


# ──────────────────────────────────────────────────────────────
# TESTS : TOOL REGISTRY
# ──────────────────────────────────────────────────────────────

class TestToolRegistry(unittest.TestCase):

    def setUp(self):
        from tools.registry import ToolRegistry
        self.reg = ToolRegistry()

    def test_register_and_get(self):
        @self.reg.register(
            name="test_tool",
            description="Un tool de test",
            parameters={"type": "object", "properties": {}, "required": []},
        )
        def my_tool():
            return {"ok": True}

        spec = self.reg.get("test_tool")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.name, "test_tool")
        self.assertEqual(spec.handler(), {"ok": True})

    def test_unknown_tool_returns_none(self):
        self.assertIsNone(self.reg.get("inexistant"))

    def test_openai_format(self):
        @self.reg.register(
            name="weather_tool",
            description="Météo",
            parameters={"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
        )
        def weather(): pass

        fmt = self.reg.to_openai_format()
        self.assertEqual(len(fmt), 1)
        self.assertEqual(fmt[0]["type"], "function")
        self.assertEqual(fmt[0]["function"]["name"], "weather_tool")


# ──────────────────────────────────────────────────────────────
# TESTS : WEATHER TOOLS (unitaires — sans appel réseau)
# ──────────────────────────────────────────────────────────────

class TestAlertComputation(unittest.TestCase):

    def test_rouge_canicule(self):
        from tools.weather_tools import compute_alert
        alert = compute_alert(temp_max=40, rain_pct=10, wind_kmh=10, description="Ciel dégagé")
        self.assertEqual(alert["level"], "ROUGE")
        self.assertFalse(alert["outdoor_ok"])

    def test_rouge_vent(self):
        from tools.weather_tools import compute_alert
        alert = compute_alert(temp_max=25, rain_pct=10, wind_kmh=70, description="Nuageux")
        self.assertEqual(alert["level"], "ROUGE")

    def test_orange_chaleur(self):
        from tools.weather_tools import compute_alert
        alert = compute_alert(temp_max=33, rain_pct=10, wind_kmh=20, description="Ensoleillé")
        self.assertEqual(alert["level"], "ORANGE")
        self.assertTrue(alert["outdoor_ok"])

    def test_vert_normal(self):
        from tools.weather_tools import compute_alert
        alert = compute_alert(temp_max=22, rain_pct=10, wind_kmh=15, description="Nuageux")
        self.assertEqual(alert["level"], "VERT")
        self.assertTrue(alert["outdoor_ok"])

    def test_rouge_pluie(self):
        from tools.weather_tools import compute_alert
        alert = compute_alert(temp_max=20, rain_pct=85, wind_kmh=20, description="Pluie forte")
        self.assertEqual(alert["level"], "ROUGE")


# ──────────────────────────────────────────────────────────────
# TESTS : MODEL ROUTER — circuit breaker
# ──────────────────────────────────────────────────────────────

class TestModelRouter(unittest.TestCase):

    def test_provider_state_circuit_breaker(self):
        from core.model_router import ProviderState
        state = ProviderState(name="test", cooldown_s=1000)
        self.assertTrue(state.is_available())
        state.report_error()
        state.report_error()
        state.report_error()
        self.assertFalse(state.is_available())

    def test_provider_state_recovery_after_cooldown(self):
        import time
        from core.model_router import ProviderState
        state = ProviderState(name="test", cooldown_s=0.01)
        state.report_error()
        state.report_error()
        state.report_error()
        time.sleep(0.02)
        self.assertTrue(state.is_available())


# ──────────────────────────────────────────────────────────────
# TESTS : OBSERVABILITY
# ──────────────────────────────────────────────────────────────

class TestTracer(unittest.TestCase):

    def setUp(self):
        from observability.tracer import AgentTracer
        self.tracer = AgentTracer(log_file=None)

    def test_run_span_increments_metrics(self):
        import contextlib
        with self.tracer.run_span("run1", "sess1", "test query"):
            pass
        metrics = self.tracer.get_metrics_snapshot()
        self.assertEqual(metrics.get("runs.total"), 1)
        self.assertEqual(metrics.get("runs.success"), 1)

    def test_run_span_error_tracked(self):
        try:
            with self.tracer.run_span("run2", "sess2", "test"):
                raise ValueError("test error")
        except ValueError:
            pass
        metrics = self.tracer.get_metrics_snapshot()
        self.assertEqual(metrics.get("runs.error"), 1)

    def test_health_structure(self):
        health = self.tracer.get_health()
        self.assertIn("status",       health)
        self.assertIn("runs_total",   health)
        self.assertIn("success_rate", health)


# ──────────────────────────────────────────────────────────────
# TESTS : PLANNER JSON PARSING
# ──────────────────────────────────────────────────────────────

class TestJsonParsing(unittest.TestCase):

    def test_clean_json(self):
        from core.planner import _safe_json_parse
        raw = '{"intent": "météo_actuelle", "steps": []}'
        result = _safe_json_parse(raw)
        self.assertEqual(result["intent"], "météo_actuelle")

    def test_markdown_wrapped_json(self):
        from core.planner import _safe_json_parse
        raw = "```json\n{\"intent\": \"prévision\"}\n```"
        result = _safe_json_parse(raw)
        self.assertEqual(result["intent"], "prévision")

    def test_invalid_json_returns_empty(self):
        from core.planner import _safe_json_parse
        result = _safe_json_parse("pas du json")
        self.assertEqual(result, {})


# ──────────────────────────────────────────────────────────────
# RUNNER
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    test_classes = [
        TestPlannerFallback,
        TestEvaluatorFallback,
        TestToolExecutorArgValidation,
        TestContextManager,
        TestToolRegistry,
        TestAlertComputation,
        TestModelRouter,
        TestTracer,
        TestJsonParsing,
    ]

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print(f"\n{'='*60}")
    print(f"Tests passés : {result.testsRun - len(result.failures) - len(result.errors)}/{result.testsRun}")
    if result.failures or result.errors:
        print("ÉCHECS :")
        for f in result.failures + result.errors:
            print(f"  - {f[0]}")
    else:
        print("✓ Tous les tests passés")
    print("="*60)