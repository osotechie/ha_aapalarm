"""Exercise the actual HA flow managers, mocking only TCP connection attempts."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_TIMEOUT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant.common import MockConfigEntry

from custom_components.aapalarm.const import (
    CONF_AREAS,
    CONF_CONNECTIONTYPE,
    CONF_KEEPALIVE,
    CONF_OUTPUTS,
    CONF_PORT,
    CONF_ZONES,
    DOMAIN,
)

from .const import ENTRY_DATA


@pytest.mark.parametrize(
    ("port", "valid"),
    [
        ("/dev/ttyUSB0", True),
        ("/dev/ttyACM0", True),
        ("/dev/ttyS0", True),
        ("COM1", True),
        ("COM12", True),
        ("../../../../etc/passwd", False),
        ("/etc/passwd", False),
        ("/tmp/fake_serial", False),
        ("", False),
        ("/dev/tty USB0", False),
        ("/dev/ttyUSB0; rm -rf /", False),
        ("/dev/ttyUSB0\x00", False),
    ],
)
async def test_serial_port_validation(
    hass: HomeAssistant, port: str, valid: bool
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONNECTIONTYPE: "serial"}
    )
    assert result["step_id"] == "serial_connection"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PORT: port}
    )
    assert result["type"] is FlowResultType.FORM
    if valid:
        assert result["step_id"] == "areas"
        assert not result["errors"]
    else:
        assert result["step_id"] == "serial_connection"
        assert result["errors"] == {"base": "invalid_serial_port"}


@pytest.mark.parametrize("failure", [OSError("offline"), TimeoutError()])
async def test_ip_connection_failure(hass: HomeAssistant, failure: Exception) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONNECTIONTYPE: "ip"}
    )
    with patch(
        "custom_components.aapalarm.config_flow.asyncio.open_connection",
        new=AsyncMock(side_effect=failure),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: "192.0.2.1", CONF_PORT: "5002"}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "ip_connection"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_complete_ip_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONNECTIONTYPE: "ip"}
    )
    writer = MagicMock(spec=asyncio.StreamWriter)
    with patch(
        "custom_components.aapalarm.config_flow.asyncio.open_connection",
        new=AsyncMock(return_value=(MagicMock(spec=asyncio.StreamReader), writer)),
    ) as connect:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.0.2.1",
                CONF_PORT: "5002",
                CONF_KEEPALIVE: 60,
                CONF_TIMEOUT: 10,
            },
        )
    connect.assert_awaited_once_with("192.0.2.1", 5002)
    writer.close.assert_called_once()
    writer.wait_closed.assert_awaited_once()
    assert result["step_id"] == "areas"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"configure_areas": True}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"area_number": 1, "area_name": "House", "area_code": "1234"},
    )
    assert result["step_id"] == "zones"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"configure_zones": True}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"zone_number": 1, "zone_name": "Front Door", "zone_type": "opening"},
    )
    assert result["step_id"] == "outputs"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"configure_outputs": True}
    )
    with patch(
        "custom_components.aapalarm.async_setup_entry",
        new=AsyncMock(return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"output_number": 1, "output_name": "Gate"}
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "aapalarm_192.0.2.1_5002"
    assert result["data"][CONF_AREAS] == {1: ENTRY_DATA[CONF_AREAS]["1"]}
    assert result["data"][CONF_ZONES] == {1: ENTRY_DATA[CONF_ZONES]["1"]}
    assert result["data"][CONF_OUTPUTS] == {1: ENTRY_DATA[CONF_OUTPUTS]["1"]}


async def test_complete_serial_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONNECTIONTYPE: "serial"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PORT: "/dev/ttyUSB0", CONF_KEEPALIVE: 60, CONF_TIMEOUT: 10},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"configure_areas": False}
    )
    with patch(
        "custom_components.aapalarm.async_setup_entry",
        new=AsyncMock(return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"configure_outputs": False}
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "aapalarm_/dev/ttyUSB0"
    assert result["data"][CONF_CONNECTIONTYPE] == "serial"


async def test_duplicate_entry(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONNECTIONTYPE: "ip"}
    )
    writer = MagicMock(spec=asyncio.StreamWriter)
    with patch(
        "custom_components.aapalarm.config_flow.asyncio.open_connection",
        new=AsyncMock(return_value=(MagicMock(), writer)),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: "192.0.2.1", CONF_PORT: "5002"}
        )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"configure_areas": False}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"configure_outputs": False}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure_preserves_entities(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": config_entry.entry_id,
        },
    )
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONNECTIONTYPE: "serial"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PORT: "/dev/ttyUSB0", CONF_KEEPALIVE: 60, CONF_TIMEOUT: 10},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"configure_areas": False}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"configure_zones": False}
    )
    with patch.object(hass.config_entries, "async_reload", return_value=True) as reload:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"configure_outputs": False}
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert config_entry.data[CONF_CONNECTIONTYPE] == "serial"
    assert config_entry.data[CONF_PORT] == "/dev/ttyUSB0"
    for key in (CONF_AREAS, CONF_ZONES, CONF_OUTPUTS):
        assert config_entry.data[key] == {1: ENTRY_DATA[key]["1"]}
    reload.assert_awaited_once_with(config_entry.entry_id)


async def test_options(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_KEEPALIVE: 90, CONF_TIMEOUT: 20}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {CONF_KEEPALIVE: 90, CONF_TIMEOUT: 20}
