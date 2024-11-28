import logging
from typing import Optional, Dict
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
from .const import DOMAIN
import aiohttp

_LOGGER = logging.getLogger(__name__)

EFFECTS = {
    "Solid": 5,
    "Sparkle": 1,
    "Breath": 2,
    "Zigzag Horizontal": 3,
    "Zigzag Vertical": 4,
    "Fast Jitter": 6,
    "Slow Jitter": 8,
    "Flow": 7,
}

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the Space Lights platform from a config entry."""
    host = config_entry.data["host"]
    name = config_entry.data["name"]

    async_add_entities([SpaceLights(name, host)])


class SpaceLights(LightEntity):
    """Representation of a Space Light."""

    def __init__(self, name: str, host: str) -> None:
        """Initialize the light."""
        self._name = name
        self._host = host
        self._state = False
        self._rgb_color = [255, 255, 255]  # Default to white
        self._brightness = 255  # Default to max brightness
        self._effect = None  # No effect by default
        self._attr_supported_color_modes = {ColorMode.RGB}
        self._attr_supported_features = LightEntityFeature.EFFECT
        self._attr_unique_id = f"{host}_light"

    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._state

    @property
    def rgb_color(self) -> list:
        """Return the RGB color value."""
        return self._rgb_color

    @property
    def brightness(self) -> int:
        """Return the brightness of the light."""
        return self._brightness

    @property
    def color_mode(self) -> str:
        """Return the current color mode."""
        return ColorMode.RGB

    @property
    def effect(self) -> Optional[str]:
        """Return the current effect."""
        return self._effect

    @property
    def effect_list(self) -> list:
        """Return the list of available effects."""
        return list(EFFECTS.keys())

    @property
    def device_info(self):
        """Return device information about this Space Light."""
        return {
            "identifiers": {(DOMAIN, self._host)},  # Use host as unique identifier
            "name": "Space Light",                # Device name
            "manufacturer": "Lab271",
            "model": "Space Model",
            "sw_version": "1.0",
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
        _LOGGER.info(f"kwargs {kwargs}")
        # Convert brightness (0–255) to intensity (0.0–1.0)
        intensity = self._brightness / 255
        if kwargs == {}:
            _LOGGER.info(f"kwargs was empty")
            intensity = 1
        # Determine the effect parameter to be sent
        effect_param = EFFECTS.get(self._effect, None)
        
        # Call the API to turn on the light with the given RGB color, intensity, and effect
        await self._send_command("live", self._rgb_color, intensity, effect_param)

    async def async_turn_off(self, **kwargs) -> None:
        """Instruct the light to turn off."""
        self._state = False

        # Call the API to turn off the light (intensity = 0)
        await self._send_command(command="live", intensity=0)

    async def async_update(self) -> None:
        """Fetch new state data for this light."""
        url = f"http://{self._host}/elm/stages/labs_strips/live"



        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    response.raise_for_status()
                    data = await response.json()
                    _LOGGER.info(f"Light Update {data}")
            # Update internal state from API response
            self._brightness = int(data["intensity"] * 255)  # Scale intensity (0.0–1.0) to brightness (0–255)
            self._rgb_color = [data["red"], data["green"], data["blue"]]
            self._state = data["intensity"] > 0  # Light is on if intensity > 0
            self._effect = self._map_int_to_effect(data["media"]) if "media" in data else None

        except aiohttp.ClientError as e:
            _LOGGER.error(f"Error updating state from {self._host}: {e}")

    async def _send_command(self, command: str, rgb_color: Optional[list] = None, intensity: Optional[float] = None, effect: Optional[int] = None) -> None:
        """Send command to the light."""
        url = f"http://{self._host}/elm/stages/labs_strips/{command}"
        params = {}
        if rgb_color is not None:
            params["blue"] = rgb_color[2]
            params["green"] = rgb_color[1]
            params["red"] = rgb_color[0]

        if intensity is not None:
            params["intensity"] = intensity

        if effect is not None:
            params["media"] = effect
        _LOGGER.info(f"Turning Light on with {params}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, params=params, timeout=5) as response:
                    response.raise_for_status()
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Error sending {command} to {self._host}: {e}")

    def _map_int_to_effect(self, effect_int: int) -> Optional[str]:
        """Map an integer back to its effect name."""
        for effect_name, effect_value in EFFECTS.items():
            if effect_value == effect_int:
                return effect_name
        return None
