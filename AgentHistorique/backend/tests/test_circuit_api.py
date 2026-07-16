from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.agents.circuit_agent import CircuitAgentResult
from app.main import app
from app.schemas.circuit_agent import (
    CircuitConstraintsStatus,
    CircuitRecommendationResponse,
    CircuitSummary,
    MapRoutePayload,
    RecommendedMonument,
    RouteSegment,
)


def _sample_response() -> CircuitRecommendationResponse:
    return CircuitRecommendationResponse(
        session_id="session_001",
        circuit=CircuitSummary(
            title="Circuit personnalisé à Carthage",
            summary="2 monuments, 90 min au total.",
            monuments=[
                RecommendedMonument(
                    order=1,
                    monument_id=22.0,
                    name="Thermes d'Antonin",
                    latitude=36.8545707,
                    longitude=10.3345294,
                    visit_duration_min=60,
                    price=2,
                    arrival_time="09:00",
                    departure_time="10:00",
                    reason="Correspond à votre intérêt pour l'époque romaine.",
                )
            ],
            total_visit_duration_min=60,
            total_travel_duration_min=10,
            total_duration_min=70,
            total_distance_km=0.8,
            total_price=2,
            score=0.87,
        ),
        route=MapRoutePayload(
            transport="walking",
            polyline=[[36.8545707, 10.3345294]],
            segments=[
                RouteSegment.model_validate(
                    {
                        "from": "Thermes d'Antonin",
                        "to": "Theatre",
                        "distance_km": 0.7,
                        "duration_min": 9,
                        "path": [[36.8545707, 10.3345294], [36.8562934, 10.3283601]],
                    }
                )
            ],
        ),
        constraints=CircuitConstraintsStatus(
            budget_ok=True,
            duration_ok=True,
            mobility_ok=True,
        ),
        explanation=["Le circuit respecte le budget maximal."],
        alternatives=[],
        feasible=True,
    )


def test_circuit_recommend_endpoint_returns_expected_schema() -> None:
    mock_result = CircuitAgentResult(response=_sample_response())
    with patch("app.api.routes_circuit_agent.CircuitAgent") as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.recommend.return_value = mock_result
        mock_agent_cls.return_value = mock_agent

        client = TestClient(app)
        response = client.post(
            "/api/circuits/recommend",
            json={
                "session_id": "session_001",
                "age": 22,
                "type_tarif": "etudiant",
                "budget_max": 30,
                "transport": "walking",
                "mobilite": "normale",
                "duration_minutes": 120,
                "start_time": "09:00",
                "end_time": "11:00",
                "zone": "Carthage",
                "preferences": {
                    "epoques": ["Romaine", "Punique"],
                    "fonctions": ["musee", "religieux", "culturel"],
                    "must_visit": ["Thermes d'Antonin"],
                    "avoid": [],
                },
                "start_location": None,
                "end_location": None,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "session_001"
    assert payload["circuit"]["title"].startswith("Circuit personnalisé")
    assert payload["circuit"]["monuments"][0]["name"] == "Thermes d'Antonin"
    assert payload["route"]["transport"] == "walking"
    assert payload["constraints"]["budget_ok"] is True
    assert payload["explanation"]


def test_circuit_recommend_impossible_constraints_returns_422() -> None:
    from app.agents.circuit_agent import CircuitAgentError

    with patch("app.api.routes_circuit_agent.CircuitAgent") as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.recommend.side_effect = CircuitAgentError(
            "Aucun circuit réalisable avec ces contraintes."
        )
        mock_agent_cls.return_value = mock_agent

        client = TestClient(app)
        response = client.post(
            "/api/circuits/recommend",
            json={
                "session_id": "session_001",
                "type_tarif": "etudiant",
                "budget_max": 1,
                "transport": "walking",
                "mobilite": "normale",
                "duration_minutes": 15,
                "zone": "Carthage",
                "preferences": {
                    "must_visit": ["Monument Inexistant"],
                    "avoid": [],
                },
            },
        )

    assert response.status_code == 422
    assert "introuvable" in response.json()["detail"].lower() or "réalisable" in response.json()["detail"].lower()
