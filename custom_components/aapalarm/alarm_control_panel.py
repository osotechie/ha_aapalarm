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
from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.device_registry import DeviceInfo

from . import (
    AREA_SCHEMA,
    CONF_AREANAME,
    CONF_CODE,
    CONF_CODE_ARM_REQUIRED,
    DATA_AAP,
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


async def async_setup_platform(
    hass: HomeAssistant, config: ConfigType, async_add_entities, discovery_info=None
):
    """Perform the setup for AAP IP / Serial Module alarm panels."""
    configured_areas = discovery_info["areas"]

    devices = []
    for part_num in configured_areas:
        device_config_data = AREA_SCHEMA(configured_areas[part_num])
        device = AAPModuleAlarm(
            hass,
            part_num,
            device_config_data[CONF_AREANAME],
            device_config_data[CONF_CODE],
            device_config_data[CONF_CODE_ARM_REQUIRED],
            hass.data[DATA_AAP].area_state[part_num],
            hass.data[DATA_AAP],
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
        area_number,
        alarm_name,
        code,
        code_arm_required,
        info,
        controller,
    ) -> None:
        """Initialize the alarm panel."""
        if area_number == 1:
            self._area_number = "A"
        else:
            self._area_number = "B"
        self._code = code
        self._code_arm_required = code_arm_required
        

        _LOGGER.debug("Setting up alarm: %s", alarm_name)
        super().__init__(alarm_name, info, controller)

    async def async_added_to_hass(self):
        """Register callbacks."""
        async_dispatcher_connect(self.hass, SIGNAL_KEYPAD_UPDATE, self._update_callback)
        async_dispatcher_connect(self.hass, SIGNAL_AREA_UPDATE, self._update_callback)

    @callback
    def _update_callback(self, area):
        """Update Home Assistant state, if needed."""
        if area is None or area == self._area_number:
            self.async_schedule_update_ha_state()

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
        state = STATE_UNKNOWN

        if self._info["status"]["alarm"]:
            state = AlarmControlPanelState.TRIGGERED
        elif self._info["status"]["armed"]:
            state = AlarmControlPanelState.ARMED_AWAY
        elif self._info["status"]["stay_armed"]:
            state = AlarmControlPanelState.ARMED_HOME
        elif (
            self._info["status"]["exit_delay"]
            or self._info["status"]["stay_exit_delay"]
        ):
            state = AlarmControlPanelState.PENDING
        elif self._info["status"]["disarmed"]:
            state = AlarmControlPanelState.DISARMED
        return state

    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""
        if code:
            self.hass.data[DATA_AAP].disarm(str(code))
        else:
            self.hass.data[DATA_AAP].disarm(str(self._code))

    async def async_alarm_arm_home(self, code=None):
        """Send arm home command."""
        self.hass.data[DATA_AAP].arm_stay()

    async def async_alarm_arm_away(self, code=None):
        """Send arm away command."""
        if code:
            self.hass.data[DATA_AAP].send_keypress(str(code))
        else:
            self.hass.data[DATA_AAP].arm_away()

    async def async_alarm_trigger(self, code=None):
        """Alarm trigger command. Will be used to trigger a panic alarm."""
        self.hass.data[DATA_AAP].panic_alarm("")

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._info["status"]

    @property
    def unique_id(self):
        """Return a unique ID for the module device."""
        return f"aapalarm_alamrpanel_{self._name}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                "aapalarm",
                f"{self.name}",
            },
            name="Elite S Alarm System",
            manufacturer="Arrowhead Alarms",
            model="IP / Serial Module",
        )

    @callback
    def async_alarm_keypress(self, keypress=None):
        """Send custom keypress."""
        if keypress:
            self.hass.data[DATA_AAP].send_keypress(str(keypress))

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return (
            AlarmControlPanelEntityFeature.ARM_HOME
            | AlarmControlPanelEntityFeature.ARM_AWAY
            | AlarmControlPanelEntityFeature.TRIGGER
        )