"""Test real alarm entities without contacting an alarm panel."""

from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant.common import MockConfigEntry

from custom_components.aapalarm.alarm_control_panel import AAPModuleAlarm
from custom_components.aapalarm.const import DOMAIN


@pytest.mark.parametrize(
    ("alarm", "code", "status", "allowed", "sent_code"),
    [
        ({}, "1234", {"armed": True}, True, "1234"),
        ({}, "9999", {"armed": True}, False, None),
        ({}, None, {"armed": True}, False, None),
        ({}, None, {"exit_delay": True}, True, "1234"),
        ({"code": ""}, None, {"armed": True}, True, ""),
        ({}, 1234, {"stay_armed": True}, True, "1234"),
    ],
    indirect=["alarm"],
)
async def test_disarm(
    alarm: AAPModuleAlarm,
    mock_panel: MagicMock,
    code: str | int | None,
    status: dict[str, bool],
    allowed: bool,
    sent_code: str | None,
) -> None:
    mock_panel.area_state["A"]["status"] = status
    await alarm.async_alarm_disarm(code)
    if allowed:
        mock_panel.disarm.assert_called_once_with(sent_code)
    else:
        mock_panel.disarm.assert_not_called()


@pytest.mark.parametrize(
    ("method", "command", "required_setting"),
    [
        ("async_alarm_arm_home", "arm_stay", "code_arm_required"),
        ("async_alarm_arm_away", "arm_away", "code_arm_required"),
        ("async_alarm_trigger", "panic_alarm", "code_panic_required"),
    ],
)
@pytest.mark.parametrize(
    ("code", "required", "allowed"),
    [
        ("1234", True, True),
        ("9999", True, False),
        (None, True, False),
        (None, False, True),
    ],
)
async def test_arm_and_panic_codes(
    alarm: AAPModuleAlarm,
    mock_panel: MagicMock,
    method: str,
    command: str,
    required_setting: str,
    code: str | None,
    required: bool,
    allowed: bool,
) -> None:
    if required_setting == "code_arm_required":
        alarm._code_arm_required = required
    else:
        alarm._code_panic_required = required
    await getattr(alarm, method)(code)
    controller_method = getattr(mock_panel, command)
    if allowed:
        controller_method.assert_called_once_with(
            *([""] if command == "panic_alarm" else [])
        )
    else:
        controller_method.assert_not_called()
    mock_panel.send_keypress.assert_not_called()


@pytest.mark.parametrize("alarm", [{"code": ""}], indirect=True)
async def test_panic_without_configured_code(
    alarm: AAPModuleAlarm, mock_panel: MagicMock
) -> None:
    await alarm.async_alarm_trigger(None)
    mock_panel.panic_alarm.assert_called_once_with("")


@pytest.mark.parametrize(
    ("keypress", "expected"),
    [
        ("0123456789", "0123456789"),
        ("CNRSXABEH", "CNRSXABEH"),
        ("abc", "ABC"),
        ("P", None),
        ("1234!", None),
        ("1234;DROP", None),
        ("1234\n5678", None),
        (None, None),
        ("", None),
        ("1" * 17, None),
        ("1" * 16, "1" * 16),
        ("1234E", "1234E"),
    ],
)
def test_keypress(
    alarm: AAPModuleAlarm,
    mock_panel: MagicMock,
    keypress: str | None,
    expected: str | None,
) -> None:
    alarm.async_alarm_keypress(keypress)
    if expected is None:
        mock_panel.send_keypress.assert_not_called()
    else:
        mock_panel.send_keypress.assert_called_once_with(expected)


@pytest.mark.parametrize(
    ("service", "code", "command"),
    [
        ("alarm_arm_home", "1234", "arm_stay"),
        ("alarm_arm_away", "1234", "arm_away"),
        ("alarm_disarm", "1234", "disarm"),
        ("alarm_trigger", "1234", "panic_alarm"),
    ],
)
async def test_alarm_services(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_panel: MagicMock,
    service: str,
    code: str,
    command: str,
) -> None:
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id(
        "alarm_control_panel", DOMAIN, f"{config_entry.entry_id}_House"
    )
    assert entity_id is not None
    await hass.services.async_call(
        "alarm_control_panel",
        service,
        {"entity_id": entity_id, "code": code},
        blocking=True,
    )
    expected_args = {"disarm": ("1234",), "panic_alarm": ("",)}.get(command, ())
    getattr(mock_panel, command).assert_called_once_with(*expected_args)


@pytest.mark.parametrize(("keys", "allowed"), [("1234e", True), ("P", False)])
async def test_keypress_service(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_panel: MagicMock,
    keys: str,
    allowed: bool,
) -> None:
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id(
        "alarm_control_panel", DOMAIN, f"{config_entry.entry_id}_House"
    )
    assert entity_id is not None
    await hass.services.async_call(
        "alarm_control_panel",
        "aap_alarm_keypress",
        {"entity_id": [entity_id], "keypress": keys},
        blocking=True,
    )
    if allowed:
        mock_panel.send_keypress.assert_called_once_with("1234E")
    else:
        mock_panel.send_keypress.assert_not_called()
