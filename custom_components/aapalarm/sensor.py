"""Support for AAP IP / Serial Module sensors (shows panel info)."""

import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.device_registry import DeviceInfo

from . import DOMAIN, DATA_AAP, SIGNAL_SYSTEM_UPDATE, AAPModuleDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant, config: ConfigType, async_add_entities, discovery_info=None
) -> None:
    """Perform the setup for AAP IP / Serial Module  Sensor devices."""
    devices = []
    device = AAPModuleSensor(
        hass,
        hass.data[DATA_AAP].system_state,
        hass.data[DATA_AAP],
    )
    devices.append(device)
    async_add_entities(devices)


class AAPModuleSensor(AAPModuleDevice, Entity):
    """Representation of an AAP IP / Serial Module keypad."""

    def __init__(self, hass: HomeAssistant, info, controller) -> None:
        """Initialize the sensor."""
        self._icon = "mdi:list-status"
        _LOGGER.debug("Setting up sensor for system")
        super().__init__("Alarm System Status", info, controller)

    async def async_added_to_hass(self):
        """Register callbacks."""
        async_dispatcher_connect(self.hass, SIGNAL_SYSTEM_UPDATE, self._update_callback)

    @property
    def icon(self):
        """Return the icon if any."""
        return self._icon

    @property
    def state(self):
        """Return the overall state."""
        return self._info["status"]["mains"]

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._info["status"]

    @property
    def unique_id(self):
        """Return a unique ID for the module device."""
        return f"aapalarm_sensor_{self._name}"

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
    def _update_callback(self, system):
        """Update the partition state in HA, if needed."""
        self.async_schedule_update_ha_state()