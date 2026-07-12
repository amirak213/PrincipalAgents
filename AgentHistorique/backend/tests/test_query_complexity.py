from __future__ import annotations

from app.rag.query_complexity import is_complex_question, user_requests_detailed_answer


def test_is_complex_question_detects_detail_request() -> None:
    assert is_complex_question("Explique en détail l'histoire punique de Carthage")


def test_is_complex_question_detects_long_message() -> None:
    message = (
        "Je voudrais comprendre comment les Thermes d'Antonin s'intègrent "
        "dans le parc archéologique de Carthage et quels monuments voisins "
        "méritent une visite pendant une demi-journée."
    )
    assert is_complex_question(message)


def test_is_complex_question_false_for_short_simple_question() -> None:
    assert not is_complex_question("Où se trouvent les Thermes d'Antonin ?")


def test_user_requests_detailed_answer_detects_explicit_detail_ask() -> None:
    assert user_requests_detailed_answer("Donne-moi plus de détails sur Byrsa")


def test_user_requests_detailed_answer_false_for_concise_question() -> None:
    assert not user_requests_detailed_answer("Quels sont les horaires ?")
