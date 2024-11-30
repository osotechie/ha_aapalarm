# CONSTANTS for Integration
DOMAIN = "aapalarm"
DATA_AAP = "data_aap"

# CONSTANTS for Connection Type
CONF_AAP_CONNECTIONTYPE = "connectiontype"
CONF_AAP_CONNECTIONTYPES = ["serial", "ip"]
CONF_AAP_PORT = "port"
CONF_AAP_KEEPALIVE = "keep_alive"

# CONSTATNS for Areas
CONF_AREANUM = "Number of Areas in use"
CONF_AREAS = "areas"
CONF_AREANAME = "name"
CONF_CODE = "code"
CONF_CODE_ARM_REQUIRED = "code_arm_required"

# CONSTANTS for Zones
CONF_ZONENUM = "Number of Zones in use"
CONF_ZONES = "zones"
CONF_ZONENAME = "name"
CONF_ZONETYPE = "type"
CONF_ZONETYPES = ["Motion", "Door", "Window", "Smoke"]

# CONSTATNS for Outputs
CONF_OUTPUTNUM = "Number of Outputs in use"
CONF_OUTPUTS = "outputs"
CONF_OUTPUTNAME = "name"

# DEFAULT VALUES
DEFAULT_PORT = "5002"
DEFAULT_KEEPALIVE = 60
DEFAULT_ZONETYPE = "opening"
DEFAULT_TIMEOUT = 10

# HA Constants
SIGNAL_ZONE_UPDATE = "aapalarm.zones_updated"
SIGNAL_AREA_UPDATE = "aapalarm.areas_updated"
SIGNAL_SYSTEM_UPDATE = "aapalarm.system_updated"
SIGNAL_OUTPUT_UPDATE = "aapalarm.output_updated"
SIGNAL_KEYPAD_UPDATE = "aapalarm.keypad_updated"