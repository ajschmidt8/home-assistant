"""Test the NEW_NAME config flow."""
from alarmdecoder.util import NoDeviceError
from homeassistant import config_entries, data_entry_flow
from homeassistant.components.alarmdecoder.const import (
    CONF_ALT_NIGHT_MODE,
    CONF_AUTO_BYPASS,
    CONF_CODE_ARM_REQUIRED,
    CONF_DEVICE_BAUD,
    CONF_DEVICE_PATH,
    DOMAIN,
    DEFAULT_ARM_OPTIONS,
    DEFAULT_ZONE_OPTIONS,
    OPTIONS_ARM,
    OPTIONS_ZONES,
    PROTOCOL_SERIAL,
    PROTOCOL_SOCKET,
    CONF_ZONE_LOOP,
    CONF_ZONE_NAME,
    CONF_ZONE_NUMBER,
    CONF_ZONE_RFID,
    CONF_ZONE_TYPE,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_PROTOCOL
from homeassistant.core import HomeAssistant


from tests.async_mock import patch
from tests.common import MockConfigEntry


async def test_setup_serial(hass: HomeAssistant):
    """Test flow for serial setup."""

    baud = 200
    path = "/dev/ttyUSB1234"
    protocol = PROTOCOL_SERIAL
    connection_settings = {CONF_DEVICE_BAUD: baud, CONF_DEVICE_PATH: path}

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PROTOCOL: protocol},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "protocol"

    with patch("homeassistant.components.alarmdecoder.config_flow.AdExt.open"), patch(
        "homeassistant.components.alarmdecoder.config_flow.AdExt.close"
    ), patch(
        "homeassistant.components.alarmdecoder.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.alarmdecoder.async_setup_entry", return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], connection_settings
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == path
        assert result["data"] == {
            CONF_PROTOCOL: protocol,
            CONF_DEVICE_PATH: path,
            CONF_DEVICE_BAUD: baud,
        }

    await hass.async_block_till_done()
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_setup_socket(hass: HomeAssistant):
    """Test flow for socket setup."""

    port = 1001
    host = "alarmdecoder123"
    protocol = PROTOCOL_SOCKET
    connection_settings = {CONF_HOST: host, CONF_PORT: port}

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PROTOCOL: protocol},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "protocol"

    with patch("homeassistant.components.alarmdecoder.config_flow.AdExt.open"), patch(
        "homeassistant.components.alarmdecoder.config_flow.AdExt.close"
    ), patch(
        "homeassistant.components.alarmdecoder.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.alarmdecoder.async_setup_entry", return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], connection_settings
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == f"{host}:{port}"
        assert result["data"] == {
            CONF_PROTOCOL: protocol,
            CONF_HOST: host,
            CONF_PORT: port,
            CONF_DEVICE_BAUD: 115200,
        }

    await hass.async_block_till_done()
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_setup_connection_error(hass: HomeAssistant):
    """Test flow for setup with a connection error."""

    port = 1001
    host = "alarmdecoder"
    protocol = PROTOCOL_SOCKET
    connection_settings = {CONF_HOST: host, CONF_PORT: port}

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PROTOCOL: protocol},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "protocol"

    with patch(
        "homeassistant.components.alarmdecoder.config_flow.AdExt.open",
        side_effect=NoDeviceError,
    ), patch("homeassistant.components.alarmdecoder.config_flow.AdExt.close"):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], connection_settings
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["errors"] == {"base": "service_unavailable"}


async def test_options_arm_flow(hass):
    """Test arm options flow."""
    user_input = {
        CONF_ALT_NIGHT_MODE: True,
        CONF_AUTO_BYPASS: True,
        CONF_CODE_ARM_REQUIRED: True,
    }
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"edit_selection": "Arming Settings"},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "arm_settings"

    with patch(
        "homeassistant.components.alarmdecoder.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input=user_input,
        )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert entry.options == {
        OPTIONS_ARM: user_input,
        OPTIONS_ZONES: DEFAULT_ZONE_OPTIONS,
    }


async def test_options_zone_flow(hass):
    """Test zone options flow."""
    zone_number = "2"

    # Check what happens when zone fields are left empty. Are they included in the final dict?
    zone_settings = {
        CONF_ZONE_NAME: True,
        CONF_AUTO_BYPASS: True,
        CONF_CODE_ARM_REQUIRED: True,
    }
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"edit_selection": "Zones"},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "arm_settings"

    with patch(
        "homeassistant.components.alarmdecoder.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input=user_input,
        )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert entry.options == {
        OPTIONS_ARM: DEFAULT_ARM_OPTIONS,
        OPTIONS_ZONES: {},
    }
