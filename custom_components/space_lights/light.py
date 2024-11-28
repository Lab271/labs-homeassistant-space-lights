import logging
import requests
from homeassistant.components.light import (
    LightEntity,
    LightEntityFeature,
    ColorMode,
    ATTR_RGB_COLOR,
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
)
from homeassistant.const import CONF_HOST, CONF_NAME

_LOGGER = logging.getLogger(__name__)

# Define the effects mapping
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

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the MyRGBLights platform."""
    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME, "My RGB Light")

    if host is None:
        _LOGGER.error("No host configured for the MyRGBLights platform")
        return

    add_entities([space_lights(name, host)])

class space_lights(LightEntity):
    """Representation of a My RGB Light."""

    def __init__(self, name, host):
        """Initialize the light."""
        self._name = name
        self._host = host
        self._state = False
        self._rgb_color = [255, 255, 255]  # Default to white
        self._brightness = 255  # Default to max brightness
        self._effect = None  # No effect by default
        self._attr_supported_color_modes = {ColorMode.RGB}
        self._attr_supported_features = LightEntityFeature.EFFECT
        _LOGGER.debug(f"space_lights initialized with name: {self._name}, host: {self._host}")

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    @property
    def rgb_color(self):
        """Return the RGB color value."""
        return self._rgb_color

    @property
    def brightness(self):
        """Return the brightness of the light."""
        return self._brightness

    @property
    def color_mode(self):
        """Return the current color mode."""
        return ColorMode.RGB

    @property
    def effect(self):
        """Return the current effect."""
        return self._effect

    @property
    def effect_list(self):
        """Return the list of available effects."""
        return list(EFFECTS.keys())

    def turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        self._state = True
        if ATTR_RGB_COLOR in kwargs:
            self._rgb_color = kwargs[ATTR_RGB_COLOR]
            _LOGGER.info(f"RGB Color on Turn on is {self._rgb_color}")
        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
        if ATTR_EFFECT in kwargs:
            self._effect = kwargs[ATTR_EFFECT]

        # Convert brightness (0–255) to intensity (0.0–1.0)
        intensity = self._brightness / 255

        # Determine the effect parameter to be sent
        effect_param = EFFECTS.get(self._effect, None)

        # Call the API to turn on the light with the given RGB color, intensity, and effect
        self._send_command("live", self._rgb_color, intensity, effect_param)

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        self._state = False

        # Call the API to turn off the light (intensity = 0)
        self._send_command(command="live", intensity=0)

    def update(self):
        """Fetch new state data for this light."""
        url = f"http://{self._host}/elm/stages/labs_strips/live"

        try:
            _LOGGER.debug(f"Fetching state from {url}")
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            # Update internal state from API response
            self._brightness = int(data["intensity"] * 255)  # Scale intensity (0.0–1.0) to brightness (0–255)
            self._rgb_color = [data["red"], data["green"], data["blue"]]
            self._state = data["intensity"] > 0  # Light is on if intensity > 0
            self._effect = self._map_int_to_effect(data["media"]) if "media" in data else None

            _LOGGER.info(f"State updated: {data}")
        except requests.RequestException as e:
            _LOGGER.error(f"Error updating state from {self._host}: {e}")

    def _send_command(self, command, rgb_color=None, intensity=None, effect=None):
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

        try:
            _LOGGER.debug(f"Sending command {command} to {url} with params {params}")
            response = requests.post(url, params=params)
            response.raise_for_status()
            _LOGGER.info(f"Command {command} sent successfully to {self._host}: {params}")
        except requests.RequestException as e:
            _LOGGER.error(f"Error sending {command} to {self._host}: {e}")

    def _map_int_to_effect(self, effect_int):
        """Map an integer back to its effect name."""
        for effect_name, effect_value in EFFECTS.items():
            if effect_value == effect_int:
                return effect_name
        return None