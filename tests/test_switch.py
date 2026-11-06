"""Test real output entities and HA switch service dispatch."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant.common import MockConfigEntry

from custom_components.aapalarm.const import DOMAIN
from custom_components.aapalarm.switch import AAPModuleOutput


@pytest.mark.parametrize(
    ("info", "expected"),
    [
        ({"status": {"open": True}}, True),
        ({"status": {"open": False}}, False),
        (None, False),
        ({"something": "else"}, False),
    ],
)
async def test_is_on_is_pure(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_panel: MagicMock,
    info: dict[str, Any] | None,
    expected: bool,
) -> None:
    switch = AAPModuleOutput(hass, config_entry, 1, "Gate", info, mock_panel)
    original_state = switch._state
    assert switch.is_on is expected
    assert switch.is_on is expected
    assert switch._state == original_state
    mock_panel.command_output.assert_not_called()


@pytest.mark.parametrize("service", ["turn_on", "turn_off"])
async def test_output_services(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_panel: MagicMock,
    service: str,
) -> None:
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id(
        "switch", DOMAIN, f"{config_entry.entry_id}_Gate"
    )
    assert entity_id is not None
    await hass.services.async_call(
        "switch", service, {"entity_id": entity_id}, blocking=True
    )
    mock_panel.command_output.assert_called_once_with("1")
