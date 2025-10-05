"""
Config flow for ArrowHead Alarm System integration (aapalarm).
"""

import asyncio
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_HOST, CONF_TIMEOUT
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv
import logging

from pyaapalarmmodule import AAPAlarmPanel

from .const import (
    DOMAIN, 
    DEFAULT_PORT, 
    DEFAULT_KEEPALIVE, 
    DEFAULT_TIMEOUT,
    CONF_CONNECTIONTYPE,
    CONF_KEEPALIVE,
    CONF_PORT,
    CONF_ZONES,
    CONF_AREAS,
    CONF_OUTPUTS,
)

_LOGGER = logging.getLogger(__name__)

class AAPAlarmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ArrowHead Alarm System."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize the config flow."""
        self._connection_data = {}
        self._zones_data = {}
        self._areas_data = {}
        self._outputs_data = {}

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step - connection type selection."""
        errors = {}
        
        if user_input is not None:
            # Store connection type and proceed to connection details
            self._connection_data = user_input
            connection_type = user_input[CONF_CONNECTIONTYPE]
            
            if connection_type == "ip":
                return await self.async_step_ip_connection()
            else:
                return await self.async_step_serial_connection()

        # Just ask for connection type first
        data_schema = vol.Schema({
            vol.Required(CONF_CONNECTIONTYPE, default="ip"): vol.In(["ip", "serial"]),
        })
        
        return self.async_show_form(
            step_id="user", 
            data_schema=data_schema, 
            errors=errors,
            description_placeholders={
                "info": "Choose how your alarm panel is connected to Home Assistant"
            }
        )

    async def async_step_ip_connection(self, user_input=None) -> FlowResult:
        """Handle IP connection configuration."""
        errors = {}
        
        if user_input is not None:
            # Merge IP connection data with existing data
            self._connection_data.update(user_input)
            return await self.async_step_areas()

        # Default values for IP connection
        host = self._connection_data.get(CONF_HOST, "192.168.1.100")
        port = self._connection_data.get(CONF_PORT, DEFAULT_PORT)
        keepalive = self._connection_data.get(CONF_KEEPALIVE, DEFAULT_KEEPALIVE)
        timeout = self._connection_data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)

        data_schema = vol.Schema({
            vol.Required(CONF_HOST, default=host): cv.string,
            vol.Required(CONF_PORT, default=port): cv.string,
            vol.Optional(CONF_KEEPALIVE, default=keepalive): vol.All(vol.Coerce(int), vol.Range(min=15)),
            vol.Optional(CONF_TIMEOUT, default=timeout): vol.Coerce(int),
        })
        
        return self.async_show_form(
            step_id="ip_connection", 
            data_schema=data_schema, 
            errors=errors,
            description_placeholders={
                "info": "Configure the IP connection to your alarm panel"
            }
        )

    async def async_step_serial_connection(self, user_input=None) -> FlowResult:
        """Handle Serial connection configuration."""
        errors = {}
        
        if user_input is not None:
            # Merge serial connection data with existing data
            self._connection_data.update(user_input)
            return await self.async_step_areas()

        # Default values for serial connection
        port = self._connection_data.get(CONF_PORT, "/dev/ttyUSB0")
        keepalive = self._connection_data.get(CONF_KEEPALIVE, DEFAULT_KEEPALIVE)
        timeout = self._connection_data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)

        data_schema = vol.Schema({
            vol.Required(CONF_PORT, default=port): cv.string,
            vol.Optional(CONF_KEEPALIVE, default=keepalive): vol.All(vol.Coerce(int), vol.Range(min=15)),
            vol.Optional(CONF_TIMEOUT, default=timeout): vol.Coerce(int),
        })
        
        return self.async_show_form(
            step_id="serial_connection", 
            data_schema=data_schema, 
            errors=errors,
            description_placeholders={
                "info": "Configure the serial connection to your alarm panel. Use format like /dev/ttyUSB0"
            }
        )

    async def async_step_areas(self, user_input=None) -> FlowResult:
        """Configure areas (alarm panels)."""
        errors = {}
        
        if user_input is not None:
            if user_input.get("configure_areas", False):
                return await self.async_step_area_config()
            else:
                # Skip areas, go to outputs
                return await self.async_step_outputs()

        data_schema = vol.Schema({
            vol.Optional("configure_areas", default=False): bool,
        })
        
        return self.async_show_form(
            step_id="areas", 
            data_schema=data_schema, 
            errors=errors,
            description_placeholders={
                "info": "Areas represent different alarm zones/partitions in your system"
            }
        )

    async def async_step_area_config(self, user_input=None) -> FlowResult:
        """Configure individual areas."""
        errors = {}
        
        if user_input is not None:
            area_number = user_input.get("area_number")
            area_name = user_input.get("area_name")
            area_code = user_input.get("area_code", "")
            code_arm_required = user_input.get("code_arm_required", True)
            
            # Check for duplicate area numbers
            if area_number and area_number in self._areas_data:
                errors["area_number"] = "Area number already exists"
            elif area_number and area_name:
                self._areas_data[area_number] = {
                    "name": area_name,
                    "code": area_code,
                    "code_arm_required": code_arm_required
                }
            
            if not errors and user_input.get("add_another_area", False):
                return await self.async_step_area_config()
            elif not errors:
                return await self.async_step_zones()

        # Suggest next available area number
        suggested_area = 1
        while suggested_area in self._areas_data:
            suggested_area += 1

        data_schema = vol.Schema({
            vol.Required("area_number", default=suggested_area): vol.All(vol.Coerce(int), vol.Range(min=1, max=2)),
            vol.Required("area_name"): cv.string,
            vol.Optional("area_code", default=""): cv.string,
            vol.Optional("code_arm_required", default=True): bool,
            vol.Optional("add_another_area", default=False): bool,
        })
        
        return self.async_show_form(
            step_id="area_config", 
            data_schema=data_schema, 
            errors=errors
        )

    async def async_step_zones(self, user_input=None) -> FlowResult:
        """Configure zones."""
        errors = {}
        
        if user_input is not None:
            if user_input.get("configure_zones", False):
                return await self.async_step_zone_config()
            else:
                # Skip zones, go to outputs
                return await self.async_step_outputs()

        data_schema = vol.Schema({
            vol.Optional("configure_zones", default=False): bool,
        })
        
        return self.async_show_form(
            step_id="zones", 
            data_schema=data_schema, 
            errors=errors,
            description_placeholders={
                "info": "Zones represent door/window sensors and other detection devices"
            }
        )

    async def async_step_zone_config(self, user_input=None) -> FlowResult:
        """Configure individual zones."""
        errors = {}
        
        if user_input is not None:
            zone_number = user_input.get("zone_number")
            zone_name = user_input.get("zone_name")
            zone_type = user_input.get("zone_type", "opening")
            
            # Check for duplicate zone numbers
            if zone_number and zone_number in self._zones_data:
                errors["zone_number"] = "Zone number already exists"
            elif zone_number and zone_name:
                self._zones_data[zone_number] = {
                    "name": zone_name,
                    "type": zone_type
                }
            
            if not errors and user_input.get("add_another_zone", False):
                return await self.async_step_zone_config()
            elif not errors:
                return await self.async_step_outputs()

        # Suggest next available zone number
        suggested_zone = 1
        while suggested_zone in self._zones_data:
            suggested_zone += 1

        data_schema = vol.Schema({
            vol.Required("zone_number", default=suggested_zone): vol.All(vol.Coerce(int), vol.Range(min=1, max=32)),
            vol.Required("zone_name"): cv.string,
            vol.Optional("zone_type", default="motion"): vol.In(["motion", "opening", "smoke", "glass", "shock"]),
            vol.Optional("add_another_zone", default=False): bool,
        })
        
        return self.async_show_form(
            step_id="zone_config", 
            data_schema=data_schema, 
            errors=errors
        )

    async def async_step_outputs(self, user_input=None) -> FlowResult:
        """Configure outputs."""
        errors = {}
        
        if user_input is not None:
            if user_input.get("configure_outputs", False):
                return await self.async_step_output_config()
            else:
                # Create the entry
                return await self._create_entry()

        data_schema = vol.Schema({
            vol.Optional("configure_outputs", default=False): bool,
        })
        
        return self.async_show_form(
            step_id="outputs", 
            data_schema=data_schema, 
            errors=errors,
            description_placeholders={
                "info": "Outputs control devices like sirens, lights, or other controllable devices"
            }
        )

    async def async_step_output_config(self, user_input=None) -> FlowResult:
        """Configure individual outputs."""
        errors = {}
        
        if user_input is not None:
            output_number = user_input.get("output_number")
            output_name = user_input.get("output_name")
            
            # Check for duplicate output numbers
            if output_number and output_number in self._outputs_data:
                errors["output_number"] = "Output number already exists"
            elif output_number and output_name:
                self._outputs_data[output_number] = {
                    "name": output_name
                }
            
            if not errors and user_input.get("add_another_output", False):
                return await self.async_step_output_config()
            elif not errors:
                return await self._create_entry()

        # Suggest next available output number
        suggested_output = 1
        while suggested_output in self._outputs_data:
            suggested_output += 1

        data_schema = vol.Schema({
            vol.Required("output_number", default=suggested_output): vol.All(vol.Coerce(int), vol.Range(min=1, max=32)),
            vol.Required("output_name"): cv.string,
            vol.Optional("add_another_output", default=False): bool,
        })
        
        return self.async_show_form(
            step_id="output_config", 
            data_schema=data_schema, 
            errors=errors
        )

    async def _create_entry(self) -> FlowResult:
        """Create the config entry."""
        # Combine all configuration data
        data = self._connection_data.copy()
        
        if self._areas_data:
            data[CONF_AREAS] = self._areas_data
        if self._zones_data:
            data[CONF_ZONES] = self._zones_data
        if self._outputs_data:
            data[CONF_OUTPUTS] = self._outputs_data
        
        # Create a meaningful title
        title = f"ArrowHead Alarm Module ({data.get(CONF_CONNECTIONTYPE, '').upper()})"
        
        return self.async_create_entry(title=title, data=data)

class AAPAlarmOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for AAP Alarm."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema({
            vol.Optional(
                CONF_KEEPALIVE, 
                default=self.config_entry.data.get(CONF_KEEPALIVE, DEFAULT_KEEPALIVE)
            ): vol.All(vol.Coerce(int), vol.Range(min=15)),
            vol.Optional(
                CONF_TIMEOUT, 
                default=self.config_entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
            ): vol.Coerce(int),
        })

        return self.async_show_form(
            step_id="init", 
            data_schema=data_schema
        )
