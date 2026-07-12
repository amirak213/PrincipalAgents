from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.chat import ChatResponse, MemoryContextSchema, SourceRefSchema


def test_chat_endpoint_returns_expected_schema() -> None:
    mock_response = ChatResponse(
        session_id="test_session",
        answer="Réponse de test.",
        sources=[
            SourceRefSchema(
                source_type="monument",
                source_id=3.9,
                title="Thermes d'Antonin",
                score=0.91,
            )
        ],
        memory_context=MemoryContextSchema(
            preferred_language="fr",
            last_mentioned_monuments=["Thermes d'Antonin"],
            primary_site_id=3,
            primary_site_name="Parc des thermes d'Antonin",
        ),
        suggested_actions=["Afficher les horaires"],
    )

    with patch("app.api.routes_chat.LocalOrchestrator") as mock_orchestrator_cls:
        mock_orchestrator = MagicMock()
        mock_orchestrator.handle_chat.return_value = mock_response
        mock_orchestrator_cls.return_value = mock_orchestrator

        client = TestClient(app)
        response = client.post(
            "/api/chat",
            json={
                "session_id": "test_session",
                "message": "Explique-moi les Thermes d'Antonin",
                "language": "fr",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "test_session"
    assert payload["answer"] == "Réponse de test."
    assert len(payload["sources"]) == 1
    assert payload["sources"][0]["source_type"] == "monument"
    assert payload["sources"][0]["source_id"] == 3.9
    assert payload["memory_context"]["primary_site_id"] == 3
    assert payload["suggested_actions"] == ["Afficher les horaires"]
    mock_orchestrator.handle_chat.assert_called_once()


def test_chat_endpoint_accepts_web_source_schema() -> None:
    mock_response = ChatResponse(
        session_id="test_session",
        answer="Réponse avec source web.",
        sources=[
            SourceRefSchema(
                source_type="monument",
                source_id=3.9,
                title="Thermes d'Antonin",
                score=0.91,
            ),
            SourceRefSchema(
                source_type="web",
                source_id=None,
                title="Fouilles récentes à Carthage",
                score=None,
                url="https://example.com/fouilles",
            ),
        ],
        memory_context=MemoryContextSchema(preferred_language="fr"),
        suggested_actions=["Afficher les horaires"],
    )

    with patch("app.api.routes_chat.LocalOrchestrator") as mock_orchestrator_cls:
        mock_orchestrator = MagicMock()
        mock_orchestrator.handle_chat.return_value = mock_response
        mock_orchestrator_cls.return_value = mock_orchestrator

        client = TestClient(app)
        response = client.post(
            "/api/chat",
            json={
                "session_id": "test_session",
                "message": "Y a-t-il des informations récentes sur les fouilles à Carthage ?",
                "language": "fr",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "test_session"
    assert payload["answer"] == "Réponse avec source web."
    assert len(payload["sources"]) == 2
    assert payload["sources"][1]["source_type"] == "web"
    assert payload["sources"][1]["source_id"] is None
    assert payload["sources"][1]["url"] == "https://example.com/fouilles"
