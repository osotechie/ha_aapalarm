"""AAP IP / Serial Module init file."""

import asyncio
import logging

from pyaapalarmmodule import AAPAlarmPanel
import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_TIMEOUT, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo


from .const import (
    # CONSTANTS for Integration
    DOMAIN,
    DATA_AAP,

    # CONSTANTS for Connection Type
    CONF_AAP_CONNECTIONTYPE,
    CONF_AAP_PORT,
    CONF_AAP_KEEPALIVE,

    # CONSTATNS for Areas
    CONF_AREAS,
    CONF_AREANAME,
    CONF_CODE,
    CONF_CODE_ARM_REQUIRED,

    # CONSTANTS for Zones
    CONF_ZONENUM,
    CONF_ZONES,
    CONF_ZONENAME,
    CONF_ZONETYPE,

    # CONSTATNS for Outputs
    CONF_OUTPUTNUM,
    CONF_OUTPUTS,
    CONF_OUTPUTNAME,

    # DEFAULT VALUES
    DEFAULT_PORT,
    DEFAULT_KEEPALIVE,
    DEFAULT_ZONETYPE,
    DEFAULT_TIMEOUT, 

    # HA Constants
    SIGNAL_ZONE_UPDATE,
    SIGNAL_AREA_UPDATE,
    SIGNAL_SYSTEM_UPDATE,
    SIGNAL_OUTPUT_UPDATE,
    SIGNAL_KEYPAD_UPDATE,
)

_LOGGER = logging.getLogger(__name__)


OUTPUT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_OUTPUTNAME): cv.string,
    }
)

ZONE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ZONENAME): cv.string,
        vol.Optional(CONF_ZONETYPE, default=DEFAULT_ZONETYPE): cv.string,
    }
)

AREA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_AREANAME): cv.string,
        vol.Optional(CONF_CODE, default=""): cv.string,
        vol.Optional(CONF_CODE_ARM_REQUIRED, default=True): cv.boolean,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_AAP_CONNECTIONTYPE): cv.string,
                vol.Optional(CONF_HOST): cv.string,
                vol.Optional(CONF_ZONES): {vol.Coerce(int): ZONE_SCHEMA},
                vol.Optional(CONF_AREAS): {vol.Coerce(int): AREA_SCHEMA},
                vol.Optional(CONF_OUTPUTS): {vol.Coerce(int): OUTPUT_SCHEMA},
                vol.Optional(CONF_AAP_PORT, default=DEFAULT_PORT): cv.string,
                vol.Optional(CONF_AAP_KEEPALIVE, default=DEFAULT_KEEPALIVE): vol.All(
                    vol.Coerce(int), vol.Range(min=15)
                ),
                vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.Coerce(int),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the AAP Alarm component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AAP Alarm from a config entry."""
    conf = entry.data
    connectiontype = conf[CONF_AAP_CONNECTIONTYPE]
    host = conf[CONF_HOST]
    code = "0000"
    port = conf[CONF_AAP_PORT]
    keep_alive = conf[CONF_AAP_KEEPALIVE]
    zones = conf[CONF_ZONES]
    areas = conf[CONF_AREAS]
    outputs = conf[CONF_OUTPUTS]
    connection_timeout = conf[CONF_TIMEOUT]
    sync_connect = asyncio.Future()

    controller = AAPAlarmPanel(
        connectiontype,
        host,
        port,
        code,
        keep_alive,
        hass.loop,
        connection_timeout,
    )

    hass.data[DATA_AAP] = controller

    @callback
    def connection_fail_callback(data):
        """Network failure callback."""
        _LOGGER.error("Could not establish a connection with the AAP IP / Serial Module")
        if not sync_connect.done():
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_aapalarm)
            sync_connect.set_result(True)

    @callback
    def connected_callback(data):
        """Handle a successful connection."""
        _LOGGER.info("Established a connection with the AAP IP / Serial Module")
        if not sync_connect.done():
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_aapalarm)
            sync_connect.set_result(True)

    @callback
    def zones_updated_callback(data):
        """Handle zone updates."""
        _LOGGER.debug("AAP IP / Serial Module sent a zone update event. Updating zones")
        async_dispatcher_send(hass, SIGNAL_ZONE_UPDATE, data)

    @callback
    def areas_updated_callback(data):
        """Handle area changes thrown by AAP (including alarms)."""
        _LOGGER.debug("The AAP IP / Serial Module sent an area update event. Updating areas")
        async_dispatcher_send(hass, SIGNAL_AREA_UPDATE, data)

    @callback
    def system_updated_callback(data):
        # Handle system updates.
        _LOGGER.debug("AAP IP / Serial Module sent a system update event. Updating system")
        async_dispatcher_send(hass, SIGNAL_SYSTEM_UPDATE, data)

    @callback
    def output_updated_callback(data):
        """Handle output updates."""
        _LOGGER.debug("AAP IP / Serial Module sent an output update event. Updating output")
        async_dispatcher_send(hass, SIGNAL_OUTPUT_UPDATE, data)

    @callback
    def stop_aapalarm(event):
        """Shutdown AAP IP / Serial Module connection and thread on exit."""
        _LOGGER.info("Shutting down AAP Alarm")
        controller.stop()

    controller.callback_zone_state_change = zones_updated_callback
    controller.callback_area_state_change = areas_updated_callback
    controller.callback_system_state_change = system_updated_callback
    controller.callback_output_state_change = output_updated_callback

    controller.callback_connected = connected_callback
    controller.callback_login_timeout = connection_fail_callback

    _LOGGER.info("Start AAP Alarm")
    controller.start()

    result = await sync_connect
    if not result:
        return False

    # Load sub-components for AAP IP / Serial Module
    if areas:
        hass.async_create_task(
            async_load_platform(
                hass,
                "alarm_control_panel",
                "aapalarm",
                {CONF_AREAS: areas},
                entry,
            )
        )
        hass.async_create_task(
            async_load_platform(
                hass,
                "sensor",
                "aapalarm",
                {CONF_AREAS: areas},
                entry,
            )
        )

    if zones:
        hass.async_create_task(
            async_load_platform(
                hass,
                "binary_sensor",
                "aapalarm",
                {CONF_ZONES: zones},
                entry,
            )
        )

    if outputs:
        hass.async_create_task(
            async_load_platform(
                hass,
                "switch",
                "aapalarm",
                {CONF_OUTPUTS: outputs},
                entry,
            )
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    controller = hass.data[DATA_AAP]
    controller.stop()
    hass.data.pop(DATA_AAP)

    return True


class AAPModuleDevice(Entity):
    """Representation of an AAP IP / Serial Module."""

    def __init__(self, name, info, controller) -> None:
        """Initialize the device."""
        self._controller = controller
        self._info = info
        self._name = name

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self):
        """No polling needed."""
        return False
    
    @property
    def unique_id(self):
        """Return a unique ID for the module device."""
        return f"aapalarm_module_{self._name}"

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