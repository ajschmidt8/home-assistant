"""Config flow for AlarmDecoder."""
import socket

from adext import AdExt
from alarmdecoder.devices import SerialDevice, SocketDevice
from alarmdecoder.util import NoDeviceError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.binary_sensor import DEVICE_CLASSES
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_PROTOCOL
from homeassistant.core import callback

from .const import (  # pylint: disable=unused-import
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
    DEFAULT_ALT_NIGHT_MODE,
    DEFAULT_ARM_OPTIONS,
    DEFAULT_AUTO_BYPASS,
    DEFAULT_CODE_ARM_REQUIRED,
    DEFAULT_DEVICE_BAUD,
    DEFAULT_DEVICE_HOST,
    DEFAULT_DEVICE_PATH,
    DEFAULT_DEVICE_PORT,
    DEFAULT_ZONE_OPTIONS,
    DEFAULT_ZONE_TYPE,
    DOMAIN,
    OPTIONS_ARM,
    OPTIONS_ZONES,
    PROTOCOL_SERIAL,
    PROTOCOL_SOCKET,
)

EDIT_KEY = "edit_selection"
EDIT_ZONES = "Zones"
EDIT_SETTINGS = "Arming Settings"


class AlarmDecoderFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a AlarmDecoder config flow."""

    VERSION = 1

    def __init__(self):
        """Initialize AlarmDecoder ConfigFlow."""
        self.protocol = None
        self.network_discovered = False

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for AlarmDecoder."""
        return AlarmDecoderOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""

        if user_input is not None:
            self.protocol = user_input[CONF_PROTOCOL]
            return await self.async_step_protocol()

        default_protocol = None
        if await async_discover_alarmdecoder(self.hass):
            self.network_discovered = True
            default_protocol = PROTOCOL_SOCKET

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PROTOCOL, default=default_protocol): vol.In(
                        [PROTOCOL_SOCKET, PROTOCOL_SERIAL]
                    ),
                }
            ),
        )

    async def async_step_protocol(self, user_input=None):
        """Handle AlarmDecoder protocol setup."""
        errors = {}
        if user_input is not None:
            connection = {}
            if self.protocol == PROTOCOL_SOCKET:
                baud = connection[CONF_DEVICE_BAUD] = DEFAULT_DEVICE_BAUD
                host = connection[CONF_HOST] = user_input[CONF_HOST]
                port = connection[CONF_PORT] = user_input[CONF_PORT]
                title = f"{host}:{port}"
                device = SocketDevice(interface=(host, port))
            if self.protocol == PROTOCOL_SERIAL:
                path = connection[CONF_DEVICE_PATH] = user_input[CONF_DEVICE_PATH]
                baud = connection[CONF_DEVICE_BAUD] = user_input[CONF_DEVICE_BAUD]
                title = path
                device = SerialDevice(interface=path)

            controller = AdExt(device)
            try:
                with controller:
                    controller.open(baudrate=baud)
                return self.async_create_entry(
                    title=title, data={CONF_PROTOCOL: self.protocol, **connection}
                )
            except NoDeviceError:
                errors["base"] = "service_unavailable"

        host = DEFAULT_DEVICE_HOST if self.network_discovered else ""

        if self.protocol == PROTOCOL_SOCKET:
            schema = vol.Schema(
                {
                    vol.Required(CONF_HOST, default=host): str,
                    vol.Required(CONF_PORT, default=DEFAULT_DEVICE_PORT): int,
                }
            )
        if self.protocol == PROTOCOL_SERIAL:
            schema = vol.Schema(
                {
                    vol.Required(CONF_DEVICE_PATH, default=DEFAULT_DEVICE_PATH): str,
                    vol.Required(CONF_DEVICE_BAUD, default=DEFAULT_DEVICE_BAUD): int,
                }
            )

        return self.async_show_form(
            step_id="protocol", data_schema=schema, errors=errors,
        )


class AlarmDecoderOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle AlarmDecoder options."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize AlarmDecoder options flow."""
        self.arm_options = config_entry.options.get(OPTIONS_ARM, DEFAULT_ARM_OPTIONS,)
        self.zone_options = config_entry.options.get(
            OPTIONS_ZONES, DEFAULT_ZONE_OPTIONS
        )

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            if user_input[EDIT_KEY] == EDIT_SETTINGS:
                return await self.async_step_settings()
            if user_input[EDIT_KEY] == EDIT_ZONES:
                return await self.async_step_zone()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(EDIT_KEY, default=EDIT_SETTINGS): vol.In(
                        [EDIT_SETTINGS, EDIT_ZONES]
                    )
                },
            ),
        )

    async def async_step_settings(self, user_input=None):
        """Manage the settings."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={OPTIONS_ARM: user_input, OPTIONS_ZONES: self.zone_options},
            )

        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ALT_NIGHT_MODE,
                        default=self.arm_options[CONF_ALT_NIGHT_MODE],
                    ): bool,
                    vol.Optional(
                        CONF_AUTO_BYPASS, default=self.arm_options[CONF_AUTO_BYPASS]
                    ): bool,
                    vol.Optional(
                        CONF_CODE_ARM_REQUIRED,
                        default=self.arm_options[CONF_CODE_ARM_REQUIRED],
                    ): bool,
                },
            ),
        )

    async def async_step_zone(self, user_input=None):
        """Manage the options."""
        errors = self._validate_zone_input(user_input)

        if user_input is not None and not errors:
            zone_options = self.zone_options.copy()
            zone_id = str(user_input[CONF_ZONE_NUMBER])
            zone_options[zone_id] = user_input
            if CONF_ZONE_NAME not in zone_options[zone_id]:
                zone_options.pop(zone_id)
            return self.async_create_entry(
                title="",
                data={OPTIONS_ARM: self.arm_options, OPTIONS_ZONES: zone_options},
            )

        return self.async_show_form(
            step_id="zone",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ZONE_NUMBER): str,
                    vol.Optional(CONF_ZONE_NAME): str,
                    vol.Optional(CONF_ZONE_TYPE, default=DEFAULT_ZONE_TYPE): vol.In(
                        DEVICE_CLASSES
                    ),
                    vol.Optional(CONF_ZONE_RFID): str,
                    vol.Optional(CONF_ZONE_LOOP): str,
                    vol.Optional(CONF_RELAY_ADDR,): str,
                    vol.Optional(CONF_RELAY_CHAN,): str,
                }
            ),
            errors=errors,
        )

    def _validate_zone_input(self, zone_input):
        if not zone_input:
            return {}
        errors = {}

        # CONF_RELAY_ADDR & CONF_RELAY_CHAN are inclusive
        if (CONF_RELAY_ADDR in zone_input and CONF_RELAY_CHAN not in zone_input) or (
            CONF_RELAY_ADDR not in zone_input and CONF_RELAY_CHAN in zone_input
        ):
            errors["base"] = "relay_inclusive"

        # The following keys must be int
        for key in [CONF_ZONE_NUMBER, CONF_ZONE_LOOP, CONF_RELAY_ADDR, CONF_RELAY_CHAN]:
            if key in zone_input:
                try:
                    int(zone_input[key])
                except ValueError:
                    errors[key] = "int"

        # CONF_ZONE_LOOP depends on CONF_ZONE_RFID
        if CONF_ZONE_LOOP in zone_input and CONF_ZONE_RFID not in zone_input:
            errors[CONF_ZONE_LOOP] = "loop_rfid"

        # CONF_ZONE_LOOP must be 1-4
        if CONF_ZONE_LOOP in zone_input and int(zone_input[CONF_ZONE_LOOP]) not in list(
            range(1, 5)
        ):
            errors[CONF_ZONE_LOOP] = "loop_range"

        return errors


async def async_discover_alarmdecoder(hass):
    """Discover AlarmDecoder address."""
    try:
        return await hass.async_add_executor_job(
            socket.gethostbyname, DEFAULT_DEVICE_HOST
        )
    except socket.gaierror:
        return None
