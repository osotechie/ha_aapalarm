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
from homeassistant.helpers.typing import ConfigType

from . import (
    AREA_SCHEMA,
    CONF_AREANAME,
    CONF_CODE,
    CONF_CODE_ARM_REQUIRED,
    DOMAIN as AAP_DOMAIN,
    SIGNAL_AREA_UPDATE,
    SIGNAL_KEYPAD_UPDATE,
    AAPModuleDevice,
)

_LOGGER = logging.getLogger(__name__)

SERVICE_ALARM_KEYPRESS = "aap_alarm_keypress"
ATTR_KEYPRESS = "keypress"
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
        
        # Get area state, fallback to empty dict if not available
        area_info = getattr(controller, 'area_state', {}).get(part_num, {
            "status": {
                "alarm": False,
                "armed": False, 
                "stay_armed": False,
                "exit_delay": False,
                "stay_exit_delay": False,
                "disarmed": True
            }
        })
        
        device = AAPModuleAlarm(
            hass,
            entry,
            part_num,
            device_config_data[CONF_AREANAME],
            device_config_data[CONF_CODE],
            device_config_data[CONF_CODE_ARM_REQUIRED],
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
        info,
        controller,
    ) -> None:
        """Initialize the alarm panel."""
        self._area_number = area_number  # Keep original area number for comparison
        self._code = code
        self._code_arm_required = code_arm_required

        _LOGGER.debug("Setting up alarm: %s for area number: %s", alarm_name, area_number)
        super().__init__(entry, alarm_name, info, controller, area_number, alarm_name, "areas")

    async def async_added_to_hass(self):
        """Register callbacks."""
        async_dispatcher_connect(self.hass, SIGNAL_KEYPAD_UPDATE, self._update_callback)
        async_dispatcher_connect(self.hass, SIGNAL_AREA_UPDATE, self._update_callback)
        
        # Force an initial state update
        _LOGGER.debug("Alarm panel added to hass, forcing initial state update for area %s", self._area_number)
        self.async_schedule_update_ha_state()

    @callback
    def _update_callback(self, area):
        """Update Home Assistant state, if needed."""
        _LOGGER.debug("Area update callback called for area %s, target area: %s", area, self._area_number)
        
        try:
            # Convert area callback data to match entity area number
            # Callback sends 'A'/'B', entity has 1/2, so convert for comparison
            if area is None:
                should_update = True
            elif area == 'A' and self._area_number == 1:
                should_update = True
            elif area == 'B' and self._area_number == 2:
                should_update = True
            else:
                should_update = False
            
            if should_update:
                # Update the area info from the controller using integer key
                area_key = int(self._area_number)  # Ensure we use integer key
                if hasattr(self._controller, 'area_state') and area_key in self._controller.area_state:
                    self._info = self._controller.area_state[area_key]
                    _LOGGER.debug("Updated area %s state", self._area_number)
                else:
                    _LOGGER.warning("No area state data available for area %s", self._area_number)
                
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
        if code:
            self._controller.disarm(str(code))
        else:
            self._controller.disarm(str(self._code))

    async def async_alarm_arm_home(self, code=None):
        """Send arm home command."""
        self._controller.arm_stay()

    async def async_alarm_arm_away(self, code=None):
        """Send arm away command."""
        if code:
            self._controller.send_keypress(str(code))
        else:
            self._controller.arm_away()

    async def async_alarm_trigger(self, code=None):
        """Alarm trigger command. Will be used to trigger a panic alarm."""
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
        if keypress:
            self._controller.send_keypress(str(keypress))

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return (
            AlarmControlPanelEntityFeature.ARM_HOME
            | AlarmControlPanelEntityFeature.ARM_AWAY
            | AlarmControlPanelEntityFeature.TRIGGER
        )