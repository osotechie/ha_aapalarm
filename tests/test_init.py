"""Test real lifecycle and push updates with the panel hardware mocked."""

from unittest.mock import MagicMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_TIMEOUT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant.common import MockConfigEntry

from custom_components.aapalarm.const import CONF_MESSAGE_LOG_ENABLED, DOMAIN


async def test_setup_and_unload(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_panel: MagicMock
) -> None:
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    assert hass.data[DOMAIN][config_entry.entry_id] is mock_panel
    mock_panel.start.assert_called_once()
    registry = er.async_get(hass)
    for domain, name, expected in [
        ("alarm_control_panel", "House", "disarmed"),
        ("binary_sensor", "Front Door", "off"),
        ("switch", "Gate", "off"),
        ("sensor", "Mains Power", "True"),
    ]:
        entity_id = registry.async_get_entity_id(
            domain, DOMAIN, f"{config_entry.entry_id}_{name}"
        )
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == expected

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    mock_panel.stop.assert_called_once()
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    assert config_entry.entry_id not in hass.data[DOMAIN]
    assert f"{config_entry.entry_id}_entry" not in hass.data[DOMAIN]


@pytest.mark.parametrize(
    ("callback", "attribute", "key", "info", "domain", "name", "expected"),
    [
        (
            "callback_area_state_change",
            "area_state",
            "A",
            {"status": {"armed": True}},
            "alarm_control_panel",
            "House",
            "armed_away",
        ),
        (
            "callback_zone_state_change",
            "zone_state",
            1,
            {"status": {"open": True}},
            "binary_sensor",
            "Front Door",
            "on",
        ),
        (
            "callback_output_state_change",
            "output_state",
            1,
            {"status": {"open": True}},
            "switch",
            "Gate",
            "on",
        ),
    ],
)
async def test_dispatcher_updates(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_panel: MagicMock,
    callback: str,
    attribute: str,
    key: str | int,
    info: dict[str, dict[str, bool]],
    domain: str,
    name: str,
    expected: str,
) -> None:
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    getattr(mock_panel, attribute)[key] = info
    getattr(mock_panel, callback)(key)
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id(
        domain, DOMAIN, f"{config_entry.entry_id}_{name}"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == expected

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    getattr(mock_panel, callback)(key)
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unavailable"


async def test_message_log(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_panel: MagicMock
) -> None:
    mock_panel._client = MagicMock()
    hass.config_entries.async_update_entry(
        config_entry,
        data={**config_entry.data, CONF_MESSAGE_LOG_ENABLED: True},
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    for number in range(7):
        mock_panel._client.process_line(f"message-{number}")
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{config_entry.entry_id}_Message Log"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "message-6"
    assert state.attributes["message_count"] == 5
    assert [message["raw"] for message in state.attributes["messages"]] == [
        f"message-{number}" for number in range(2, 7)
    ]


@pytest.mark.parametrize("failure", ["login", "timeout"])
@pytest.mark.parametrize("message_log", [False, True])
async def test_setup_failure_cleanup(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_panel: MagicMock,
    failure: str,
    message_log: bool,
) -> None:
    hass.config_entries.async_update_entry(
        config_entry,
        data={**config_entry.data, CONF_MESSAGE_LOG_ENABLED: message_log},
    )
    if failure == "login":
        mock_panel.start.side_effect = lambda: mock_panel.callback_login_timeout(None)
    else:
        mock_panel.start.side_effect = None
        hass.config_entries.async_update_entry(
            config_entry, data={**config_entry.data, CONF_TIMEOUT: 0.01}
        )
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    mock_panel.stop.assert_called_once()
    assert config_entry.entry_id not in hass.data[DOMAIN]
    assert f"{config_entry.entry_id}_message_log" not in hass.data[DOMAIN]
