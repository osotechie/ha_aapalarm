"""Representative alarm configuration for offline tests."""

from homeassistant.const import CONF_HOST, CONF_TIMEOUT

from custom_components.aapalarm.const import (
    CONF_AREAS,
    CONF_CONNECTIONTYPE,
    CONF_KEEPALIVE,
    CONF_OUTPUTS,
    CONF_PORT,
    CONF_ZONES,
)

ENTRY_DATA = {
    CONF_CONNECTIONTYPE: "ip",
    CONF_HOST: "192.0.2.1",
    CONF_PORT: "5002",
    CONF_KEEPALIVE: 60,
    CONF_TIMEOUT: 10,
    CONF_AREAS: {
        "1": {
            "name": "House",
            "code": "1234",
            "code_arm_required": True,
            "code_panic_required": True,
        }
    },
    CONF_ZONES: {"1": {"name": "Front Door", "type": "opening"}},
    CONF_OUTPUTS: {"1": {"name": "Gate"}},
}
