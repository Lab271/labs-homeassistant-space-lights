from .const import DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

# Pre-import platforms to avoid blocking calls
from . import light, number


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Enttec LED Mapper from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "name": entry.data["name"],
        "host": entry.data["host"],
        "stage": entry.data["stage"],
    }

    await hass.config_entries.async_forward_entry_setups(entry, ["light", "number"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await hass.config_entries.async_unload_platforms(entry, ["light", "number"])
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
