"""Support for AAP IP /Serial Module sensors (shows panel info)."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import ConfigType

from . import (
    CONF_OUTPUTNAME,
    DATA_AAP,
    OUTPUT_SCHEMA,
    SIGNAL_OUTPUT_UPDATE,
    AAPModuleDevice,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant, config: ConfigType, async_add_entities, discovery_info=None
) -> None:
    """Perform the setup for AAP IP / Serial Module Switch devices."""
    configured_outputs = discovery_info["outputs"]

    _LOGGER.debug(str(configured_outputs))

    devices = []
    if configured_outputs is not None:
        for output_num in configured_outputs:
            device_config_data = OUTPUT_SCHEMA(configured_outputs[output_num])
            device = AAPModuleOutput(
                hass,
                output_num,
                device_config_data[CONF_OUTPUTNAME],
                hass.data[DATA_AAP].output_state[output_num],
                hass.data[DATA_AAP],
            )
            devices.append(device)

    async_add_entities(devices)


class AAPModuleOutput(AAPModuleDevice, SwitchEntity):
    """Representation of an AAP IP / Serial Module Output Switch."""

    def __init__(
        self, hass: HomeAssistant, output_number, output_name, info, controller
    ) -> None:
        """Initialize the switch."""
        self._output_number = output_number
        _LOGGER.debug("Setting up output switch for system")
        super().__init__(output_name, info, controller)
        self._name = "Alarm Output: " + output_name
        self._state = STATE_OFF

    async def async_added_to_hass(self):
        """Register callbacks."""
        async_dispatcher_connect(self.hass, SIGNAL_OUTPUT_UPDATE, self._update_callback)

    @property
    def name(self):
        """Return name of the output."""
        return self._name

    @property
    def is_on(self):
        """Return true if device is on."""
        self._state = self._info["status"]["open"]
        _LOGGER.debug("Is_on=%s", str(self._state))
        return self._state

    async def async_turn_on(self, **kwargs):
        """Turn on the output."""
        self.hass.data[DATA_AAP].command_output(str(self._output_number))
        self._state = STATE_ON
        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn off the output."""
        self.hass.data[DATA_AAP].command_output(str(self._output_number))
        self._state = STATE_OFF
        self.async_schedule_update_ha_state()

    @callback
    def _update_callback(self, output):
        """Update the output state in HA, if needed."""
        if output is None or int(output) == int(self._output_number):
            self.async_schedule_update_ha_state()
            _LOGGER.debug("Update output %s", str(output))