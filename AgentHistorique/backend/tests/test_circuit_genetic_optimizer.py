from __future__ import annotations

from decimal import Decimal

from app.circuits.constraints import ConstraintContext
from app.circuits.data_loader import GraphEdge, MonumentNode
from app.circuits.dijkstra import DijkstraRouter
from app.circuits.genetic_optimizer import GAConfig, GeneticOptimizer


def _node(monument_id: int, name: str, *, price: float = 2, popularity: float = 4) -> MonumentNode:
    return MonumentNode(
        id=Decimal(monument_id),
        name=name,
        latitude=36.85 + monument_id * 0.001,
        longitude=10.33 + monument_id * 0.001,
        visit_duration_min=20,
        popularity=popularity,
        price=price,
        dominant_period="Romaine",
        secondary_period="Punique",
        third_period=None,
        function="musee",
        accessibility=None,
        relief=None,
    )


def _build_router(nodes: dict[Decimal, MonumentNode]) -> DijkstraRouter:
    graph: dict[Decimal, dict[Decimal, GraphEdge]] = {}
    ids = list(nodes.keys())
    for i, from_id in enumerate(ids):
        graph[from_id] = {}
        for j, to_id in enumerate(ids):
            if i == j:
                continue
            graph[from_id][to_id] = GraphEdge(to_id, 0.3, 5, 3, 2)
    return DijkstraRouter(graph, nodes, transport="walking")


def test_genetic_optimizer_returns_valid_circuit() -> None:
    nodes = {
        Decimal(1): _node(1, "Thermes d'Antonin"),
        Decimal(2): _node(2, "Theatre"),
        Decimal(3): _node(3, "Tophet"),
        Decimal(4): _node(4, "Ports puniques"),
    }
    candidates = nodes.copy()
    scores = {mid: 0.8 for mid in candidates}
    context = ConstraintContext(
        budget_max=50,
        duration_minutes=240,
        mobilite="normale",
        required_ids=frozenset({Decimal(1)}),
        excluded_ids=frozenset(),
        max_stops=4,
    )
    optimizer = GeneticOptimizer(
        candidates=candidates,
        scores=scores,
        router=_build_router(nodes),
        context=context,
        config=GAConfig(population_size=20, generations=15, max_stops=4),
        seed=42,
    )
    result = optimizer.optimize()
    assert result.chromosome
    assert Decimal(1) in result.chromosome
    assert len(set(result.chromosome)) == len(result.chromosome)
    assert result.fitness > -100
