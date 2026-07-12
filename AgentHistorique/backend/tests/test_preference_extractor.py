from __future__ import annotations

from app.memory.preference_extractor import (
    extract_preferences_from_message,
    merge_memory_updates,
)


def test_extract_interests_from_message() -> None:
    result = extract_preferences_from_message("Je suis intéressé par l'architecture romaine.")
    assert "romain" in result.get("interests", [])
    assert "architecture" in result.get("interests", [])


def test_extract_available_time_hours_minutes() -> None:
    result = extract_preferences_from_message("J'ai 1h30 pour visiter Carthage.")
    assert result.get("available_time_minutes") == 90


def test_extract_mobility_mode_walking() -> None:
    result = extract_preferences_from_message("Je préfère visiter à pied.")
    assert result.get("mobility_mode") == "walking"


def test_merge_memory_updates_keeps_monuments() -> None:
    merged = merge_memory_updates(
        {"last_mentioned_monuments": ["Theatre"]},
        {"interests": ["romain"]},
        {"last_mentioned_monuments": ["Thermes d'Antonin"]},
    )
    assert "Thermes d'Antonin" in merged["last_mentioned_monuments"]
    assert "romain" in merged["interests"]
