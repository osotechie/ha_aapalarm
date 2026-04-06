"""Constants for the AAP Alarm integration."""

DOMAIN = "aapalarm"

# Configuration constants
CONF_KEEPALIVE = "keepalive_interval"
CONF_CONNECTIONTYPE = "connectiontype"
CONF_PORT = "port"

CONF_AREAS = "areas"
CONF_AREANAME = "name"
CONF_CODE = "code"
CONF_CODE_ARM_REQUIRED = "code_arm_required"
CONF_CODE_PANIC_REQUIRED = "code_panic_required"

CONF_ZONES = "zones"
CONF_ZONENAME = "name"
CONF_ZONETYPE = "type"

CONF_OUTPUTS = "outputs"
CONF_OUTPUTNAME = "name"
CONF_MESSAGE_LOG_ENABLED = "message_log_enabled"

# Default values
DEFAULT_PORT = "5002"
DEFAULT_KEEPALIVE = 60
DEFAULT_TIMEOUT = 10
DEFAULT_ZONETYPE = "motion"
DEFAULT_MESSAGE_LOG_ENABLED = False

# Signals
SIGNAL_ZONE_UPDATE = "aapalarm.zones_updated"
SIGNAL_AREA_UPDATE = "aapalarm.areas_updated"
SIGNAL_SYSTEM_UPDATE = "aapalarm.system_updated"
SIGNAL_OUTPUT_UPDATE = "aapalarm.output_updated"
SIGNAL_KEYPAD_UPDATE = "aapalarm.keypad_updated"
SIGNAL_MESSAGE_LOG_UPDATE = "aapalarm.message_log_updated"

# Data key
DATA_AAP = "aapalarm"
