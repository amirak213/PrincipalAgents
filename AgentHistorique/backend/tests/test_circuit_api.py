from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.agents.circuit_agent import CircuitAgentResult
from app.circuits.constraints import ConstraintContext
from app.circuits.data_loader import CircuitDataLoader, MonumentNode, get_monument_price
from app.circuits.route_builder import build_route
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
            unknown_price_count=0,
            budget_max=30,
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
    assert payload["circuit"]["budget_max"] == 30
    assert payload["circuit"]["unknown_price_count"] == 0
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
                    "epoques": [],
                    "fonctions": [],
                    "must_visit": ["Monument Inexistant"],
                    "avoid": [],
                },
            },
        )

    assert response.status_code == 422
    assert "introuvable" in response.json()["detail"].lower() or "réalisable" in response.json()["detail"].lower()


def test_loader_keeps_database_null_price_as_none() -> None:
    monument = SimpleNamespace(
        id_str="1",
        name_fr="Tarif inconnu",
        latitude_float=36.8,
        longitude_float=10.3,
        visit_duration_minutes=30,
        priority=3,
        dominant_period=None,
        secondary_period=None,
        third_period=None,
        function=None,
        accessibility=None,
        relief=None,
        price_student=None,
    )
    db = MagicMock()
    db.scalars.return_value.all.return_value = [monument]

    nodes = CircuitDataLoader(db).load_monuments("etudiant")

    assert nodes["1"].price is None
    assert get_monument_price(monument, "etudiant") is None


def test_route_total_sums_selected_profile_prices_and_counts_unknowns() -> None:
    profile_prices = [
        get_monument_price(SimpleNamespace(price_student=Decimal("2")), "etudiant"),
        get_monument_price(SimpleNamespace(price_student=Decimal("3.5")), "etudiant"),
    ]
    candidates = {
        "1": MonumentNode(
            id="1", name="Payant A", latitude=36.8, longitude=10.3,
            visit_duration_min=20, price=profile_prices[0],
        ),
        "2": MonumentNode(
            id="2", name="Payant B", latitude=36.81, longitude=10.31,
            visit_duration_min=20, price=profile_prices[1],
        ),
        "3": MonumentNode(
            id="3", name="Inconnu", latitude=36.82, longitude=10.32,
            visit_duration_min=20, price=None,
        ),
    }
    context = ConstraintContext(
        budget_max=100,
        duration_minutes=180,
        mobilite="normale",
        required_ids=frozenset(),
        excluded_ids=frozenset(),
    )

    class NoRoute:
        @staticmethod
        def shortest_path(_from_id: str, _to_id: str):
            return None

    route = build_route(
        ["1", "2", "3"],
        candidates=candidates,
        router=NoRoute(),
        context=context,
        fitness_score=0.8,
        preferred_periods=[],
        preferred_functions=[],
        transport="walking",
        start_time=None,
        zone="Carthage",
    )

    assert route.total_price == 5.5
    assert route.unknown_price_count == 1
    assert route.monuments[2]["price"] is None
