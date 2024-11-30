"""Support for AAP Alarm IP / Serial Module."""

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.device_registry import DeviceInfo

from . import (
    DOMAIN,
    CONF_ZONENAME,
    CONF_ZONETYPE,
    DATA_AAP,
    SIGNAL_ZONE_UPDATE,
    ZONE_SCHEMA,
    AAPModuleDevice,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant, config: ConfigType, async_add_entities, discovery_info=None
) -> None:
    """Set up the AAP binary sensor devices."""
    configured_zones = discovery_info["zones"]

    devices = []
    for zone_num in configured_zones:
        device_config_data = ZONE_SCHEMA(configured_zones[zone_num])
        device = AAPModuleBinarySensor(
            hass,
            zone_num,
            device_config_data[CONF_ZONENAME],
            device_config_data[CONF_ZONETYPE],
            hass.data[DATA_AAP].zone_state[zone_num],
            hass.data[DATA_AAP],
        )
        devices.append(device)

    async_add_entities(devices)


class AAPModuleBinarySensor(AAPModuleDevice, BinarySensorEntity):
    """Representation of an AAP IP / Serial Module binary sensor."""

    def __init__(
        self, hass: HomeAssistant, zone_number, zone_name, zone_type, info, controller
    ) -> None:
        """Initialize the binary_sensor."""
        self._zone_type = zone_type
        self._zone_number = zone_number

        _LOGGER.debug("Setting up zone: %s", zone_name)
        super().__init__("Alarm " + self.device_class.title() + ": " + zone_name, info, controller)

    async def async_added_to_hass(self):
        """Register callbacks."""
        async_dispatcher_connect(self.hass, SIGNAL_ZONE_UPDATE, self._update_callback)

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._info["status"]["open"]

    @property
    def device_class(self):
        """Return the class of this sensor, from DEVICE_CLASSES."""
        return self._zone_type

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._info["status"]

    @property
    def unique_id(self):
        """Return a unique ID for the module device."""
        return f"aapalarm_zone_{self._name}"

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
    def _update_callback(self, zone):
        """Update the zone's state, if needed."""
        if zone is None or int(zone) == self._zone_number:
            self.async_schedule_update_ha_state()