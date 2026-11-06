"""Use real Home Assistant objects and mock only the physical alarm interface."""

from collections.abc import Generator
from copy import deepcopy
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pyaapalarmmodule import AAPAlarmPanel
from pytest_homeassistant.common import MockConfigEntry

from custom_components.aapalarm.alarm_control_panel import AAPModuleAlarm
from custom_components.aapalarm.const import DOMAIN

from .const import ENTRY_DATA


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="aapalarm_192.0.2.1_5002",
        data=deepcopy(ENTRY_DATA),
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture(autouse=True)
def mock_panel() -> Generator[MagicMock, None, None]:
    panel = MagicMock(spec=AAPAlarmPanel)
    panel.area_state = {"A": {"status": {"disarmed": True}}}
    panel.zone_state = {1: {"status": {"open": False}}}
    panel.output_state = {1: {"status": {"open": False}}}
    panel.system_state = {"status": {"mains": True, "ready": True}}
    panel.start.side_effect = lambda: panel.callback_connected(None)
    with patch("custom_components.aapalarm.AAPAlarmPanel", return_value=panel):
        yield panel


@pytest.fixture
async def alarm(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_panel: MagicMock,
    request: pytest.FixtureRequest,
) -> AAPModuleAlarm:
    settings = getattr(request, "param", {})
    return AAPModuleAlarm(
        hass,
        config_entry,
        1,
        "House",
        settings.get("code", "1234"),
        settings.get("code_arm_required", True),
        settings.get("code_panic_required", True),
        mock_panel.area_state["A"],
        mock_panel,
    )
