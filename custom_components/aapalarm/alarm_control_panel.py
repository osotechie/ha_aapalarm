"""Support for AAP IP / Serial Module-based alarm control panel."""

import logging

import voluptuous as vol

from homeassistant.components.alarm_control_panel import (
    DOMAIN,
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
    CodeFormat,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import (
    AREA_SCHEMA,
    CONF_AREANAME,
    CONF_CODE,
    CONF_CODE_ARM_REQUIRED,
    CONF_CODE_PANIC_REQUIRED,
    DOMAIN as AAP_DOMAIN,
    SIGNAL_AREA_UPDATE,
    SIGNAL_KEYPAD_UPDATE,
    AAPModuleDevice,
)

_LOGGER = logging.getLogger(__name__)

SERVICE_ALARM_KEYPRESS = "aap_alarm_keypress"
ATTR_KEYPRESS = "keypress"

# Valid keys on the AAP alarm keypad (excluding P/PROG for safety)
VALID_KEYPRESS_CHARS = set("0123456789ABCEHNRSX")
MAX_KEYPRESS_LENGTH = 16

ALARM_KEYPRESS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required(ATTR_KEYPRESS): cv.string,
    }
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Perform the setup for AAP IP / Serial Module alarm panels."""
    controller = hass.data[AAP_DOMAIN][entry.entry_id]
    configured_areas = entry.data.get("areas", {})

    devices = []
    for part_num in configured_areas:
        device_config_data = AREA_SCHEMA(configured_areas[part_num])
        part_num = int(part_num)  # JSON deserializes dict keys as strings
        
        # Get area state, fallback to empty dict if not available
        # Try letter key first (controller uses 'A'/'B'), then integer, then string
        area_letter = {1: 'A', 2: 'B'}.get(part_num)
        area_state = getattr(controller, 'area_state', {})
        default_info = {
            "status": {
                "alarm": False,
                "armed": False, 
                "stay_armed": False,
                "exit_delay": False,
                "stay_exit_delay": False,
                "disarmed": True
            }
        }
        if area_letter and area_letter in area_state:
            area_info = area_state[area_letter]
        elif part_num in area_state:
            area_info = area_state[part_num]
        else:
            area_info = default_info
        
        device = AAPModuleAlarm(
            hass,
            entry,
            part_num,
            device_config_data[CONF_AREANAME],
            device_config_data[CONF_CODE],
            device_config_data[CONF_CODE_ARM_REQUIRED],
            device_config_data.get(CONF_CODE_PANIC_REQUIRED, True),
            area_info,
            controller,
        )
        devices.append(device)

    async_add_entities(devices)

    @callback
    def alarm_keypress_handler(service):
        """Map services to methods on Alarm."""
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        keypress = service.data.get(ATTR_KEYPRESS)

        target_devices = [
            device for device in devices if device.entity_id in entity_ids
        ]

        for device in target_devices:
            device.async_alarm_keypress(keypress)

    hass.services.async_register(
        DOMAIN,
        SERVICE_ALARM_KEYPRESS,
        alarm_keypress_handler,
        schema=ALARM_KEYPRESS_SCHEMA,
    )

    return True


class AAPModuleAlarm(AAPModuleDevice, AlarmControlPanelEntity):
    """Representation of an AAP IP / Serial Module-based alarm panel."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        area_number,
        alarm_name,
        code,
        code_arm_required,
        code_panic_required,
        info,
        controller,
    ) -> None:
        """Initialize the alarm panel."""
        self._area_number = area_number  # Keep original area number for comparison
        self._code = code
        self._code_arm_required = code_arm_required
        self._code_panic_required = code_panic_required

        _LOGGER.debug("Setting up alarm: %s for area number: %s", alarm_name, area_number)
        super().__init__(entry, alarm_name, info, controller, area_number, alarm_name, "areas")

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_KEYPAD_UPDATE, self._update_callback)
        )
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_AREA_UPDATE, self._update_callback)
        )
        
        # Force an initial state update
        _LOGGER.debug("Alarm panel added to hass, forcing initial state update for area %s", self._area_number)
        self.async_schedule_update_ha_state()

    # Mapping between area letters (from controller) and area numbers (from config)
    AREA_LETTER_TO_NUMBER = {'A': 1, 'B': 2}
    AREA_NUMBER_TO_LETTER = {1: 'A', 2: 'B'}

    @callback
    def _update_callback(self, area):
        """Update Home Assistant state, if needed."""
        _LOGGER.debug("Area update callback called for area %s, target area: %s", area, self._area_number)
        
        try:
            # Determine if this callback is for our area
            if area is None:
                should_update = True
            else:
                # Normalize the incoming area identifier to an integer for comparison
                if isinstance(area, str) and area in self.AREA_LETTER_TO_NUMBER:
                    incoming_area_num = self.AREA_LETTER_TO_NUMBER[area]
                else:
                    try:
                        incoming_area_num = int(area)
                    except (ValueError, TypeError):
                        incoming_area_num = None
                should_update = incoming_area_num == self._area_number
            
            if should_update:
                # Try multiple key formats since the controller may use letters or integers
                area_letter = self.AREA_NUMBER_TO_LETTER.get(self._area_number)
                area_state = getattr(self._controller, 'area_state', {})
                if area_letter and area_letter in area_state:
                    self._info = area_state[area_letter]
                    _LOGGER.debug("Updated area %s state (letter key)", self._area_number)
                elif self._area_number in area_state:
                    self._info = area_state[self._area_number]
                    _LOGGER.debug("Updated area %s state (int key)", self._area_number)
                elif str(self._area_number) in area_state:
                    self._info = area_state[str(self._area_number)]
                    _LOGGER.debug("Updated area %s state (str key)", self._area_number)
                else:
                    _LOGGER.warning("No area state data available for area %s (tried keys: %s, %s, %s)", self._area_number, area_letter, self._area_number, str(self._area_number))
                
                _LOGGER.debug("Scheduling state update for area %s", self._area_number)
                self.async_schedule_update_ha_state()
        except (ValueError, TypeError) as e:
            _LOGGER.error("Error processing area update callback for area %s: %s", self._area_number, e)

    # """Required to show up Keypad on alarm panel"""

    @property
    def code_format(self) -> CodeFormat | None:
        """Regex for code format or None if no code is required."""
        if self._code != "":
            return None
        return CodeFormat.NUMBER

    @property
    def code_arm_required(self) -> bool:
        """Whether the code is required for arm actions."""
        return self._code_arm_required

    @property
    def alarm_state(self):
        """Return the state of the device."""
        _LOGGER.debug("Checking alarm state for area %s, _info: %s", self._area_number, self._info)
        
        if not self._info or "status" not in self._info:
            _LOGGER.debug("No info or status available for area %s", self._area_number)
            return STATE_UNKNOWN

        status = self._info["status"]
        _LOGGER.debug("Area %s status: %s", self._area_number, status)
        
        if status.get("alarm", False):
            state = AlarmControlPanelState.TRIGGERED
        elif status.get("armed", False):
            state = AlarmControlPanelState.ARMED_AWAY
        elif status.get("stay_armed", False):
            state = AlarmControlPanelState.ARMED_HOME
        elif (
            status.get("exit_delay", False)
            or status.get("stay_exit_delay", False)
        ):
            state = AlarmControlPanelState.PENDING
        else:
            # Default to disarmed if no other state is active
            state = AlarmControlPanelState.DISARMED
            
        _LOGGER.debug("Area %s determined state: %s", self._area_number, state)
        return state

    @property
    def available(self):
        """Return if entity is available."""
        return self._info is not None and "status" in self._info

    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""
        # During exit delay, allow disarm without code
        if self.alarm_state == AlarmControlPanelState.PENDING:
            self._controller.disarm(str(self._code))
            return
        # When armed, require valid code
        if not self._code:
            self._controller.disarm("")
            return
        if code is None or str(code) != str(self._code):
            _LOGGER.warning("Invalid code provided for disarm on area %s", self._area_number)
            return
        self._controller.disarm(str(self._code))

    async def async_alarm_arm_home(self, code=None):
        """Send arm home command."""
        if self._code_arm_required and self._code:
            if code is None or str(code) != str(self._code):
                _LOGGER.warning("Invalid code provided for arm home on area %s", self._area_number)
                return
        self._controller.arm_stay()

    async def async_alarm_arm_away(self, code=None):
        """Send arm away command."""
        if self._code_arm_required and self._code:
            if code is None or str(code) != str(self._code):
                _LOGGER.warning("Invalid code provided for arm away on area %s", self._area_number)
                return
        self._controller.arm_away()

    async def async_alarm_trigger(self, code=None):
        """Alarm trigger command. Will be used to trigger a panic alarm."""
        if self._code_panic_required and self._code:
            if code is None or str(code) != str(self._code):
                _LOGGER.warning("Invalid code provided for panic trigger on area %s", self._area_number)
                return
        self._controller.panic_alarm("")

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self._info and "status" in self._info:
            return self._info["status"]
        return {}

    @callback
    def async_alarm_keypress(self, keypress=None):
        """Send custom keypress."""
        if not keypress:
            return
        keypress = str(keypress).upper()
        if len(keypress) > MAX_KEYPRESS_LENGTH:
            _LOGGER.warning("Keypress rejected: exceeds max length of %s", MAX_KEYPRESS_LENGTH)
            return
        if not set(keypress).issubset(VALID_KEYPRESS_CHARS):
            _LOGGER.warning("Keypress rejected: contains invalid characters")
            return
        self._controller.send_keypress(keypress)

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return (
            AlarmControlPanelEntityFeature.ARM_HOME
            | AlarmControlPanelEntityFeature.ARM_AWAY
            | AlarmControlPanelEntityFeature.TRIGGER
        )