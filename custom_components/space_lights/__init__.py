from .const import DOMAIN
import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from typing import Any

# Pre-import platforms to avoid blocking calls
from . import light, number


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Space Lights from a config entry."""
    name = entry.data["name"]
    host = entry.data["host"]

    # Store data in hass
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"name": name, "host": host}

    # Forward entry setups for platforms (light and number)
    await hass.config_entries.async_forward_entry_setups(entry, ["light", "number"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await hass.config_entries.async_unload_platforms(entry, ["light", "number"])
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
