from __future__ import annotations

from app.rag.answer_parser import parse_llm_answer


def test_parse_llm_answer_plain_text_passthrough() -> None:
    assert parse_llm_answer("Réponse simple.", structured=False) == "Réponse simple."


def test_parse_llm_answer_structured_json() -> None:
    raw = '{"answer": "Horaires: 08H00 - 18H00"}'
    assert parse_llm_answer(raw, structured=True) == "Horaires: 08H00 - 18H00"


def test_parse_llm_answer_structured_fallback_on_invalid_json() -> None:
    raw = "Réponse en texte libre."
    assert parse_llm_answer(raw, structured=True) == "Réponse en texte libre."


def test_parse_llm_answer_structured_json_fence() -> None:
    raw = '```json\n{"answer": "Tarif: 12 TND"}\n```'
    assert parse_llm_answer(raw, structured=True) == "Tarif: 12 TND"


def test_parse_llm_answer_strips_internal_prompt_labels() -> None:
    raw = (
        "Nous pouvons nous baser uniquement sur le LOCAL_KNOWLEDGE_BASE_CONTEXT. "
        "Le port est ouvert."
    )
    assert parse_llm_answer(raw, structured=False) == (
        "Nous pouvons nous baser uniquement sur notre base documentaire. "
        "Le port est ouvert."
    )
