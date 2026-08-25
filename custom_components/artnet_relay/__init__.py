# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2024-2026 Schuberg Philis / Lab271
"""The Art-Net Relay integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .hub import ArtnetRelayHub

# Pre-import platforms to avoid blocking calls
from . import light, scene  # noqa: F401


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Art-Net Relay from a config entry."""
    hub = ArtnetRelayHub(
        hass,
        entry.data["name"],
        entry.data["host"],
        entry.data["port"],
    )
    # Ask the relay what it can do before creating entities: the effect list,
    # the scenes and the groups all come from the running relay.
    await hub.async_discover()
    hub.start()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = hub

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hub: ArtnetRelayHub = hass.data[DOMAIN].pop(entry.entry_id)
        await hub.stop()
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Re-run discovery, e.g. after the relay's config.yaml changed."""
    await hass.config_entries.async_reload(entry.entry_id)
