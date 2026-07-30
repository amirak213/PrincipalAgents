import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from AgentPrincipal.wizard_state_machine import (
    WizardEvent,
    WizardSession,
    WizardState,
    apply_event,
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
