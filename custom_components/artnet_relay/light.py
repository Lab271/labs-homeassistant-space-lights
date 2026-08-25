# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2024-2026 Schuberg Philis / Lab271
"""Art-Net Relay light platform.

One light for the whole relay (POST /all) plus one per configured group
(POST /groups/{name}). Effects are relay-wide, so only the whole-relay light
exposes them.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, entity_platform

from .const import (
    ATTR_EFFECT_PARAMS,
    DOMAIN,
    SERVICE_START_EFFECT,
    SERVICE_STOP_EFFECT,
)
from .hub import ArtnetRelayHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up the relay light and one light per group."""
    hub: ArtnetRelayHub = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[ArtnetRelayBaseLight] = [ArtnetRelayLight(hub)]
    entities.extend(
        ArtnetRelayGroupLight(hub, group, members)
        for group, members in sorted(hub.groups.items())
    )
    async_add_entities(entities)

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_START_EFFECT,
        {
            vol.Required(ATTR_EFFECT): cv.string,
            # Free-form so new relay effect params work without an integration
            # release; the relay validates and rejects what it doesn't take.
            vol.Optional(ATTR_EFFECT_PARAMS, default={}): dict,
        },
        "async_start_effect",
    )
    platform.async_register_entity_service(
        SERVICE_STOP_EFFECT, {}, "async_stop_effect"
    )


class ArtnetRelayBaseLight(LightEntity):
    """Shared colour/brightness handling for a set of strips on the relay."""

    _attr_should_poll = False
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_has_entity_name = True

    def __init__(self, hub: ArtnetRelayHub) -> None:
        self._hub = hub
        self._attr_brightness = 255
        self._attr_rgb_color = (255, 255, 255)
        self._attr_is_on = False
        self._unsub = None

    @property
    def device_info(self) -> dict[str, Any]:
        return self._hub.device_info

    @property
    def available(self) -> bool:
        return self._hub.available

    async def async_added_to_hass(self) -> None:
        self._unsub = self._hub.add_listener(self._handle_update)
        self._handle_update()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def _handle_update(self) -> None:
        self._apply_snapshot()
        self.async_write_ha_state()

    def _target_strips(self) -> list[dict[str, Any]]:
        """The snapshot entries this entity reflects."""
        raise NotImplementedError

    def _endpoint(self) -> str:
        """The relay path this entity writes to."""
        raise NotImplementedError

    def _apply_snapshot(self) -> None:
        strips = self._target_strips()
        if strips:
            first = strips[0]
            rgb = first.get("rgb")
            if isinstance(rgb, list) and len(rgb) == 3:
                self._attr_rgb_color = tuple(rgb)
            bri = first.get("brightness")
            if isinstance(bri, (int, float)):
                self._attr_brightness = max(0, min(255, int(round(bri * 255))))
        self._attr_is_on = any(
            isinstance(s.get("brightness"), (int, float)) and s["brightness"] > 0
            for s in strips
        )

    def _colour_body(self, **kwargs: Any) -> dict[str, Any]:
        if ATTR_RGB_COLOR in kwargs:
            self._attr_rgb_color = tuple(kwargs[ATTR_RGB_COLOR])
        if ATTR_BRIGHTNESS in kwargs:
            self._attr_brightness = kwargs[ATTR_BRIGHTNESS]
        return {
            "r": self._attr_rgb_color[0],
            "g": self._attr_rgb_color[1],
            "b": self._attr_rgb_color[2],
            "brightness": (self._attr_brightness or 255) / 255,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        body = self._colour_body(**kwargs)
        if ATTR_TRANSITION in kwargs:
            body["transition_ms"] = int(kwargs[ATTR_TRANSITION] * 1000)
        await self._hub.post(self._endpoint(), json_body=body)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Fade brightness to zero — honours transition, keeps the colour."""
        body = {
            "r": self._attr_rgb_color[0],
            "g": self._attr_rgb_color[1],
            "b": self._attr_rgb_color[2],
            "brightness": 0.0,
        }
        if ATTR_TRANSITION in kwargs:
            body["transition_ms"] = int(kwargs[ATTR_TRANSITION] * 1000)
        await self._hub.post(self._endpoint(), json_body=body)

    async def async_start_effect(self, effect: str, params: dict | None = None) -> None:
        raise HomeAssistantError(
            f"{self.entity_id}: effects run relay-wide, call this on the "
            "whole-relay light instead"
        )

    async def async_stop_effect(self) -> None:
        raise HomeAssistantError(
            f"{self.entity_id}: effects run relay-wide, call this on the "
            "whole-relay light instead"
        )


class ArtnetRelayLight(ArtnetRelayBaseLight):
    """Every strip on the relay, plus the relay-wide effect engine."""

    _attr_name = None  # the device name is the entity name
    _attr_supported_features = LightEntityFeature.TRANSITION | LightEntityFeature.EFFECT

    def __init__(self, hub: ArtnetRelayHub) -> None:
        super().__init__(hub)
        self._attr_unique_id = f"{hub.host}_{hub.port}_light"
        # Read off GET /effects at setup, so effects added to the relay show up
        # without touching this integration.
        self._attr_effect_list = hub.effects

    @property
    def effect(self) -> str | None:
        return self._hub.current_effect

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"effect_params": self._hub.current_effect_params}

    def _target_strips(self) -> list[dict[str, Any]]:
        return self._hub.strip_states()

    def _endpoint(self) -> str:
        return "/all"

    def _apply_snapshot(self) -> None:
        super()._apply_snapshot()
        # A running effect drives the strips directly; treat that as "on" even
        # if this frame happens to catch every strip dark.
        self._attr_is_on = bool(self._hub.current_effect) or self._attr_is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        effect = kwargs.get(ATTR_EFFECT)
        if effect:
            if effect not in self._hub.effects:
                raise HomeAssistantError(f"Unknown effect '{effect}'")
            await self._hub.post(f"/effects/{effect}", json_body=self._colour_body(**kwargs))
            return
        # Any plain colour command cancels the effect that would fight it.
        if self._hub.current_effect:
            await self._hub.post("/stop")
        await super().async_turn_on(**kwargs)

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self._hub.current_effect:
            await self._hub.post("/stop")
        await super().async_turn_off(**kwargs)

    async def async_start_effect(self, effect: str, params: dict | None = None) -> None:
        """Start an effect with explicit params (artnet_relay.start_effect)."""
        if effect not in self._hub.effects:
            raise HomeAssistantError(
                f"Unknown effect '{effect}'; relay offers: "
                f"{', '.join(self._hub.effects)}"
            )
        body = self._colour_body()
        body.update(params or {})
        if not await self._hub.post(f"/effects/{effect}", json_body=body):
            raise HomeAssistantError(f"Relay rejected effect '{effect}' with {params}")

    async def async_stop_effect(self) -> None:
        """Stop the running effect, leaving the strips as they are."""
        await self._hub.post("/stop")


class ArtnetRelayGroupLight(ArtnetRelayBaseLight):
    """One configured group of strips (POST /groups/{name})."""

    _attr_supported_features = LightEntityFeature.TRANSITION

    def __init__(self, hub: ArtnetRelayHub, group: str, members: list[str]) -> None:
        super().__init__(hub)
        self._group = group
        self._members = members
        self._attr_name = group.replace("_", " ").title()
        self._attr_unique_id = f"{hub.host}_{hub.port}_group_{group}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"strips": self._members}

    def _target_strips(self) -> list[dict[str, Any]]:
        return self._hub.strip_states(self._members)

    def _endpoint(self) -> str:
        return f"/groups/{self._group}"
