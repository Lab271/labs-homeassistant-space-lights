from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up Space Lights number entity from a config entry."""
    host = config_entry.data["host"]
    name = config_entry.data["name"]
    async_add_entities([MyNumber(name, host)])


class MyNumber(NumberEntity):
    """Representation of a Space Light Speed Control."""

    def __init__(self, name: str, host: str) -> None:
        """Initialize the number entity."""
        self._name = f"{name}_speed"
        self._host = host
        self._value = 5  # Default value
        self._attr_unique_id = f"{host}_speed"  # Unique ID for the entity

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self._value

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        return 0

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        return 10

    @property
    def native_step(self) -> float:
        """Return the step value."""
        return 0.5

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for grouping entities under a device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._host)},
            name="Space Light",  # Device name, not the entity name
            manufacturer="Lab271",
            model="Space Model",
            sw_version="1.0",
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set a new value."""
        self._value = value
        self.async_write_ha_state()
