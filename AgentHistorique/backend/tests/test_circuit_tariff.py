from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.circuits.data_loader import get_monument_price


def test_tariff_price_calculation_maps_etudiant_to_student_column() -> None:
    monument = SimpleNamespace(
        price_resident=9,
        price_student=2,
        price_foreign=12,
        price_teacher=4.5,
        price_senior=4.5,
        price_child=2,
    )
    assert get_monument_price(monument, "etudiant") == 2.0
    assert get_monument_price(monument, "resident") == 9.0
    assert get_monument_price(monument, "etranger") == 12.0


def test_tariff_price_missing_value_returns_zero() -> None:
    monument = SimpleNamespace(
        price_resident=None,
        price_student=None,
        price_foreign=None,
        price_teacher=None,
        price_senior=None,
        price_child=None,
    )
    assert get_monument_price(monument, "etudiant") == 0.0
