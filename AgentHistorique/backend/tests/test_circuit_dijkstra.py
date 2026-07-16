from __future__ import annotations

from decimal import Decimal

from app.circuits.data_loader import GraphEdge, MonumentNode
from app.circuits.dijkstra import DijkstraRouter


def _node(monument_id: int, name: str, lat: float, lng: float) -> MonumentNode:
    return MonumentNode(
        id=Decimal(monument_id),
        name=name,
        latitude=lat,
        longitude=lng,
        visit_duration_min=15,
        popularity=4,
        price=2,
        dominant_period="Romaine",
        secondary_period=None,
        third_period=None,
        function="musee",
        accessibility=None,
        relief=None,
    )


def test_dijkstra_returns_shortest_path_on_small_graph() -> None:
    nodes = {
        Decimal(1): _node(1, "A", 36.0, 10.0),
        Decimal(2): _node(2, "B", 36.001, 10.0),
        Decimal(3): _node(3, "C", 36.002, 10.0),
    }
    graph = {
        Decimal(1): {
            Decimal(2): GraphEdge(Decimal(2), 0.1, 5, 3, 1),
            Decimal(3): GraphEdge(Decimal(3), 1.0, 20, 10, 5),
        },
        Decimal(2): {
            Decimal(3): GraphEdge(Decimal(3), 0.1, 4, 2, 1),
        },
    }
    router = DijkstraRouter(graph, nodes, transport="walking")
    result = router.shortest_path(Decimal(1), Decimal(3))
    assert result is not None
    assert result.path == [Decimal(1), Decimal(2), Decimal(3)]
    assert result.duration_min == 9.0


def test_dijkstra_unknown_monument_returns_none_without_fallback() -> None:
    nodes = {Decimal(1): _node(1, "A", 36.0, 10.0)}
    router = DijkstraRouter({}, nodes, transport="walking", fallback_enabled=False)
    assert router.shortest_path(Decimal(1), Decimal(99)) is None


def test_dijkstra_uses_haversine_fallback_when_edge_missing() -> None:
    nodes = {
        Decimal(1): _node(1, "A", 36.0, 10.0),
        Decimal(2): _node(2, "B", 36.01, 10.01),
    }
    router = DijkstraRouter({}, nodes, transport="walking", fallback_enabled=True)
    result = router.shortest_path(Decimal(1), Decimal(2))
    assert result is not None
    assert result.used_fallback is True
    assert result.duration_min > 0
