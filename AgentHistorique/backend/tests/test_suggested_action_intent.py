from __future__ import annotations

from app.rag.prompts import build_retrieval_query, is_attribute_follow_up
from app.rag.suggested_action_intent import get_suggested_action_intent


def test_get_suggested_action_intent_detects_arabic_circuit_action() -> None:
    assert get_suggested_action_intent("عرض تفاصيل المسار") == "circuit_detail"


def test_build_retrieval_query_for_circuit_action_uses_carthage_context() -> None:
    query = build_retrieval_query(
        "عرض تفاصيل المسار",
        {
            "last_mentioned_monuments": ["Parc des thermes d'Antonin"],
            "primary_site_name": "Parc des thermes d'Antonin",
        },
    )
    assert "circuit" in query.lower()
    assert "carthage" in query.lower()
    assert "thermes" in query.lower() or "antonin" in query.lower()


def test_is_attribute_follow_up_detects_show_hours_action() -> None:
    assert is_attribute_follow_up("Show opening hours")
