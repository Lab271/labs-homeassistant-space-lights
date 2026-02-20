import logging
import aiohttp
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up Enttec LED Mapper speed control from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([ELMStageSpeed(hass, data["name"], data["host"], data["stage"])])


class ELMStageSpeed(NumberEntity):
    """Controls the speed of an Enttec LED Mapper stage."""

    def __init__(self, hass: HomeAssistant, name: str, host: str, stage: str) -> None:
        """Initialize the speed control."""
        self._hass = hass
        self._name = f"{name} Speed"
        self._host = host
        self._stage = stage
        self._value = 5.0
        self._attr_unique_id = f"{host}_{stage}_speed"

    @property
    def name(self) -> str:
        return self._name

    @property
    def native_value(self) -> float:
        return self._value

    @property
    def native_min_value(self) -> float:
        return 0

    @property
    def native_max_value(self) -> float:
        return 10

    @property
    def native_step(self) -> float:
        return 0.5

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._host)},
            name="Enttec LED Mapper",
            manufacturer="Enttec",
            model="LED Mapper",
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set a new speed value and send it to the ELM stage."""
        self._value = value
        url = f"http://{self._host}/elm/stages/{self._stage}/live"
        session = async_get_clientsession(self._hass)
        try:
            async with session.post(
                url,
                params={"speed": value},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                response.raise_for_status()
        except aiohttp.ClientError as e:
            _LOGGER.error("Error setting speed on %s: %s", self._host, e)
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Fetch current speed from the ELM stage."""
        url = f"http://{self._host}/elm/stages/{self._stage}/live"
        session = async_get_clientsession(self._hass)
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                response.raise_for_status()
                data = await response.json()
                _LOGGER.debug("Speed update: %s", data)

            if "speed" in data:
                self._value = data["speed"]

        except aiohttp.ClientError as e:
            _LOGGER.error("Error fetching speed from %s: %s", self._host, e)
