from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def normalize_monument_reference_id(value: object | None) -> str:
    """Normalize a monument identifier from DB values to the string form used by the app."""
    if value is None:
        return ""

    raw_text = str(value).strip()
    if not raw_text:
        return ""

    try:
        decimal_value = Decimal(raw_text)
    except InvalidOperation:
        return raw_text

    if decimal_value == decimal_value.to_integral():
        return str(int(decimal_value))

    normalized = format(decimal_value.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized


def normalize_monument_name(value: object | None) -> str:
    """Compare monument names in a normalized form that ignores accents and spacing."""
    if value is None:
        return ""

    text = unicodedata.normalize("NFKD", str(value).strip())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def resolve_monument_name(session: Session, monument_id: object | None) -> str | None:
    """Resolve a monument identifier to its French name via monuments.nom_monument_fr."""
    if monument_id is None:
        return None

    normalized_id = normalize_monument_reference_id(monument_id)
    if not normalized_id:
        return None

    result = session.execute(
        text(
            "SELECT nom_monument_fr FROM monuments WHERE id_monument = :id_monument"
        ),
        {"id_monument": normalized_id},
    ).scalar_one_or_none()
    if result is not None:
        return str(result)

    rows = session.execute(text("SELECT id_monument, nom_monument_fr FROM monuments")).mappings().all()
    for row in rows:
        if normalize_monument_reference_id(row.get("id_monument")) == normalized_id:
            return str(row.get("nom_monument_fr"))

    return None


def build_distance_lookup(
    session: Session,
    *,
    monument_ids: list[str],
) -> tuple[dict[tuple[str, str], dict[str, Any]], list[tuple[str, str]]]:
    """Build a lookup of distance rows using the real distance table keyed by from_lieu/to_lieu."""
    names_by_id: dict[str, str | None] = {}
    for monument_id in monument_ids:
        names_by_id[str(monument_id)] = resolve_monument_name(session, monument_id)

    try:
        rows = session.execute(
            text(
                "SELECT from_lieu, to_lieu, distance_km FROM distance"
            )
        ).mappings().all()
    except Exception as exc:  # pragma: no cover - depends on DB availability
        print(f"[circuits] Unable to read distance table: {exc}")
        return {}, []

    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    unresolved: list[tuple[str, str]] = []

    normalized_rows: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        from_name = str(row.get("from_lieu") or "")
        to_name = str(row.get("to_lieu") or "")
        if not from_name or not to_name:
            continue
        normalized_rows[(normalize_monument_name(from_name), normalize_monument_name(to_name))] = {
            "from_lieu": from_name,
            "to_lieu": to_name,
            "distance_km": float(row.get("distance_km") or 0.0),
            "duration_walk_min": 0.0,
            "duration_bike_min": 0.0,
            "duration_car_min": 0.0,
        }

    for monument_id in monument_ids:
        from_name = names_by_id.get(str(monument_id))
        if not from_name:
            continue

        from_key = normalize_monument_name(from_name)
        for target_id in monument_ids:
            if monument_id == target_id:
                continue
            to_name = names_by_id.get(str(target_id))
            if not to_name:
                continue

            to_key = normalize_monument_name(to_name)
            if from_key == to_key:
                lookup[(str(monument_id), str(target_id))] = {
                    "distance_km": 0.0,
                    "duration_walk_min": 0.0,
                    "duration_bike_min": 0.0,
                    "duration_car_min": 0.0,
                }
                continue

            row = normalized_rows.get((from_key, to_key))
            if row is None:
                unresolved.append((from_name, to_name))
                continue

            lookup[(str(monument_id), str(target_id))] = {
                "distance_km": row["distance_km"],
                "duration_walk_min": row["duration_walk_min"],
                "duration_bike_min": row["duration_bike_min"],
                "duration_car_min": row["duration_car_min"],
            }

    if unresolved:
        unique_unresolved = list(dict.fromkeys(unresolved))
        for from_name, to_name in unique_unresolved:
            print(f"[circuits] No distance match for monument pair: {from_name} -> {to_name}")

    return lookup, unique_unresolved if "unique_unresolved" in locals() else []
