import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from AgentPrincipal.wizard_state_machine import (
    WizardEvent,
    WizardSession,
    WizardState,
    WizardValidationError,
    apply_event,
    start_wizard,
)


def test_load_more_places_increments_offset_without_leaving_place_selection():
    wizard = WizardSession(
        session_id="demo",
        state=WizardState.PLACE_SELECTION,
        places_offset=0,
    )

    updated = apply_event(wizard, WizardEvent(type="load_more_places"))

    assert updated.state == WizardState.PLACE_SELECTION
    assert updated.places_offset == 1


@pytest.mark.parametrize(
    "profile",
    [None, "", "unknown"],
)
def test_budget_rejects_missing_or_invalid_tariff_profile(profile):
    wizard = WizardSession(
        session_id="demo",
        state=WizardState.CUSTOMIZATION_BUDGET,
    )

    with pytest.raises(WizardValidationError, match="Profil tarifaire"):
        apply_event(
            wizard,
            WizardEvent(type="set_budget", value={"type": profile, "amount": 150}),
        )

    assert wizard.budget is None
    assert wizard.state == WizardState.CUSTOMIZATION_BUDGET


@pytest.mark.parametrize(
    "value",
    [
        None,
        "walking",
        {"transport": "walking"},
        {"transport": "unknown", "mobilite": "reduite"},
        {"transport": "walking", "mobilite": "unknown"},
    ],
)
def test_mobility_rejects_missing_or_invalid_fields_without_transition(value):
    wizard = WizardSession(
        session_id="demo",
        state=WizardState.CUSTOMIZATION_MOBILITY,
    )

    with pytest.raises(WizardValidationError):
        apply_event(wizard, WizardEvent(type="set_mobility", value=value))

    assert wizard.state == WizardState.CUSTOMIZATION_MOBILITY
    assert wizard.mobility is None
    assert wizard.mobilite is None


def test_mobility_stores_transport_and_level_before_advancing():
    wizard = WizardSession(
        session_id="demo",
        state=WizardState.CUSTOMIZATION_MOBILITY,
    )

    updated = apply_event(
        wizard,
        WizardEvent(
            type="set_mobility",
            value={"transport": "walking", "mobilite": "reduite"},
        ),
    )

    assert updated.mobility == "walking"
    assert updated.mobilite == "reduite"
    assert updated.state == WizardState.CUSTOMIZATION_TIME


def test_wizard_starts_on_profile_without_city_selection():
    wizard = start_wizard("demo")

    assert wizard.state == WizardState.CUSTOMIZATION_BUDGET
    assert not hasattr(wizard, "city")


@pytest.mark.parametrize(
    "value",
    [
        None,
        {"duration_minutes": 120, "start_time": "09:00"},
        {"duration_minutes": 10, "start_time": "09:00", "end_time": "12:00"},
        {"duration_minutes": 120, "start_time": "12:00", "end_time": "09:00"},
    ],
)
def test_time_rejects_missing_or_invalid_values_without_transition(value):
    wizard = WizardSession(
        session_id="demo",
        state=WizardState.CUSTOMIZATION_TIME,
    )

    with pytest.raises(WizardValidationError):
        apply_event(wizard, WizardEvent(type="set_time", value=value))

    assert wizard.state == WizardState.CUSTOMIZATION_TIME
    assert wizard.time_constraints is None


def test_nominal_flow_orders_profile_time_preferences_then_places():
    wizard = WizardSession(
        session_id="demo",
        state=WizardState.CUSTOMIZATION_TIME,
    )
    wizard = apply_event(
        wizard,
        WizardEvent(
            type="set_time",
            value={
                "duration_minutes": 120,
                "start_time": "09:00",
                "end_time": "12:00",
                "date": "ignored",
            },
        ),
    )
    assert wizard.state == WizardState.CUSTOMIZATION_PREFERENCES
    assert wizard.time_constraints == {
        "duration_minutes": 120,
        "start_time": "09:00",
        "end_time": "12:00",
    }

    wizard = apply_event(
        wizard,
        WizardEvent(type="set_preferences", value={"epoques": ["Romaine"], "fonctions": ["musee"]}),
    )
    assert wizard.state == WizardState.PLACE_SELECTION

    wizard = apply_event(wizard, WizardEvent(type="select_places", value=[]))
    assert wizard.state == WizardState.CIRCUIT_GENERATION


def test_from_json_migrates_legacy_city_and_calendar_date():
    wizard = WizardSession.from_json(
        '{"session_id":"demo","state":"CITY_SELECTION","city":"carthage",'
        '"dates":{"date":"2026-09-28","start_time":"09:00",'
        '"end_time":"12:00"}}'
    )

    assert wizard.state == WizardState.CUSTOMIZATION_BUDGET
    assert wizard.time_constraints == {"start_time": "09:00", "end_time": "12:00"}
