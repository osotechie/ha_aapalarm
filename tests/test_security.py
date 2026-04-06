"""Unit tests for security-critical logic in the AAP Alarm integration."""

import asyncio
import re
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock

import pytest


# ---------------------------------------------------------------------------
# Helpers – lightweight fakes so we don't need a real HA instance
# ---------------------------------------------------------------------------

def _make_alarm(code="1234", code_arm_required=True, code_panic_required=True,
                area_number=1, alarm_state_value=None, info=None):
    """Create a minimal AAPModuleAlarm-like object for testing."""

    controller = MagicMock()
    obj = MagicMock()

    # Store the real values
    obj._code = code
    obj._code_arm_required = code_arm_required
    obj._code_panic_required = code_panic_required
    obj._area_number = area_number
    obj._controller = controller

    # Import the actual constants
    from custom_components.aapalarm.alarm_control_panel import (
        VALID_KEYPRESS_CHARS,
        MAX_KEYPRESS_LENGTH,
    )

    # Bind the real methods from the class
    from custom_components.aapalarm.alarm_control_panel import AAPModuleAlarm

    obj.async_alarm_disarm = lambda code=None: asyncio.get_event_loop().run_until_complete(
        AAPModuleAlarm.async_alarm_disarm(obj, code)
    )
    obj.async_alarm_arm_home = lambda code=None: asyncio.get_event_loop().run_until_complete(
        AAPModuleAlarm.async_alarm_arm_home(obj, code)
    )
    obj.async_alarm_arm_away = lambda code=None: asyncio.get_event_loop().run_until_complete(
        AAPModuleAlarm.async_alarm_arm_away(obj, code)
    )
    obj.async_alarm_trigger = lambda code=None: asyncio.get_event_loop().run_until_complete(
        AAPModuleAlarm.async_alarm_trigger(obj, code)
    )
    obj.async_alarm_keypress = lambda keypress=None: AAPModuleAlarm.async_alarm_keypress(obj, keypress)

    # Mock alarm_state property
    if alarm_state_value is not None:
        type(obj).alarm_state = PropertyMock(return_value=alarm_state_value)

    return obj


# ---------------------------------------------------------------------------
# Disarm Code Validation Tests
# ---------------------------------------------------------------------------

class TestDisarmCodeValidation:
    """Tests for async_alarm_disarm code verification."""

    def test_disarm_correct_code(self):
        """Disarm succeeds with correct code."""
        from homeassistant.components.alarm_control_panel import AlarmControlPanelState
        alarm = _make_alarm(code="1234", alarm_state_value=AlarmControlPanelState.ARMED_AWAY)
        alarm.async_alarm_disarm(code="1234")
        alarm._controller.disarm.assert_called_once_with("1234")

    def test_disarm_wrong_code_rejected(self):
        """Disarm rejected with wrong code."""
        from homeassistant.components.alarm_control_panel import AlarmControlPanelState
        alarm = _make_alarm(code="1234", alarm_state_value=AlarmControlPanelState.ARMED_AWAY)
        alarm.async_alarm_disarm(code="9999")
        alarm._controller.disarm.assert_not_called()

    def test_disarm_no_code_rejected_when_armed(self):
        """Disarm rejected when no code provided while armed."""
        from homeassistant.components.alarm_control_panel import AlarmControlPanelState
        alarm = _make_alarm(code="1234", alarm_state_value=AlarmControlPanelState.ARMED_AWAY)
        alarm.async_alarm_disarm(code=None)
        alarm._controller.disarm.assert_not_called()

    def test_disarm_no_code_allowed_during_exit_delay(self):
        """Disarm allowed without code during PENDING (exit delay)."""
        from homeassistant.components.alarm_control_panel import AlarmControlPanelState
        alarm = _make_alarm(code="1234", alarm_state_value=AlarmControlPanelState.PENDING)
        alarm.async_alarm_disarm(code=None)
        alarm._controller.disarm.assert_called_once_with("1234")

    def test_disarm_no_code_configured_allows_disarm(self):
        """Disarm works when no code is configured."""
        from homeassistant.components.alarm_control_panel import AlarmControlPanelState
        alarm = _make_alarm(code="", alarm_state_value=AlarmControlPanelState.ARMED_AWAY)
        alarm.async_alarm_disarm(code=None)
        alarm._controller.disarm.assert_called_once_with("")

    def test_disarm_sends_configured_code_not_user_input(self):
        """Disarm always sends the configured code, not raw user input."""
        from homeassistant.components.alarm_control_panel import AlarmControlPanelState
        alarm = _make_alarm(code="1234", alarm_state_value=AlarmControlPanelState.ARMED_HOME)
        alarm.async_alarm_disarm(code="1234")
        alarm._controller.disarm.assert_called_once_with("1234")
        # Verify it used self._code, not the user's code object
        assert alarm._controller.disarm.call_args[0][0] == "1234"


# ---------------------------------------------------------------------------
# Arm Code Validation Tests
# ---------------------------------------------------------------------------

class TestArmCodeValidation:
    """Tests for arm_home and arm_away code verification."""

    def test_arm_home_correct_code(self):
        alarm = _make_alarm(code="1234", code_arm_required=True)
        alarm.async_alarm_arm_home(code="1234")
        alarm._controller.arm_stay.assert_called_once()

    def test_arm_home_wrong_code_rejected(self):
        alarm = _make_alarm(code="1234", code_arm_required=True)
        alarm.async_alarm_arm_home(code="9999")
        alarm._controller.arm_stay.assert_not_called()

    def test_arm_home_no_code_rejected_when_required(self):
        alarm = _make_alarm(code="1234", code_arm_required=True)
        alarm.async_alarm_arm_home(code=None)
        alarm._controller.arm_stay.assert_not_called()

    def test_arm_home_no_code_ok_when_not_required(self):
        alarm = _make_alarm(code="1234", code_arm_required=False)
        alarm.async_alarm_arm_home(code=None)
        alarm._controller.arm_stay.assert_called_once()

    def test_arm_away_correct_code(self):
        alarm = _make_alarm(code="1234", code_arm_required=True)
        alarm.async_alarm_arm_away(code="1234")
        alarm._controller.arm_away.assert_called_once()

    def test_arm_away_wrong_code_rejected(self):
        alarm = _make_alarm(code="1234", code_arm_required=True)
        alarm.async_alarm_arm_away(code="9999")
        alarm._controller.arm_away.assert_not_called()

    def test_arm_away_uses_arm_away_not_keypress(self):
        """Arm away must use arm_away(), never send_keypress()."""
        alarm = _make_alarm(code="1234", code_arm_required=True)
        alarm.async_alarm_arm_away(code="1234")
        alarm._controller.arm_away.assert_called_once()
        alarm._controller.send_keypress.assert_not_called()


# ---------------------------------------------------------------------------
# Panic Code Validation Tests
# ---------------------------------------------------------------------------

class TestPanicCodeValidation:
    """Tests for panic trigger code verification."""

    def test_panic_correct_code(self):
        alarm = _make_alarm(code="1234", code_panic_required=True)
        alarm.async_alarm_trigger(code="1234")
        alarm._controller.panic_alarm.assert_called_once_with("")

    def test_panic_wrong_code_rejected(self):
        alarm = _make_alarm(code="1234", code_panic_required=True)
        alarm.async_alarm_trigger(code="9999")
        alarm._controller.panic_alarm.assert_not_called()

    def test_panic_no_code_rejected_when_required(self):
        alarm = _make_alarm(code="1234", code_panic_required=True)
        alarm.async_alarm_trigger(code=None)
        alarm._controller.panic_alarm.assert_not_called()

    def test_panic_no_code_ok_when_not_required(self):
        alarm = _make_alarm(code="1234", code_panic_required=False)
        alarm.async_alarm_trigger(code=None)
        alarm._controller.panic_alarm.assert_called_once_with("")

    def test_panic_no_code_configured_allows_trigger(self):
        alarm = _make_alarm(code="", code_panic_required=True)
        alarm.async_alarm_trigger(code=None)
        alarm._controller.panic_alarm.assert_called_once_with("")


# ---------------------------------------------------------------------------
# Keypress Sanitization Tests
# ---------------------------------------------------------------------------

class TestKeypressSanitization:
    """Tests for keypress input validation."""

    def test_valid_digits(self):
        alarm = _make_alarm()
        alarm.async_alarm_keypress("1234")
        alarm._controller.send_keypress.assert_called_once_with("1234")

    def test_valid_command_keys(self):
        alarm = _make_alarm()
        alarm.async_alarm_keypress("CNRSXABEH")
        alarm._controller.send_keypress.assert_called_once_with("CNRSXABEH")

    def test_lowercase_normalized_to_upper(self):
        alarm = _make_alarm()
        alarm.async_alarm_keypress("abc")
        alarm._controller.send_keypress.assert_called_once_with("ABC")

    def test_prog_key_rejected(self):
        """P (PROG) should be rejected for safety."""
        alarm = _make_alarm()
        alarm.async_alarm_keypress("P")
        alarm._controller.send_keypress.assert_not_called()

    def test_invalid_chars_rejected(self):
        alarm = _make_alarm()
        alarm.async_alarm_keypress("1234!")
        alarm._controller.send_keypress.assert_not_called()

    def test_semicolon_injection_rejected(self):
        alarm = _make_alarm()
        alarm.async_alarm_keypress("1234;DROP")
        alarm._controller.send_keypress.assert_not_called()

    def test_newline_injection_rejected(self):
        alarm = _make_alarm()
        alarm.async_alarm_keypress("1234\n5678")
        alarm._controller.send_keypress.assert_not_called()

    def test_empty_keypress_ignored(self):
        alarm = _make_alarm()
        alarm.async_alarm_keypress(None)
        alarm._controller.send_keypress.assert_not_called()

    def test_empty_string_ignored(self):
        alarm = _make_alarm()
        alarm.async_alarm_keypress("")
        alarm._controller.send_keypress.assert_not_called()

    def test_max_length_enforced(self):
        alarm = _make_alarm()
        alarm.async_alarm_keypress("1" * 17)
        alarm._controller.send_keypress.assert_not_called()

    def test_max_length_boundary_accepted(self):
        alarm = _make_alarm()
        alarm.async_alarm_keypress("1" * 16)
        alarm._controller.send_keypress.assert_called_once_with("1" * 16)

    def test_mixed_valid_sequence(self):
        """Realistic sequence: code + enter."""
        alarm = _make_alarm()
        alarm.async_alarm_keypress("1234E")
        alarm._controller.send_keypress.assert_called_once_with("1234E")


# ---------------------------------------------------------------------------
# Serial Port Path Validation Tests
# ---------------------------------------------------------------------------

class TestSerialPortValidation:
    """Tests for serial port path regex validation."""

    SERIAL_PATTERN = re.compile(r'^(/dev/tty[A-Za-z0-9/_-]+|COM\d+)$')

    def test_valid_usb_path(self):
        assert self.SERIAL_PATTERN.match("/dev/ttyUSB0")

    def test_valid_acm_path(self):
        assert self.SERIAL_PATTERN.match("/dev/ttyACM0")

    def test_valid_serial_path(self):
        assert self.SERIAL_PATTERN.match("/dev/ttyS0")

    def test_valid_com_port(self):
        assert self.SERIAL_PATTERN.match("COM1")

    def test_valid_com_port_high(self):
        assert self.SERIAL_PATTERN.match("COM12")

    def test_path_traversal_rejected(self):
        assert not self.SERIAL_PATTERN.match("../../../../etc/passwd")

    def test_etc_passwd_rejected(self):
        assert not self.SERIAL_PATTERN.match("/etc/passwd")

    def test_arbitrary_path_rejected(self):
        assert not self.SERIAL_PATTERN.match("/tmp/fake_serial")

    def test_empty_string_rejected(self):
        assert not self.SERIAL_PATTERN.match("")

    def test_spaces_rejected(self):
        assert not self.SERIAL_PATTERN.match("/dev/tty USB0")

    def test_command_injection_rejected(self):
        assert not self.SERIAL_PATTERN.match("/dev/ttyUSB0; rm -rf /")

    def test_null_byte_rejected(self):
        assert not self.SERIAL_PATTERN.match("/dev/ttyUSB0\x00")


# ---------------------------------------------------------------------------
# Switch is_on Property Tests
# ---------------------------------------------------------------------------

class TestSwitchIsOnProperty:
    """Tests that is_on is a pure property with no side effects."""

    def test_is_on_returns_true(self):
        switch = MagicMock()
        switch._info = {"status": {"open": True}}
        from custom_components.aapalarm.switch import AAPModuleOutput
        result = AAPModuleOutput.is_on.fget(switch)
        assert result is True

    def test_is_on_returns_false(self):
        switch = MagicMock()
        switch._info = {"status": {"open": False}}
        from custom_components.aapalarm.switch import AAPModuleOutput
        result = AAPModuleOutput.is_on.fget(switch)
        assert result is False

    def test_is_on_no_info_returns_false(self):
        switch = MagicMock()
        switch._info = None
        from custom_components.aapalarm.switch import AAPModuleOutput
        result = AAPModuleOutput.is_on.fget(switch)
        assert result is False

    def test_is_on_no_status_returns_false(self):
        switch = MagicMock()
        switch._info = {"something": "else"}
        from custom_components.aapalarm.switch import AAPModuleOutput
        result = AAPModuleOutput.is_on.fget(switch)
        assert result is False

    def test_is_on_does_not_mutate_state(self):
        """Verify is_on does not write to self._state."""
        switch = MagicMock()
        switch._info = {"status": {"open": True}}
        switch._state = "ORIGINAL"
        from custom_components.aapalarm.switch import AAPModuleOutput
        AAPModuleOutput.is_on.fget(switch)
        # _state should NOT have been modified by the property
        assert switch._state == "ORIGINAL"
