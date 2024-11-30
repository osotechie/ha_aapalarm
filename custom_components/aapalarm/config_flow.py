import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_HOST, CONF_TIMEOUT, EVENT_HOMEASSISTANT_STOP
from .const import (
    DOMAIN, 
    CONF_AAP_CONNECTIONTYPE, 
    CONF_AAP_CONNECTIONTYPES, 
    CONF_AAP_PORT, 
    CONF_AAP_KEEPALIVE, 
    CONF_ZONES, 
    CONF_ZONENUM,
    CONF_ZONETYPES, 
    CONF_AREAS, 
    CONF_AREANUM, 
    CONF_OUTPUTS, 
    CONF_OUTPUTNUM
)

_LOGGER = logging.getLogger(__name__)

@config_entries.HANDLERS.register(DOMAIN)
class AAPAlarmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AAP Alarm."""

    VERSION = "2024.11.30"
    #CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        self.data = {}
        self.zone_index = 1
        self.output_index = 1
        self.area_index = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_area_count()

        data_schema = vol.Schema({
            vol.Required(CONF_AAP_CONNECTIONTYPE, default=CONF_AAP_CONNECTIONTYPES[0]): vol.In(CONF_AAP_CONNECTIONTYPES),
            vol.Required(CONF_HOST, default='localhost'): str,
            vol.Required(CONF_AAP_PORT, default='/dev/ttyUSB0'): str,
            vol.Required(CONF_AAP_KEEPALIVE, default=60): int,
            vol.Required(CONF_TIMEOUT, default=20): int,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors,
            description_placeholders={"title": "Connection Details"}
        )

    async def async_step_area_count(self, user_input=None):
        """Handle the step to capture the number of areas."""
        errors = {}
        if user_input is not None:
            try:
                if user_input[CONF_AREANUM] < 1 or user_input[CONF_AREANUM] > 2:
                    errors["base"] = "invalid_area_count"
                else:
                    self.data[CONF_AREANUM] = user_input[CONF_AREANUM]
                    self.area_index = 1  # Initialize area_index
                    return await self.async_step_area()
            except Exception as e:
                _LOGGER.error("Error in async_step_area_count: %s", e)
                errors["base"] = "unknown"

        data_schema = vol.Schema({
            vol.Required(CONF_AREANUM, default=1): vol.All(vol.Coerce(int), vol.Range(min=1)),
        })

        return self.async_show_form(
            step_id="area_count", data_schema=data_schema, errors=errors,
            description_placeholders={"title": "Areas"}
        )

    async def async_step_area(self, user_input=None):
        """Handle the step to capture details for each area."""
        errors = {}
        if user_input is not None:
            try:
                if CONF_AREAS not in self.data:
                    self.data[CONF_AREAS] = {}
                area_id = user_input[f"ID"]
                self.data[CONF_AREAS][area_id] = {
                    "name": user_input[f"Name"],
                    "code": user_input[f"Code"],
                    "code_arm_required": user_input[f"Code Required to Arm"]
                }
                self.area_index += 1
                if self.area_index > self.data[CONF_AREANUM]:
                    return await self.async_step_zone_count()
                return await self.async_step_area()
            except Exception as e:
                _LOGGER.error("Error in async_step_area: %s", e)
                errors["base"] = "unknown"

        area_schema = vol.Schema({
            vol.Required(f"ID"): int,
            vol.Required(f"Name"): str,
            vol.Required(f"Code"): str,
            vol.Required(f"Code Required to Arm", default=False): bool,
        })

        return self.async_show_form(
            step_id="area", data_schema=area_schema, errors=errors,
            description_placeholders={"title": "Area {self.area_index}"}
        )

    async def async_step_zone_count(self, user_input=None):
        """Handle the step to capture the number of zones."""
        errors = {}
        if user_input is not None:
            try:
                if user_input[CONF_ZONENUM] < 1:
                    errors["base"] = "invalid_zone_count"
                else:
                    self.data[CONF_ZONENUM] = user_input[CONF_ZONENUM]
                    self.zone_index = 1  # Initialize zone_index
                    return await self.async_step_zone()
            except Exception as e:
                _LOGGER.error("Error in async_step_zone_count: %s", e)
                errors["base"] = "unknown"

        data_schema = vol.Schema({
            vol.Required(CONF_ZONENUM, default=8): vol.All(vol.Coerce(int), vol.Range(min=1)),
        })

        return self.async_show_form(
            step_id="zone_count", data_schema=data_schema, errors=errors,
            description_placeholders={"title": "Zones"}
        )

    async def async_step_zone(self, user_input=None):
        """Handle the step to capture details for each zone."""
        errors = {}
        if user_input is not None:
            try:
                if CONF_ZONES not in self.data:
                    self.data[CONF_ZONES] = {}
                zone_id = user_input[f"ID"]
                self.data[CONF_ZONES][zone_id] = {
                    "name": user_input[f"Name"],
                    "type": user_input[f"Type"].lower()
                }
                self.zone_index += 1
                if self.zone_index > self.data[CONF_ZONENUM]:
                    return await self.async_step_output_count()
                return await self.async_step_zone()
            except Exception as e:
                _LOGGER.error("Error in async_step_zone: %s", e)
                errors["base"] = "unknown"

        zone_schema = vol.Schema({
            vol.Required(f"ID"): int,
            vol.Required(f"Name"): str,
            vol.Required(f"Type", default=CONF_ZONETYPES[0]): vol.In(CONF_ZONETYPES),
        })

        return self.async_show_form(
            step_id="zone", data_schema=zone_schema, errors=errors,
            description_placeholders={"title": "Zone {self.zone_index}"}
        )

    async def async_step_output_count(self, user_input=None):
        """Handle the step to capture the number of outputs."""
        errors = {}
        if user_input is not None:
            try:
                self.data[CONF_OUTPUTNUM] = user_input[CONF_OUTPUTNUM]
                if self.data[CONF_OUTPUTNUM] == 0:
                    return self.async_create_entry(title="AAP Alarm", data=self.data)
                self.output_index = 1  # Initialize output_index
                return await self.async_step_output()
            except Exception as e:
                _LOGGER.error("Error in async_step_output_count: %s", e)
                errors["base"] = "unknown"

        data_schema = vol.Schema({
            vol.Required(CONF_OUTPUTNUM, default=2): vol.All(vol.Coerce(int), vol.Range(min=0)),
        })

        return self.async_show_form(
            step_id="output_count", data_schema=data_schema, errors=errors,
            description_placeholders={"title": "Outputs"}
        )

    async def async_step_output(self, user_input=None):
        """Handle the step to capture details for each output."""
        errors = {}
        if user_input is not None:
            try:
                if CONF_OUTPUTS not in self.data:
                    self.data[CONF_OUTPUTS] = {}
                output_id = user_input[f"ID"]
                self.data[CONF_OUTPUTS][output_id] = {
                    "name": user_input[f"Name"]
                }
                self.output_index += 1
                if self.output_index > self.data[CONF_OUTPUTNUM]:
                    return self.async_create_entry(title="AAP Alarm", data=self.data)
                return await self.async_step_output()
            except Exception as e:
                _LOGGER.error("Error in async_step_output: %s", e)
                errors["base"] = "unknown"

        output_schema = vol.Schema({
            vol.Required(f"ID"): int,
            vol.Required(f"Name"): str,
        })

        return self.async_show_form(
            step_id="output", data_schema=output_schema, errors=errors,
            description_placeholders={"title": "Output {self.output_index}"}
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AAPAlarmOptionsFlowHandler(config_entry)


class AAPAlarmOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle AAP Alarm options."""

    def __init__(self, config_entry):
        """Initialize AAP Alarm options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_AAP_CONNECTIONTYPE, default=self.config_entry.options.get(CONF_AAP_CONNECTIONTYPE)): str,
            vol.Required(CONF_HOST, default=self.config_entry.options.get(CONF_HOST)): str,
            vol.Required(CONF_AAP_PORT, default=self.config_entry.options.get(CONF_AAP_PORT)): int,
            vol.Required(CONF_AAP_KEEPALIVE, default=self.config_entry.options.get(CONF_AAP_KEEPALIVE)): int,
            vol.Required(CONF_TIMEOUT, default=self.config_entry.options.get(CONF_TIMEOUT)): int,
        })

        return self.async_show_form(
            step_id="init", data_schema=data_schema
        )