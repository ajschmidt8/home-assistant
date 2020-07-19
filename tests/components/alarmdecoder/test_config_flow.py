"""Test the AlarmDecoder config flow."""
from alarmdecoder.util import NoDeviceError
from homeassistant import config_entries, data_entry_flow
from homeassistant.components.alarmdecoder.const import (
    CONF_ALT_NIGHT_MODE,
    CONF_AUTO_BYPASS,
    CONF_CODE_ARM_REQUIRED,
    CONF_DEVICE_BAUD,
    CONF_DEVICE_PATH,
    CONF_RELAY_ADDR,
    CONF_RELAY_CHAN,
    CONF_ZONE_LOOP,
    CONF_ZONE_NAME,
    CONF_ZONE_NUMBER,
    CONF_ZONE_RFID,
    CONF_ZONE_TYPE,
    DOMAIN,
    DEFAULT_ARM_OPTIONS,
    DEFAULT_ZONE_OPTIONS,
    OPTIONS_ARM,
    OPTIONS_ZONES,
    PROTOCOL_SERIAL,
    PROTOCOL_SOCKET,
)

from homeassistant.components.binary_sensor import DEVICE_CLASS_WINDOW
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


async def test_options_arm_flow(hass: HomeAssistant):
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


async def test_options_zone_flow(hass: HomeAssistant):
    """Test options flow for adding/deleting zones."""
    zone_number = "2"
    zone_settings = {CONF_ZONE_NAME: "Front Entry", CONF_ZONE_TYPE: DEVICE_CLASS_WINDOW}
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"edit_selection": "Zones"},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "zone_select"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_ZONE_NUMBER: zone_number},
    )

    with patch(
        "homeassistant.components.alarmdecoder.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input=zone_settings,
        )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert entry.options == {
        OPTIONS_ARM: DEFAULT_ARM_OPTIONS,
        OPTIONS_ZONES: {zone_number: zone_settings},
    }

    # Make sure zone can be removed...
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"edit_selection": "Zones"},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "zone_select"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_ZONE_NUMBER: zone_number},
    )

    with patch(
        "homeassistant.components.alarmdecoder.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={},
        )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert entry.options == {
        OPTIONS_ARM: DEFAULT_ARM_OPTIONS,
        OPTIONS_ZONES: {},
    }


async def test_options_zone_flow_validation(hass: HomeAssistant):
    """Test input validation for zone options flow."""
    zone_number = "2"
    zone_settings = {CONF_ZONE_NAME: "Front Entry", CONF_ZONE_TYPE: DEVICE_CLASS_WINDOW}
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"edit_selection": "Zones"},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "zone_select"

    # Zone Number must be int
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_ZONE_NUMBER: "asd"},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "zone_select"
    assert result["errors"] == {CONF_ZONE_NUMBER: "int"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_ZONE_NUMBER: zone_number},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "zone_details"

    # CONF_RELAY_ADDR & CONF_RELAY_CHAN are inclusive
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={**zone_settings, CONF_RELAY_ADDR: "1"},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "zone_details"
    assert result["errors"] == {"base": "relay_inclusive"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={**zone_settings, CONF_RELAY_CHAN: "1"},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "zone_details"
    assert result["errors"] == {"base": "relay_inclusive"}

    # CONF_RELAY_ADDR, CONF_RELAY_CHAN must be int
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={**zone_settings, CONF_RELAY_ADDR: "abc", CONF_RELAY_CHAN: "abc"},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "zone_details"
    assert result["errors"] == {
        CONF_RELAY_ADDR: "int",
        CONF_RELAY_CHAN: "int",
    }

    # CONF_ZONE_LOOP depends on CONF_ZONE_RFID
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={**zone_settings, CONF_ZONE_LOOP: "1"},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "zone_details"
    assert result["errors"] == {CONF_ZONE_LOOP: "loop_rfid"}

    # CONF_ZONE_LOOP must be int
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={**zone_settings, CONF_ZONE_RFID: "rfid123", CONF_ZONE_LOOP: "ab"},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "zone_details"
    assert result["errors"] == {CONF_ZONE_LOOP: "int"}

    # CONF_ZONE_LOOP must be between [1,4]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={**zone_settings, CONF_ZONE_RFID: "rfid123", CONF_ZONE_LOOP: "5"},
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "zone_details"
    assert result["errors"] == {CONF_ZONE_LOOP: "loop_range"}

    # All valid settings
    with patch(
        "homeassistant.components.alarmdecoder.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                **zone_settings,
                CONF_ZONE_RFID: "rfid123",
                CONF_ZONE_LOOP: "2",
                CONF_RELAY_ADDR: "12",
                CONF_RELAY_CHAN: "1",
            },
        )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert entry.options == {
        OPTIONS_ARM: DEFAULT_ARM_OPTIONS,
        OPTIONS_ZONES: {
            zone_number: {
                **zone_settings,
                CONF_ZONE_RFID: "rfid123",
                CONF_ZONE_LOOP: "2",
                CONF_RELAY_ADDR: "12",
                CONF_RELAY_CHAN: "1",
            }
        },
    }
