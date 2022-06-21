"""Support for controlling a Orange Pi cover."""
from __future__ import annotations

from time import sleep

import voluptuous as vol

from homeassistant.components.cover import PLATFORM_SCHEMA, CoverEntity
from homeassistant.const import CONF_COVERS, CONF_NAME, CONF_UNIQUE_ID, STATE_CLOSED, STATE_CLOSING, STATE_OPEN, STATE_OPENING
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.reload import setup_reload_service
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN, PLATFORMS, setup_output, write_output

CONF_CLOSE_PIN = "close_pin"
CONF_STOP_PIN = "stop_pin"
CONF_OPEN_PIN = "open_pin"
CONF_INVERT_RELAY = "invert_relay"
CONF_INTERMEDIATE_MODE = 'intermediate_mode'
CONF_CLOSE_DURATION = "close_duration"
CONF_OPEN_DURATION = "open_duration"
CONF_DEVICE_CLASS = "device_class"

DEFAULT_RELAY_TIME = 0.2
DEFAULT_INTERMEDIATE_TIME = 5
DEFAULT_INVERT_RELAY = False
DEFAULT_INTERMEDIATE_MODE = False
DEFAULT_CLOSE_DURATION = 5
DEFAULT_OPEN_DURATION = 5

_COVERS_SCHEMA = vol.All(
    cv.ensure_list,
    [
        vol.Schema(
            {
                CONF_NAME: cv.string,
                CONF_CLOSE_PIN: cv.positive_int,
                CONF_STOP_PIN: cv.positive_int,
                CONF_OPEN_PIN: cv.positive_int,        
                vol.Optional(CONF_INVERT_RELAY, default=DEFAULT_INVERT_RELAY): cv.boolean,
                vol.Optional(CONF_INTERMEDIATE_MODE, default=DEFAULT_INTERMEDIATE_MODE): cv.boolean,
                vol.Optional(CONF_CLOSE_DURATION, default=DEFAULT_CLOSE_DURATION): cv.positive_int,
                vol.Optional(CONF_OPEN_DURATION, default=DEFAULT_OPEN_DURATION): cv.positive_int,
                vol.Optional(CONF_DEVICE_CLASS, default=None): cv.string,
                vol.Optional(CONF_UNIQUE_ID): cv.string,
            }
        )
    ],
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_COVERS): _COVERS_SCHEMA,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the OPi cover platform."""
    setup_reload_service(hass, DOMAIN, PLATFORMS)

    covers = []
    covers_conf = config[CONF_COVERS]

    for cover in covers_conf:
        covers.append(
            OPiGPIOCover(
                cover[CONF_NAME],
                cover[CONF_CLOSE_PIN],
                cover[CONF_STOP_PIN],
                cover[CONF_OPEN_PIN],
                cover[CONF_INVERT_RELAY],
                cover[CONF_INTERMEDIATE_MODE],
                cover[CONF_CLOSE_DURATION],
                cover[CONF_OPEN_DURATION],
                cover[CONF_DEVICE_CLASS],
                cover.get(CONF_UNIQUE_ID),
            )
        )
    add_entities(covers)


class OPiGPIOCover(CoverEntity):
    """Representation of a Orange GPIO cover."""

    def __init__(
        self,
        name,
        close_pin,
        stop_pin,
        open_pin,
        invert_relay,
        intermediate_mode,
        close_duration,
        open_duration,
        device_class,
        
        unique_id,
    ):
        """Initialize the cover."""
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._state = STATE_CLOSED
        self._close_pin = close_pin
        self._stop_pin = stop_pin
        self._open_pin = open_pin
        self._invert_relay = invert_relay
        self._intermediate_mode = intermediate_mode
        self._close_duration = close_duration
        self._open_duration = open_duration
        self._attr_device_class = device_class

        setup_output(self._close_pin)
        setup_output(self._stop_pin)
        setup_output(self._open_pin)
        write_output(self._close_pin, 1 if self._invert_relay else 0)
        write_output(self._stop_pin, 1 if self._invert_relay else 0)
        write_output(self._open_pin, 1 if self._invert_relay else 0)

    @property
    def is_closed(self):
        """Return true if cover is closed."""
        return self._state == STATE_CLOSED

    def _trigger(self, pin, val, delay, duration):
        write_output(pin, val)
        sleep(delay)
        write_output(pin, 0 if val == 1 else 1)
        sleep(duration)

    def close_cover(self, **kwargs):
        """Close the cover."""
        if not self.is_closed:
            self._state = STATE_CLOSING
            self._trigger(self._close_pin, 0 if self._invert_relay else 1, DEFAULT_RELAY_TIME, self._close_duration)
            self._state = STATE_CLOSED

    def open_cover(self, **kwargs):
        """Open the cover."""
        if self.is_closed:
            self._state = STATE_OPENING
            if self._intermediate_mode:
                self._trigger(self._stop_pin, 0 if self._invert_relay else 1, DEFAULT_INTERMEDIATE_TIME, self._open_duration)
            else:
                self._trigger(self._open_pin, 0 if self._invert_relay else 1, DEFAULT_RELAY_TIME, self._open_duration)
            self._state = STATE_OPEN

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        self._trigger(self._stop_pin, 0 if self._invert_relay else 1, DEFAULT_RELAY_TIME, 0)
