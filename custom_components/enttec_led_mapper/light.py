import logging
import aiohttp
from typing import Optional
from homeassistant.components.light import (
    LightEntity,
    LightEntityFeature,
    ColorMode,
    ATTR_RGB_COLOR,
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

EFFECTS = {
    "Static": 5,
    "Circle": 2,
    "Horizontal Swing": 3,
    "Vertical Swing": 4,
    "Happy Rainbow": 6,
    "Fireworks": 7,
    "Old Snake": 8,
    "Bouncing Things": 9,
    "Horizontal + Vertical Swing": 10,
    "Warp Speed": 11,
    "Particles": 12,
    "Topologica": 13,
    "Bubbles Soap": 14,
}


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the Enttec LED Mapper light platform from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([ELMStageLight(hass, data["name"], data["host"], data["stage"])])


class ELMStageLight(LightEntity):
    """Representation of an Enttec LED Mapper stage as a light."""

    def __init__(self, hass: HomeAssistant, name: str, host: str, stage: str) -> None:
        """Initialize the light."""
        self._hass = hass
        self._name = name
        self._host = host
        self._stage = stage
        self._state = False
        self._rgb_color = [255, 255, 255]
        self._brightness = 255
        self._effect = None
        self._attr_supported_color_modes = {ColorMode.RGB}
        self._attr_supported_features = LightEntityFeature.EFFECT
        self._attr_unique_id = f"{host}_{stage}_light"

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_on(self) -> bool:
        return self._state

    @property
    def rgb_color(self) -> list:
        return self._rgb_color

    @property
    def brightness(self) -> int:
        return self._brightness

    @property
    def color_mode(self) -> str:
        return ColorMode.RGB

    @property
    def effect(self) -> Optional[str]:
        return self._effect

    @property
    def effect_list(self) -> list:
        return list(EFFECTS.keys())

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._host)},
            "name": "Enttec LED Mapper",
            "manufacturer": "Enttec",
            "model": "LED Mapper",
        }

    async def async_turn_on(self, **kwargs) -> None:
        """Instruct the light to turn on."""
        self._state = True
        if ATTR_RGB_COLOR in kwargs:
            self._rgb_color = kwargs[ATTR_RGB_COLOR]
        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
        if ATTR_EFFECT in kwargs:
            self._effect = kwargs[ATTR_EFFECT]

        intensity = self._brightness / 255
        effect_param = EFFECTS.get(self._effect, None)

        await self._send_command("live", self._rgb_color, intensity, effect_param)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Instruct the light to turn off."""
        self._state = False
        await self._send_command(command="live", intensity=0)
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Fetch new state data for this light."""
        url = f"http://{self._host}/elm/stages/{self._stage}/live"
        session = async_get_clientsession(self._hass)
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                response.raise_for_status()
                data = await response.json()
                _LOGGER.debug("Light update: %s", data)

            self._state = data["intensity"] > 0
            if self._state:
                self._brightness = int(data["intensity"] * 255)
            self._rgb_color = [data["red"], data["green"], data["blue"]]
            self._effect = self._map_int_to_effect(data["media"]) if "media" in data else None

        except aiohttp.ClientError as e:
            _LOGGER.error("Error updating state from %s: %s", self._host, e)

    async def _send_command(
        self,
        command: str,
        rgb_color: Optional[list] = None,
        intensity: Optional[float] = None,
        effect: Optional[int] = None,
    ) -> None:
        """Send command to the ELM stage."""
        url = f"http://{self._host}/elm/stages/{self._stage}/{command}"
        params = {}
        if rgb_color is not None:
            params["red"] = rgb_color[0]
            params["green"] = rgb_color[1]
            params["blue"] = rgb_color[2]
        if intensity is not None:
            params["intensity"] = intensity
        if effect is not None:
            params["media"] = effect

        _LOGGER.debug("Sending to %s: %s", url, params)
        session = async_get_clientsession(self._hass)
        try:
            async with session.post(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as response:
                response.raise_for_status()
        except aiohttp.ClientError as e:
            _LOGGER.error("Error sending %s to %s: %s", command, self._host, e)

    def _map_int_to_effect(self, effect_int: int) -> Optional[str]:
        """Map an integer back to its effect name."""
        for effect_name, effect_value in EFFECTS.items():
            if effect_value == effect_int:
                return effect_name
        return None
