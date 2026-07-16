from __future__ import annotations

from decimal import Decimal

from app.circuits.constraints import ConstraintContext, filter_monuments
from app.circuits.data_loader import MonumentNode


def _node(
    monument_id: int,
    *,
    name: str,
    price: float = 2,
    lat: float = 36.85,
    lng: float = 10.33,
) -> MonumentNode:
    return MonumentNode(
        id=Decimal(monument_id),
        name=name,
        latitude=lat,
        longitude=lng,
        visit_duration_min=30,
        popularity=4,
        price=price,
        dominant_period="Romaine",
        secondary_period=None,
        third_period=None,
        function="musee",
        accessibility=None,
        relief=None,
    )


def test_constraints_exclude_monuments_and_enforce_required() -> None:
    nodes = {
        Decimal(1): _node(1, name="Thermes d'Antonin"),
        Decimal(2): _node(2, name="Theatre"),
        Decimal(3): _node(3, name="Tophet", price=50),
    }
    context = ConstraintContext(
        budget_max=30,
        duration_minutes=180,
        mobilite="normale",
        required_ids=frozenset({Decimal(1)}),
        excluded_ids=frozenset({Decimal(2)}),
    )
    candidates, warnings = filter_monuments(nodes, context)
    assert Decimal(2) not in candidates
    assert Decimal(1) in candidates
    assert Decimal(3) not in candidates


def test_constraints_keeps_required_monument_over_budget() -> None:
    nodes = {
        Decimal(1): _node(1, name="Thermes d'Antonin", price=40),
        Decimal(2): _node(2, name="Theatre", price=2),
    }
    context = ConstraintContext(
        budget_max=10,
        duration_minutes=180,
        mobilite="normale",
        required_ids=frozenset({Decimal(1)}),
        excluded_ids=frozenset(),
    )
    candidates, _ = filter_monuments(nodes, context)
    assert Decimal(1) in candidates
