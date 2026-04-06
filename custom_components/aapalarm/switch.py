"""Support for AAP IP /Serial Module sensors (shows panel info)."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import (
    CONF_OUTPUTNAME,
    DOMAIN,
    OUTPUT_SCHEMA,
    SIGNAL_OUTPUT_UPDATE,
    AAPModuleDevice,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Perform the setup for AAP IP / Serial Module Switch devices."""
    controller = hass.data[DOMAIN][entry.entry_id]
    configured_outputs = entry.data.get("outputs", {})

    _LOGGER.debug(str(configured_outputs))

    devices = []
    if configured_outputs is not None:
        for output_num in configured_outputs:
            device_config_data = OUTPUT_SCHEMA(configured_outputs[output_num])
            
            # Get output state, fallback to empty dict if not available  
            output_info = getattr(controller, 'output_state', {}).get(output_num, {"status": {"open": False}})
            
            device = AAPModuleOutput(
                hass,
                entry,
                output_num,
                device_config_data[CONF_OUTPUTNAME],
                output_info,
                controller,
            )
            devices.append(device)

    async_add_entities(devices)


class AAPModuleOutput(AAPModuleDevice, SwitchEntity):
    """Representation of an AAP IP / Serial Module Output Switch."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, output_number, output_name, info, controller
    ) -> None:
        """Initialize the switch."""
        self._output_number = output_number
        _LOGGER.debug("Setting up output switch for system")
        super().__init__(entry, output_name, info, controller, None, None, "outputs")
        self._name = output_name
        self._state = STATE_OFF

    async def async_added_to_hass(self):
        """Register callbacks."""
        _LOGGER.debug("Adding output %s (%s) to Home Assistant", self._output_number, self._name)
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_OUTPUT_UPDATE, self._update_callback)
        )
        
        # Force an initial state update
        if hasattr(self._controller, 'output_state') and self._output_number in self._controller.output_state:
            self._info = self._controller.output_state[self._output_number]
            _LOGGER.debug("Initial output %s state: %s", self._output_number, self._info)
            self.async_schedule_update_ha_state()

    @property
    def name(self):
        """Return name of the output."""
        return self._name

    @property
    def is_on(self):
        """Return true if device is on."""
        if self._info and "status" in self._info and "open" in self._info["status"]:
            return self._info["status"]["open"]
        return False

    @property
    def available(self):
        """Return if entity is available."""
        return self._info is not None and "status" in self._info

    async def async_turn_on(self, **kwargs):
        """Turn on the output."""
        self._controller.command_output(str(self._output_number))
        self._state = STATE_ON
        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn off the output."""
        self._controller.command_output(str(self._output_number))
        self._state = STATE_OFF
        self.async_schedule_update_ha_state()

    @callback
    def _update_callback(self, output):
        """Update the output state in HA, if needed."""
        _LOGGER.debug("Output update callback triggered for output %s, target output %s", output, self._output_number)
        
        try:
            if output is None or int(output) == int(self._output_number):
                # Update the output info from the controller using integer key
                output_key = int(self._output_number)  # Ensure we use integer key
                if hasattr(self._controller, 'output_state') and output_key in self._controller.output_state:
                    self._info = self._controller.output_state[output_key]
                    _LOGGER.debug("Updated output %s state", self._output_number)
                else:
                    _LOGGER.warning("No output state data available for output %s", self._output_number)
                
                self.async_schedule_update_ha_state()
        except (ValueError, TypeError) as e:
            _LOGGER.error("Error processing output update callback for output %s: %s", self._output_number, e)