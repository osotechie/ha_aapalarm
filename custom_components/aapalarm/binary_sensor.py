"""Support for AAP Alarm IP / Serial Module."""

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import (
    CONF_ZONENAME,
    CONF_ZONETYPE,
    DOMAIN,
    SIGNAL_ZONE_UPDATE,
    ZONE_SCHEMA,
    AAPModuleDevice,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the AAP binary sensor devices from a config entry."""
    controller = hass.data[DOMAIN][entry.entry_id]
    configured_zones = entry.data.get("zones", {})

    devices = []
    for zone_num in configured_zones:
        device_config_data = ZONE_SCHEMA(configured_zones[zone_num])
        
        # Get zone state, fallback to empty dict if not available
        zone_info = getattr(controller, 'zone_state', {}).get(zone_num, {"status": {"open": False}})
        
        device = AAPModuleBinarySensor(
            hass,
            entry,
            zone_num,
            device_config_data[CONF_ZONENAME],
            device_config_data[CONF_ZONETYPE],
            zone_info,
            controller,
        )
        devices.append(device)

    async_add_entities(devices)


class AAPModuleBinarySensor(AAPModuleDevice, BinarySensorEntity):
    """Representation of an AAP IP / Serial Module binary sensor."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, zone_number, zone_name, zone_type, info, controller
    ) -> None:
        """Initialize the binary_sensor."""
        self._zone_type = zone_type
        self._zone_number = zone_number
        self._entry = entry

        _LOGGER.debug("Setting up zone: %s", zone_name)
        super().__init__(entry, zone_name, info, controller, None, None, "zones")

    async def async_added_to_hass(self):
        """Register callbacks."""
        _LOGGER.debug("Adding zone %s (%s) to Home Assistant", self._zone_number, self._name)
        async_dispatcher_connect(self.hass, SIGNAL_ZONE_UPDATE, self._update_callback)
        
        # Force an initial state update
        if hasattr(self._controller, 'zone_state') and self._zone_number in self._controller.zone_state:
            self._info = self._controller.zone_state[self._zone_number]
            _LOGGER.debug("Initial zone %s state: %s", self._zone_number, self._info)
            self.async_schedule_update_ha_state()

    @property
    def is_on(self):
        """Return true if sensor is on."""
        if self._info and "status" in self._info and "open" in self._info["status"]:
            return self._info["status"]["open"]
        return False

    @property
    def available(self):
        """Return if entity is available."""
        return self._info is not None and "status" in self._info

    @property
    def device_class(self):
        """Return the class of this sensor, from DEVICE_CLASSES."""
        return self._zone_type

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self._info and "status" in self._info:
            return self._info["status"]
        return {}

    @callback
    def _update_callback(self, zone):
        """Update the zone's state, if needed."""
        _LOGGER.debug("Zone update callback triggered for zone %s, target zone %s", zone, self._zone_number)
        
        # Handle different data types for zone comparison - zone comes as string from controller
        try:
            # Convert both to int for comparison, or if zone is None, update all
            if zone is None or int(zone) == int(self._zone_number):
                # Update the zone info from the controller using integer key
                zone_key = int(self._zone_number)  # Ensure we use integer key
                if hasattr(self._controller, 'zone_state') and zone_key in self._controller.zone_state:
                    self._info = self._controller.zone_state[zone_key]
                    _LOGGER.debug("Updated zone %s state", self._zone_number)
                else:
                    _LOGGER.warning("No zone state data available for zone %s", self._zone_number)
                
                self.async_schedule_update_ha_state()
        except (ValueError, TypeError) as e:
            _LOGGER.error("Error processing zone update callback for zone %s: %s", self._zone_number, e)