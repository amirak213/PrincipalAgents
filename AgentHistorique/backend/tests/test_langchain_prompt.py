from __future__ import annotations

from app.rag.langchain_prompt import format_rag_messages
from app.rag.prompts import build_rag_messages


def test_format_rag_messages_includes_all_sections() -> None:
    messages = format_rag_messages(
        answer_language="fr",
        memory_context='{"last_mentioned_monuments": ["Thermes d\'Antonin"]}',
        retrieved_context="[Source 1] monument — Thermes d'Antonin (score: 0.90)\nChunk text",
        web_search_context="Aucun résultat web.",
        user_question="Et quels sont les horaires ?",
        output_guidelines="- Réponds d'abord à partir de la base documentaire locale.",
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    user_content = messages[1]["content"]
    assert "Langue de réponse demandée: fr" in user_content
    assert "Sources locales:" in user_content
    assert "Résultats web:" in user_content
    assert "Contexte de session:" in user_content
    assert "Question du visiteur:" in user_content
    assert "Règles de réponse:" in user_content
    assert "Thermes d'Antonin" in user_content
    assert "Chunk text" in user_content
    assert "Et quels sont les horaires ?" in user_content
    assert "base documentaire locale" in user_content


def test_build_rag_messages_delegates_memory_and_context() -> None:
    memory_context = {
        "preferred_language": "fr",
        "interests": ["romain"],
        "last_mentioned_monuments": ["Thermes d'Antonin"],
        "primary_site_id": 3,
        "primary_site_name": "Parc des thermes d'Antonin",
    }
    retrieved_chunks = [
        {
            "title": "Thermes d'Antonin",
            "source_type": "monument",
            "score": 0.91,
            "chunk_text": "Horaires été: 08H00 - 18H00",
            "metadata": {"site_id": 3},
        }
    ]

    messages = build_rag_messages(
        user_message="Et quels sont les horaires ?",
        memory_context=memory_context,
        retrieved_chunks=retrieved_chunks,
        language="fr",
    )

    user_content = messages[1]["content"]
    assert '"primary_site_id": 3' in user_content
    assert "Horaires été: 08H00 - 18H00" in user_content
    assert "Et quels sont les horaires ?" in user_content
    assert "Thermes d'Antonin" in user_content


def test_build_rag_messages_omits_practical_info_rules_for_history_question() -> None:
    messages = build_rag_messages(
        user_message="Explique-moi les Thermes d'Antonin",
        memory_context={"preferred_language": "fr"},
        retrieved_chunks=[
            {
                "title": "Thermes d'Antonin",
                "source_type": "monument",
                "score": 0.91,
                "chunk_text": "Complexe thermal romain.",
                "metadata": {},
            }
        ],
        language="fr",
    )

    guidelines = messages[1]["content"].split("Règles de réponse:", 1)[1]
    assert "Ne mentionne pas les horaires ni les tarifs" in guidelines
    assert "Ne mentionne pas les circuits touristiques" in guidelines
