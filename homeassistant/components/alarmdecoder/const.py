"""Constants for the AlarmDecoder component."""

CONF_ALT_NIGHT_MODE = "alt_night_mode"
CONF_AUTO_BYPASS = "auto_bypass"
CONF_CODE_ARM_REQUIRED = "code_arm_required"
CONF_DEVICE_BAUD = "baudrate"
CONF_DEVICE_PATH = "path"
CONF_RELAY_ADDR = "relayaddr"
CONF_RELAY_CHAN = "relaychan"
CONF_ZONE_LOOP = "loop"
CONF_ZONE_NAME = "name"
CONF_ZONE_NUMBER = "number"
CONF_ZONE_RFID = "rfid"
CONF_ZONE_TYPE = "type"

DEFAULT_ALT_NIGHT_MODE = False
DEFAULT_AUTO_BYPASS = False
DEFAULT_CODE_ARM_REQUIRED = True
DEFAULT_DEVICE_BAUD = 115200
DEFAULT_DEVICE_PATH = "/dev/ttyUSB0"
DEFAULT_DEVICE_HOST = "alarmdecoder"
DEFAULT_DEVICE_PORT = 10000
DEFAULT_ZONE_TYPE = "opening"

DOMAIN = "alarmdecoder"

OPTIONS_ARM = "arm_options"
OPTIONS_ZONES = "zone_options"

PROTOCOL_SOCKET = "socket"
PROTOCOL_SERIAL = "serial"
