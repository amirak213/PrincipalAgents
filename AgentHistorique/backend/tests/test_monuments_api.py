from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.monument import MonumentSummaryResponse, MonumentsListResponse


def _sample_monuments() -> MonumentsListResponse:
    return MonumentsListResponse(
        monuments=[
            MonumentSummaryResponse(
                id=22.0,
                name_fr="Thermes d'Antonin",
                name_en="Antonine Baths",
                name_ar=None,
                latitude=36.8545707,
                longitude=10.3345294,
                visit_duration_min=60,
                dominant_period="Romaine",
                function="culturel",
                popularity=5,
                image_url=None,
            )
        ]
    )


def test_get_monuments_returns_list() -> None:
    with patch("app.api.routes_monuments.list_monuments") as mock_list:
        mock_list.return_value = _sample_monuments()
        client = TestClient(app)
        response = client.get("/api/monuments")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["monuments"]) == 1
    assert payload["monuments"][0]["name_fr"] == "Thermes d'Antonin"
    mock_list.assert_called_once()
