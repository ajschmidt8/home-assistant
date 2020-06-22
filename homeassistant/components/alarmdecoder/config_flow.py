"""Config flow for AlarmDecoder."""
import socket

from adext import AdExt
from alarmdecoder.devices import SerialDevice, SocketDevice
from alarmdecoder.util import NoDeviceError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_PROTOCOL
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_DEVICE_BAUD,
    CONF_DEVICE_PATH,
    DEFAULT_DEVICE_BAUD,
    DEFAULT_DEVICE_HOST,
    DEFAULT_DEVICE_PATH,
    DEFAULT_DEVICE_PORT,
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
                return self.async_create_entry(title=title, data={"test": "data"})
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

    def __init__(self, config_entry):
        """Initialize AlarmDecoder options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            if user_input["edit_select"] == "Settings":
                return await self.async_step_settings()
            if user_input["edit_select"] == "Zones":
                return await self.async_step_zones()

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
            print("HERE!")
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "alt_night_mode",
                        default=self.config_entry.options.get("alt_night_mode", False),
                    ): bool,
                    vol.Optional(
                        "auto_bypass",
                        default=self.config_entry.options.get("auto_bypass", False),
                    ): bool,
                    vol.Optional(
                        "code_arm_required",
                        default=self.config_entry.options.get(
                            "code_arm_required", True
                        ),
                    ): bool,
                },
            ),
        )

    async def async_step_zones(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            print("HERE!")
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="zones",
            data_schema=vol.Schema(
                {
                    vol.Required("action"): vol.In(
                        [
                            "Save Zones and Close",
                            "Add New Zone",
                            "Edit Zone 1 - Front Door",
                        ]
                    )
                },
            ),
        )

    async def async_step_zone(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            print("HERE!")
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="zone",
            data_schema=vol.Schema(
                {vol.Required("show_things"): bool, vol.Required("more"): str},
            ),
        )


async def async_discover_alarmdecoder(hass):
    """Discover AlarmDecoder address."""
    try:
        return await hass.async_add_executor_job(
            socket.gethostbyname, DEFAULT_DEVICE_HOST
        )
    except socket.gaierror:
        return None
