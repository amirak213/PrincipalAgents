from __future__ import annotations

from unittest.mock import MagicMock

from app.agents.historical_agent import HistoricalAgentResult, SourceRef
from app.agents.local_orchestrator import LocalOrchestrator
from app.schemas.chat import ChatRequest


def test_local_orchestrator_returns_chat_response() -> None:
    db = MagicMock()
    memory_agent = MagicMock()
    historical_agent = MagicMock()

    memory_agent.get_context.return_value = {"preferred_language": "fr", "interests": []}
    memory_agent.record_turn.return_value = {
        "preferred_language": "fr",
        "interests": ["romain"],
        "available_time_minutes": None,
        "last_mentioned_monuments": ["Theatre"],
        "primary_site_id": 1,
        "primary_site_name": "Theatre",
    }
    historical_agent.answer.return_value = HistoricalAgentResult(
        answer="Réponse historique.",
        sources=[
            SourceRef(
                source_type="monument",
                source_id=1.0,
                title="Theatre",
                score=0.88,
            )
        ],
        suggested_actions=["Afficher les horaires"],
        memory_updates={"last_mentioned_monuments": ["Theatre"]},
    )

    orchestrator = LocalOrchestrator(
        db,
        memory_agent=memory_agent,
        historical_agent=historical_agent,
    )
    response = orchestrator.handle_chat(
        ChatRequest(
            session_id="orch_test",
            message="Parle-moi du théâtre.",
            language="fr",
        )
    )

    memory_agent.get_or_create_session.assert_called_once()
    historical_agent.answer.assert_called_once()
    memory_agent.record_turn.assert_called_once()
    db.commit.assert_called_once()

    assert response.session_id == "orch_test"
    assert response.answer == "Réponse historique."
    assert len(response.sources) == 1
    assert response.sources[0].title == "Theatre"
    assert response.memory_context.interests == ["romain"]
    assert response.suggested_actions == ["Afficher les horaires"]
