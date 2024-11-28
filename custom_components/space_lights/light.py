import logging
import requests
from homeassistant.components.light import (
    LightEntity,
    LightEntityFeature,
    ColorMode,
    ATTR_RGB_COLOR,
    ATTR_BRIGHTNESS,
)
from homeassistant.const import CONF_HOST, CONF_NAME

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the MyRGBLights platform."""
    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME, "My RGB Light")

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
        self._attr_supported_color_modes = {ColorMode.RGB}

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

    def turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        self._state = True
        if ATTR_RGB_COLOR in kwargs:
            self._rgb_color = kwargs[ATTR_RGB_COLOR]
            _LOGGER.info(f"RGB Color on Turn on is {self._rgb_color}")
        # else:
        #     self._rgb_color = [255, 255, 255]
        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
        # else:
        #     self._brightness = 120

        # Convert brightness (0–255) to intensity (0.0–1.0)
        intensity = self._brightness / 255

        # Call the API to turn on the light with the given RGB color and intensity
        self._send_command("live", self._rgb_color, intensity)

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        self._state = False

        # Call the API to turn off the light (intensity = 0)
        self._send_command(command = "live", intensity = 0)

    def update(self):
        """Fetch new state data for this light."""
        url = f"http://{self._host}/elm/stages/labs_strips/live"

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            # Update internal state from API response
            self._brightness = int(data["intensity"] * 255)  # Scale intensity (0.0–1.0) to brightness (0–255)
            self._rgb_color = [data["red"], data["green"], data["blue"]]
            self._state = data["intensity"] > 0  # Light is on if intensity > 0

            _LOGGER.info(f"State updated: {data}")
        except requests.RequestException as e:
            _LOGGER.error(f"Error updating state from {self._host}: {e}")

    def _send_command(self, command, rgb_color = None, intensity = None):
        """Send command to the light."""
        url = f"http://{self._host}/elm/stages/labs_strips/{command}"
        params = {}
        if rgb_color is not None:
            params["blue"] = rgb_color[2]
            params["green"] = rgb_color[1]
            params["red"] = rgb_color[0]
        
        if intensity is not None:
            params["intensity"] = intensity


        try:
            response = requests.post(url, params=params)
            response.raise_for_status()
            _LOGGER.info(f"Command {command} sent successfully to {self._host}: {params}")
        except requests.RequestException as e:
            _LOGGER.error(f"Error sending {command} to {self._host}: {e}")
