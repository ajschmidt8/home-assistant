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
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_DEVICE_BAUD,
    CONF_DEVICE_PATH,
    CONF_RELAY_ADDR,
    CONF_RELAY_CHAN,
    CONF_ZONE_LOOP,
    CONF_ZONE_NAME,
    CONF_ZONE_NUMBER,
    CONF_ZONE_RFID,
    CONF_ZONE_TYPE,
    DEFAULT_DEVICE_BAUD,
    DEFAULT_DEVICE_HOST,
    DEFAULT_DEVICE_PATH,
    DEFAULT_DEVICE_PORT,
    DEFAULT_ZONE_TYPE,
    DOMAIN,
    PROTOCOL_SERIAL,
    PROTOCOL_SOCKET,
)


class AlarmDecoderFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a AlarmDecoder config flow."""

    VERSION = 1

    def __init__(self):
        """Initialize AlarmDecoder ConfigFlow"""
        self.protocol = None
        self.network_discovered = False

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
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
        errors = {}
        if user_input is not None:
            if self.protocol == PROTOCOL_SOCKET:
                baud = 0
                host = user_input[CONF_HOST]
                port = user_input[CONF_PORT]
                title = f"{host}:{port}"
                device = SocketDevice(interface=(host, port))
            if self.protocol == PROTOCOL_SERIAL:
                path = user_input[CONF_DEVICE_PATH]
                baud = user_input[CONF_DEVICE_BAUD]
                title = path
                device = SerialDevice(interface=path)

            controller = AdExt(device)
            try:
                with controller:
                    controller.open(baudrate=baud)
                return self.async_create_entry(title=title, data={})
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
        self.arm_options = config_entry.options.get(
            "arm_options",
            {"code_arm_required": True, "auto_bypass": False, "alt_night_mode": False,},
        )
        self.zones = config_entry.options.get("zones", {})

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            if user_input["edit_select"] == "Settings":
                return await self.async_step_settings()
            if user_input["edit_select"] == "Zones":
                return await self.async_step_zone()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("edit_select", default="Settings"): vol.In(
                        ["Settings", "Zones"]
                    )
                },
            ),
        )

    async def async_step_settings(self, user_input=None):
        """Manage the settings."""
        if user_input is not None:
            return self.async_create_entry(
                title="", data={"arm_options": user_input, "zones": self.zones}
            )

        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "alt_night_mode", default=self.arm_options["alt_night_mode"]
                    ): bool,
                    vol.Optional(
                        "auto_bypass", default=self.arm_options["auto_bypass"]
                    ): bool,
                    vol.Optional(
                        "code_arm_required",
                        default=self.arm_options["code_arm_required"],
                    ): bool,
                },
            ),
        )

    async def async_step_zone(self, user_input=None):
        """Manage the options."""
        errors = self._validate_zone_input(user_input)

        if user_input is not None and not errors:
            # Add Inclusive backend validation here
            zone_settings = self.zones.copy()
            zone_id = str(user_input[CONF_ZONE_NUMBER])
            zone_settings[zone_id] = user_input
            if CONF_ZONE_NAME not in zone_settings[zone_id]:
                zone_settings.pop(zone_id)
            return self.async_create_entry(
                title="", data={"arm_options": self.arm_options, "zones": zone_settings}
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
