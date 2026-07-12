from __future__ import annotations

from app.rag.practical_info_intent import (
    user_explicitly_requests_circuits,
    user_explicitly_requests_horaires_or_tarifs,
)
from app.rag.prompts import build_output_guidelines


def test_horaires_not_explicit_for_history_question() -> None:
    guidelines = build_output_guidelines(
        user_message="Explique-moi les Thermes d'Antonin",
        memory_context={"preferred_language": "fr"},
        answer_language="fr",
    )
    assert "Ne mentionne pas les horaires ni les tarifs" in guidelines
    assert "Ne mentionne pas les circuits touristiques" in guidelines


def test_horaires_allowed_when_explicit() -> None:
    guidelines = build_output_guidelines(
        user_message="Quels sont les horaires des Thermes d'Antonin ?",
        memory_context={"preferred_language": "fr"},
        answer_language="fr",
    )
    assert "Ne mentionne pas les horaires ni les tarifs" not in guidelines


def test_circuits_allowed_when_explicit() -> None:
    guidelines = build_output_guidelines(
        user_message="Propose un circuit romain à Carthage",
        memory_context={"preferred_language": "fr"},
        answer_language="fr",
    )
    assert "Ne mentionne pas les circuits touristiques" not in guidelines


def test_user_explicitly_requests_horaires_on_follow_up() -> None:
    assert user_explicitly_requests_horaires_or_tarifs("Et les horaires ?")
    assert not user_explicitly_requests_horaires_or_tarifs("Parle-moi du Tophet")


def test_user_explicitly_requests_circuits_with_duration() -> None:
    assert user_explicitly_requests_circuits("J'ai 1h30, que puis-je visiter ?")
    assert not user_explicitly_requests_circuits("Quelle est l'histoire du Tophet ?")
