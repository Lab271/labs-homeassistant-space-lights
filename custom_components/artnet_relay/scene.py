# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2024-2026 Schuberg Philis / Lab271
"""Expose the relay's configured scenes (POST /scenes/{name})."""

from __future__ import annotations

from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .hub import ArtnetRelayHub

DEFAULT_TRANSITION_MS = 1000


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up one scene entity per scene the relay reports."""
    hub: ArtnetRelayHub = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(ArtnetRelayScene(hub, name) for name in sorted(hub.scenes))


class ArtnetRelayScene(Scene):
    """A scene defined in the relay's config.yaml."""

    _attr_has_entity_name = True

    def __init__(self, hub: ArtnetRelayHub, scene: str) -> None:
        self._hub = hub
        self._scene = scene
        self._attr_name = scene.replace("_", " ").title()
        self._attr_unique_id = f"{hub.host}_{hub.port}_scene_{scene}"

    @property
    def device_info(self) -> dict[str, Any]:
        return self._hub.device_info

    @property
    def available(self) -> bool:
        return self._hub.available

    async def async_activate(self, **kwargs: Any) -> None:
        """Apply the scene. The relay takes the fade as a query param."""
        transition = kwargs.get("transition")
        transition_ms = (
            int(transition * 1000) if transition is not None else DEFAULT_TRANSITION_MS
        )
        await self._hub.post(
            f"/scenes/{self._scene}", params={"transition_ms": transition_ms}
        )
