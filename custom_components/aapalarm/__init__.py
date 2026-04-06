"""AAP IP / Serial Module init file."""

import asyncio
from collections import deque
from datetime import datetime
import json
import logging
from pathlib import Path

from pyaapalarmmodule import AAPAlarmPanel
import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_TIMEOUT, EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    DATA_AAP,
    CONF_KEEPALIVE,
    CONF_CONNECTIONTYPE,
    CONF_MESSAGE_LOG_ENABLED,
    CONF_PORT,
    CONF_AREAS,
    CONF_AREANAME,
    CONF_CODE,
    CONF_CODE_ARM_REQUIRED,
    CONF_CODE_PANIC_REQUIRED,
    CONF_ZONES,
    CONF_ZONENAME,
    CONF_ZONETYPE,
    CONF_OUTPUTS,
    CONF_OUTPUTNAME,
    DEFAULT_PORT,
    DEFAULT_KEEPALIVE,
    DEFAULT_MESSAGE_LOG_ENABLED,
    DEFAULT_ZONETYPE,
    DEFAULT_TIMEOUT,
    SIGNAL_ZONE_UPDATE,
    SIGNAL_AREA_UPDATE,
    SIGNAL_SYSTEM_UPDATE,
    SIGNAL_OUTPUT_UPDATE,
    SIGNAL_KEYPAD_UPDATE as SIGNAL_KEYPAD_UPDATE,
    SIGNAL_MESSAGE_LOG_UPDATE,
)

_LOGGER = logging.getLogger(__name__)

# Read version from manifest.json
_MANIFEST = json.loads((Path(__file__).parent / "manifest.json").read_text())
_VERSION = _MANIFEST.get("version", "unknown")

# Platforms to load
PLATFORMS: list[Platform] = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
]

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
        vol.Optional(CONF_CODE_PANIC_REQUIRED, default=True): cv.boolean,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_CONNECTIONTYPE): cv.string,
                vol.Optional(CONF_HOST): cv.string,
                vol.Optional(CONF_ZONES): {vol.Coerce(int): ZONE_SCHEMA},
                vol.Optional(CONF_AREAS): {vol.Coerce(int): AREA_SCHEMA},
                vol.Optional(CONF_OUTPUTS): {vol.Coerce(int): OUTPUT_SCHEMA},
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.string,
                vol.Optional(CONF_KEEPALIVE, default=DEFAULT_KEEPALIVE): vol.All(
                    vol.Coerce(int), vol.Range(min=15)
                ),
                vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.Coerce(int),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up for AAP IP / Serial Module (YAML configuration)."""

    # Initialize data store
    hass.data.setdefault(DOMAIN, {})

    conf = config.get(DOMAIN)
    if conf is None:
        # No YAML configuration found, but this is OK if using config flow
        _LOGGER.debug("No YAML configuration found for domain %s, expecting config entries", DOMAIN)
        return True
    
    connectiontype = conf.get(CONF_CONNECTIONTYPE)
    host = conf.get(CONF_HOST)
    port = conf.get(CONF_PORT)
    keep_alive = conf.get(CONF_KEEPALIVE)
    zones = conf.get(CONF_ZONES)
    areas = conf.get(CONF_AREAS)
    outputs = conf.get(CONF_OUTPUTS)
    connection_timeout = conf.get(CONF_TIMEOUT)
    sync_connect = asyncio.Future()
    
    _LOGGER.info("Setting up AAP Alarm Module integration")
    _LOGGER.debug("Connection Type: %s", connectiontype)
    _LOGGER.debug("Host: %s", host)
    _LOGGER.debug("Port: %s", port)
    _LOGGER.debug("Keep Alive: %s", keep_alive)
    _LOGGER.debug("Connection Timeout: %s", connection_timeout)  

    controller = AAPAlarmPanel(
        connectiontype,
        host,
        port,
        "",
        keep_alive,
        asyncio.get_event_loop(),
        connection_timeout,
    )

    hass.data[DATA_AAP] = controller

    # Message log buffer for last 5 raw messages (if enabled)
    message_log_enabled = conf.get(CONF_MESSAGE_LOG_ENABLED, DEFAULT_MESSAGE_LOG_ENABLED)
    if message_log_enabled:
        message_log = deque(maxlen=5)
        hass.data[f"{DATA_AAP}_message_log"] = message_log

        def _log_raw_message(raw_line):
            """Record a raw message to the log buffer."""
            message_log.append({
                "timestamp": datetime.now().isoformat(),
                "raw": raw_line,
            })
            async_dispatcher_send(hass, SIGNAL_MESSAGE_LOG_UPDATE, None)

        def _wrap_process_line(controller_ref):
            """Wrap the client's process_line to capture raw data."""
            original = controller_ref._client.process_line

            def wrapped_process_line(line):
                _log_raw_message(line)
                return original(line)

            controller_ref._client.process_line = wrapped_process_line

    @callback
    def connection_fail_callback(data):
        """Network failure callback."""
        _LOGGER.error("Could not establish a connection with the AAP IP / Serial Module")
        if not sync_connect.done():
            sync_connect.set_result(False)

    @callback
    def connected_callback(data):
        """Handle a successful connection."""
        _LOGGER.info("Established a connection with the AAP IP / Serial Module")
        if message_log_enabled and hasattr(controller, '_client') and controller._client:
            _wrap_process_line(controller)
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

    try:
        result = await asyncio.wait_for(sync_connect, timeout=connection_timeout)
    except asyncio.TimeoutError:
        _LOGGER.error("Timed out connecting to AAP Alarm Module")
        controller.stop()
        return False
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
                config,
            )
        )
        hass.async_create_task(
            async_load_platform(
                hass,
                "sensor",
                "aapalarm",
                {CONF_AREAS: areas},
                config,
            )
        )

    if zones:
        hass.async_create_task(
            async_load_platform(
                hass,
                "binary_sensor",
                "aapalarm",
                {CONF_ZONES: zones},
                config,
            )
        )

    if outputs:
        hass.async_create_task(
            async_load_platform(
                hass,
                "switch",
                "aapalarm",
                {CONF_OUTPUTS: outputs},
                config,
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AAP Alarm from a config entry (GUI setup)."""
    
    # Initialize data store
    hass.data.setdefault(DOMAIN, {})
    
    # Get configuration data from the config entry
    conf = entry.data
    
    connectiontype = conf.get(CONF_CONNECTIONTYPE)
    host = conf.get(CONF_HOST)
    port = conf.get(CONF_PORT)
    keep_alive = conf.get(CONF_KEEPALIVE)
    connection_timeout = conf.get(CONF_TIMEOUT)
    sync_connect = asyncio.Future()
    
    _LOGGER.info("Setting up AAP Alarm Module integration via config entry")
    _LOGGER.debug("Connection Type: %s", connectiontype)
    _LOGGER.debug("Host: %s", host)
    _LOGGER.debug("Port: %s", port)
    _LOGGER.debug("Keep Alive: %s", keep_alive)
    _LOGGER.debug("Connection Timeout: %s", connection_timeout)  

    controller = AAPAlarmPanel(
        connectiontype,
        host,
        port,
        "",
        keep_alive,
        asyncio.get_event_loop(),
        connection_timeout,
    )

    hass.data[DOMAIN][entry.entry_id] = controller

    # Message log buffer for last 5 raw messages (if enabled)
    message_log_enabled = conf.get(CONF_MESSAGE_LOG_ENABLED, DEFAULT_MESSAGE_LOG_ENABLED)
    if message_log_enabled:
        message_log = deque(maxlen=5)
        hass.data[DOMAIN][f"{entry.entry_id}_message_log"] = message_log

        def _log_raw_message(raw_line):
            """Record a raw message to the log buffer."""
            message_log.append({
                "timestamp": datetime.now().isoformat(),
                "raw": raw_line,
            })
            async_dispatcher_send(hass, SIGNAL_MESSAGE_LOG_UPDATE, None)

        def _wrap_process_line(controller_ref):
            """Wrap the client's process_line to capture raw data."""
            original = controller_ref._client.process_line

            def wrapped_process_line(line):
                _log_raw_message(line)
                return original(line)

            controller_ref._client.process_line = wrapped_process_line

    @callback
    def connection_fail_callback(data):
        """Network failure callback."""
        _LOGGER.error("Could not establish a connection with the AAP IP / Serial Module")
        if not sync_connect.done():
            sync_connect.set_result(False)

    @callback
    def connected_callback(data):
        """Connected callback."""
        _LOGGER.info("Connected to AAP IP / Serial Module")
        if message_log_enabled and hasattr(controller, '_client') and controller._client:
            _wrap_process_line(controller)
        if not sync_connect.done():
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_aapalarm)
            sync_connect.set_result(True)

    @callback
    def zones_updated_callback(data):
        """Handle zone updates."""
        _LOGGER.debug("Zone update event received for zone: %s", data)
        async_dispatcher_send(hass, SIGNAL_ZONE_UPDATE, data)

    @callback
    def areas_updated_callback(data):
        """Handle area updates."""
        _LOGGER.debug("Area update event received for area: %s", data)
        async_dispatcher_send(hass, SIGNAL_AREA_UPDATE, data)

    @callback
    def system_updated_callback(data):
        # Handle system updates.
        _LOGGER.debug("System update event received: %s", data)
        async_dispatcher_send(hass, SIGNAL_SYSTEM_UPDATE, data)

    @callback
    def output_updated_callback(data):
        """Handle output updates."""
        _LOGGER.debug("Output update event received for output: %s", data)
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

    try:
        result = await asyncio.wait_for(sync_connect, timeout=connection_timeout)
    except asyncio.TimeoutError:
        _LOGGER.error("Timed out connecting to AAP Alarm Module")
        controller.stop()
        raise ConfigEntryNotReady("Timed out connecting to AAP Alarm Module")
    if not result:
        raise ConfigEntryNotReady("Failed to connect to AAP Alarm Module")

    # Store entry reference for platforms
    hass.data[DOMAIN][f"{entry.entry_id}_entry"] = entry

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok and DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        controller = hass.data[DOMAIN][entry.entry_id]
        controller.stop()
        del hass.data[DOMAIN][entry.entry_id]
        # Clean up entry reference
        if f"{entry.entry_id}_entry" in hass.data[DOMAIN]:
            del hass.data[DOMAIN][f"{entry.entry_id}_entry"]
    
    return unload_ok


class AAPModuleDevice(Entity):
    """Representation of an AAP IP / Serial Module."""

    def __init__(self, entry: ConfigEntry, name, info, controller, area_number=None, area_name=None, device_type=None) -> None:
        """Initialize the device."""
        self._controller = controller
        self._info = info
        self._name = name
        self._entry = entry
        self._area_number = area_number
        self._area_name = area_name
        self._device_type = device_type
        
        # Create device info for the alarm system
        connection_type = entry.data.get(CONF_CONNECTIONTYPE, "unknown")
        
        if device_type == "areas":
            # Single device for all areas/alarm panels
            device_name = "Areas"
            device_identifier = f"{entry.entry_id}_areas"
        elif device_type == "zones":
            # Single device for all zones
            device_name = "Zones"
            device_identifier = f"{entry.entry_id}_zones"
        elif device_type == "outputs":
            # Single device for all outputs
            device_name = "Outputs"
            device_identifier = f"{entry.entry_id}_outputs"
        elif device_type == "system":
            # Single device for system status entities
            device_name = "System"
            device_identifier = f"{entry.entry_id}_system"
        else:
            # No device for entities that don't need grouping
            self._device_info = None
            return
        
        self._device_info = DeviceInfo(
            identifiers={(DOMAIN, device_identifier)},
            name=device_name,
            manufacturer="ArrowHead Alarm",
            model=f"Alarm Panel ({connection_type.upper()})",
            configuration_url=None,
            sw_version=_VERSION,
        )

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device information about this entity."""
        return self._device_info

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
        """Return a unique ID for this entity."""
        return f"{self._entry.entry_id}_{self._name}"
