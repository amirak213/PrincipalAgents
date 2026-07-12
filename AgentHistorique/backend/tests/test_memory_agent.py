from __future__ import annotations

from unittest.mock import MagicMock

from app.agents.memory_agent import MemoryAgent
from app.models.memory import UserSession


def test_memory_agent_record_turn_delegates_to_service() -> None:
    session = UserSession(id=1, session_id="test_session", preferred_language="fr")
    memory_service = MagicMock()
    memory_service.get_or_create_session.return_value = session
    memory_service.update_memory.return_value = {
        "preferred_language": "fr",
        "interests": ["romain"],
        "available_time_minutes": 90,
        "last_mentioned_monuments": ["Theatre"],
        "primary_site_id": None,
        "primary_site_name": None,
    }

    agent = MemoryAgent(MagicMock(), memory_service=memory_service)
    context = agent.record_turn(
        "test_session",
        user_message="Je suis intéressé par l'époque romaine.",
        assistant_answer="Voici des monuments romains.",
        request_language="fr",
        memory_updates={"last_mentioned_monuments": ["Theatre"]},
    )

    memory_service.store_message.assert_any_call(session, role="user", content="Je suis intéressé par l'époque romaine.")
    memory_service.store_message.assert_any_call(session, role="assistant", content="Voici des monuments romains.")
    assert context["interests"] == ["romain"]
    assert context["available_time_minutes"] == 90


def test_memory_agent_get_context_requires_existing_session() -> None:
    memory_service = MagicMock()
    memory_service.get_session_by_external_id.return_value = None
    agent = MemoryAgent(MagicMock(), memory_service=memory_service)

    try:
        agent.get_context("missing_session")
    except ValueError as exc:
        assert "Session not found" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing session")
