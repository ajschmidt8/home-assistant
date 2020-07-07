"""Support for AlarmDecoder devices."""
import asyncio
from datetime import timedelta
import logging

from adext import AdExt
from alarmdecoder.devices import SerialDevice, SocketDevice
from alarmdecoder.util import NoDeviceError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_PROTOCOL,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DEVICE_BAUD,
    CONF_DEVICE_PATH,
    DEFAULT_ZONE_OPTIONS,
    DOMAIN,
    OPTIONS_ZONES,
    PROTOCOL_SERIAL,
    PROTOCOL_SOCKET,
    SIGNAL_OPTIONS_UPDATE,
    SIGNAL_PANEL_MESSAGE,
    SIGNAL_REL_MESSAGE,
    SIGNAL_RFX_MESSAGE,
    SIGNAL_ZONE_FAULT,
    SIGNAL_ZONE_RESTORE,
)

_LOGGER = logging.getLogger(__name__)

RESTART = False


async def async_setup(hass, config):
    """Set up for the AlarmDecoder devices."""
    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """Set up AlarmDecoder config flow."""
    _LOGGER.error("we made it here")
    _LOGGER.error("entry: %s", entry.as_dict())
    entry.add_update_listener(_update_listener)

    ad_connection = entry.data
    protocol = ad_connection[CONF_PROTOCOL]
    zones = entry.options.get(OPTIONS_ZONES, DEFAULT_ZONE_OPTIONS)
    _LOGGER.error("zones: %s", zones)

    def stop_alarmdecoder(event):
        """Handle the shutdown of AlarmDecoder."""
        if not hass.data.get(DOMAIN):
            return
        _LOGGER.debug("Shutting down alarmdecoder")
        global RESTART
        RESTART = False
        controller.close()

    def open_connection(now=None):
        """Open a connection to AlarmDecoder."""
        global RESTART
        try:
            controller.open(baud)
        except NoDeviceError:
            _LOGGER.debug("Failed to connect. Retrying in 5 seconds")
            hass.helpers.event.track_point_in_time(
                open_connection, dt_util.utcnow() + timedelta(seconds=5)
            )
            return
        _LOGGER.debug("Established a connection with the alarmdecoder")
        RESTART = True

    def handle_closed_connection(event):
        """Restart after unexpected loss of connection."""
        global RESTART
        if not RESTART:
            return
        RESTART = False
        _LOGGER.warning("AlarmDecoder unexpectedly lost connection")
        hass.add_job(open_connection)

    def handle_message(sender, message):
        """Handle message from AlarmDecoder."""
        hass.helpers.dispatcher.dispatcher_send(SIGNAL_PANEL_MESSAGE, message)

    def handle_rfx_message(sender, message):
        """Handle RFX message from AlarmDecoder."""
        hass.helpers.dispatcher.dispatcher_send(SIGNAL_RFX_MESSAGE, message)

    def zone_fault_callback(sender, zone):
        """Handle zone fault from AlarmDecoder."""
        hass.helpers.dispatcher.dispatcher_send(SIGNAL_ZONE_FAULT, zone)

    def zone_restore_callback(sender, zone):
        """Handle zone restore from AlarmDecoder."""
        hass.helpers.dispatcher.dispatcher_send(SIGNAL_ZONE_RESTORE, zone)

    def handle_rel_message(sender, message):
        """Handle relay or zone expander message from AlarmDecoder."""
        hass.helpers.dispatcher.dispatcher_send(SIGNAL_REL_MESSAGE, message)

    controller = False
    baud = ad_connection[CONF_DEVICE_BAUD]
    if protocol == PROTOCOL_SOCKET:
        host = ad_connection[CONF_HOST]
        port = ad_connection[CONF_PORT]
        controller = AdExt(SocketDevice(interface=(host, port)))
    if protocol == PROTOCOL_SERIAL:
        path = ad_connection[CONF_DEVICE_PATH]
        controller = AdExt(SerialDevice(interface=path))

    controller.on_message += handle_message
    controller.on_rfx_message += handle_rfx_message
    controller.on_zone_fault += zone_fault_callback
    controller.on_zone_restore += zone_restore_callback
    controller.on_close += handle_closed_connection
    controller.on_expander_message += handle_rel_message

    hass.data[DOMAIN] = controller

    open_connection()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_alarmdecoder)

    for component in _get_platforms(entry):
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistantType, entry: ConfigEntry):
    """Unload a AlarmDecoder entry."""
    print("unloading")
    global RESTART
    RESTART = False

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in _get_platforms(entry)
            ]
        )
    )

    if not unload_ok:
        return False

    hass.data[DOMAIN].close()
    hass.data.pop(DOMAIN)

    return True


def _get_platforms(entry: ConfigEntry):
    """Get a list of platforms for loading/unloading AlarmDecoder."""
    zones = entry.options.get(OPTIONS_ZONES, DEFAULT_ZONE_OPTIONS)
    platforms = ["alarm_control_panel", "sensor"]
    if zones:
        platforms.append("binary_sensor")

    return platforms


async def _update_listener(hass: HomeAssistantType, entry: ConfigEntry):
    """Handle options update."""
    print("updated! :", entry.as_dict())
    async_dispatcher_send(hass, SIGNAL_OPTIONS_UPDATE, entry)
