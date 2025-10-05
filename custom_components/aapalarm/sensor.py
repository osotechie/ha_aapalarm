"""Support for AAP IP / Serial Module sensors (shows panel info)."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from . import DOMAIN, SIGNAL_SYSTEM_UPDATE, AAPModuleDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Perform the setup for AAP IP / Serial Module Sensor devices."""
    controller = hass.data[DOMAIN][entry.entry_id]
    
    devices = []
    
    # Create individual system status entities
    system_sensors = [
        ("mains", "Mains Power", "mdi:power-plug", "connectivity"),
        ("battery", "Main Battery", "mdi:battery", "battery"),
        ("tamper", "Tamper", "mdi:shield-alert", "problem"),
        ("line", "Phone Line", "mdi:phone", "connectivity"),
        ("dialler", "Dialler", "mdi:phone-dial", "connectivity"),
        ("ready", "System Ready", "mdi:shield-check", None),
        ("fuse", "Fuse Status", "mdi:fuse", "problem"),
        ("zonebattery", "Zone Battery", "mdi:battery-outline", "battery"),
        ("pendantbattery", "Pendant Battery", "mdi:battery-bluetooth", "battery"),
        ("codetamper", "Code Tamper", "mdi:lock-alert", "problem"),
    ]
    
    for sensor_key, sensor_name, icon, device_class in system_sensors:
        device = AAPModuleSystemSensor(
            hass,
            entry,
            sensor_key,
            sensor_name,
            icon,
            device_class,
            controller.system_state,
            controller,
        )
        devices.append(device)
    
    async_add_entities(devices)


class AAPModuleSystemSensor(AAPModuleDevice, Entity):
    """Representation of an individual AAP IP / Serial Module system sensor."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, sensor_key: str, sensor_name: str, icon: str, device_class: str | None, info, controller) -> None:
        """Initialize the sensor."""
        self._sensor_key = sensor_key
        self._icon = icon
        self._device_class = device_class
        _LOGGER.debug("Setting up system sensor: %s", sensor_name)
        super().__init__(entry, sensor_name, info, controller, None, None, "system")

    async def async_added_to_hass(self):
        """Register callbacks."""
        _LOGGER.debug("Adding system sensor %s (%s) to Home Assistant", self._sensor_key, self._name)
        async_dispatcher_connect(self.hass, SIGNAL_SYSTEM_UPDATE, self._update_callback)
        
        # Force an initial state update
        if hasattr(self._controller, 'system_state'):
            self._info = self._controller.system_state
            _LOGGER.debug("Initial system sensor %s state: %s", self._sensor_key, self._info)
            self.async_schedule_update_ha_state()

    @property
    def icon(self):
        """Return the icon if any."""
        return self._icon

    @property
    def device_class(self):
        """Return the device class if any."""
        return self._device_class

    @property
    def state(self):
        """Return the state of this specific sensor."""
        if self._sensor_key in self._info.get("status", {}):
            return self._info["status"][self._sensor_key]
        return None

    @property
    def available(self):
        """Return if entity is available."""
        return self._info is not None and "status" in self._info

    @callback
    def _update_callback(self, system):
        """Update the sensor state in HA, if needed."""
        # Update the system info from the controller
        if hasattr(self._controller, 'system_state'):
            self._info = self._controller.system_state
            _LOGGER.debug("Updated system sensor %s state", self._sensor_key)
        else:
            _LOGGER.warning("No system state data available for sensor %s", self._sensor_key)
        
        self.async_schedule_update_ha_state()