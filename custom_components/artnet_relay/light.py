"""Art-Net Relay light platform."""

import logging
from typing import Any

import aiohttp

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

EFFECTS = ["rainbow", "chase", "breathe", "strobe", "police", "fire", "sparkle", "wave"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up the Art-Net Relay light from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [ArtnetRelayLight(hass, data["name"], data["host"], data["port"])]
    )


class ArtnetRelayLight(LightEntity):
    """A whole-relay light entity controlled via the artnet-relay /all endpoint."""

    _attr_assumed_state = True
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_supported_features = LightEntityFeature.TRANSITION | LightEntityFeature.EFFECT
    _attr_effect_list = EFFECTS

    def __init__(self, hass: HomeAssistant, name: str, host: str, port: int) -> None:
        self._hass = hass
        self._attr_name = name
        self._host = host
        self._port = port
        self._attr_unique_id = f"{host}_{port}_light"
        self._attr_is_on = False
        self._attr_brightness = 255
        self._attr_rgb_color = (255, 255, 255)
        self._attr_effect = None

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, f"{self._host}:{self._port}")},
            "name": self._attr_name,
            "manufacturer": "Lab271",
            "model": "Art-Net Relay",
        }

    @property
    def _base_url(self) -> str:
        return f"http://{self._host}:{self._port}"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the lights on, applying any color/brightness/transition/effect kwargs."""
        if ATTR_RGB_COLOR in kwargs:
            self._attr_rgb_color = tuple(kwargs[ATTR_RGB_COLOR])
        if ATTR_BRIGHTNESS in kwargs:
            self._attr_brightness = kwargs[ATTR_BRIGHTNESS]

        body: dict[str, Any] = {
            "r": self._attr_rgb_color[0],
            "g": self._attr_rgb_color[1],
            "b": self._attr_rgb_color[2],
            "brightness": (self._attr_brightness or 255) / 255,
        }

        if ATTR_EFFECT in kwargs and kwargs[ATTR_EFFECT] in EFFECTS:
            effect = kwargs[ATTR_EFFECT]
            if await self._post(f"/effects/{effect}", json=body):
                self._attr_effect = effect
                self._attr_is_on = True
                self.async_write_ha_state()
            return

        if ATTR_TRANSITION in kwargs:
            body["transition_ms"] = int(kwargs[ATTR_TRANSITION] * 1000)

        if await self._post("/all", json=body):
            self._attr_effect = None
            self._attr_is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the lights off by fading brightness to zero (honours transition)."""
        body: dict[str, Any] = {
            "r": self._attr_rgb_color[0],
            "g": self._attr_rgb_color[1],
            "b": self._attr_rgb_color[2],
            "brightness": 0.0,
        }
        if ATTR_TRANSITION in kwargs:
            body["transition_ms"] = int(kwargs[ATTR_TRANSITION] * 1000)

        if await self._post("/all", json=body):
            self._attr_effect = None
            self._attr_is_on = False
            self.async_write_ha_state()

    async def _post(self, path: str, json: dict | None = None) -> bool:
        url = f"{self._base_url}{path}"
        session = async_get_clientsession(self._hass)
        try:
            async with session.post(
                url,
                json=json,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                response.raise_for_status()
                return True
        except aiohttp.ClientError as e:
            _LOGGER.error("POST %s failed: %s", url, e)
            return False
