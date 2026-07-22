# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2024-2026 Schuberg Philis / Lab271
"""Art-Net Relay light platform."""

import asyncio
import json
import logging
from typing import Any

import aiohttp

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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

EFFECTS = ["rainbow", "chase", "breathe", "strobe", "police", "fire", "sparkle", "wave"]

SSE_RECONNECT_DELAY = 5


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up the Art-Net Relay light from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [ArtnetRelayLight(hass, data["name"], data["host"], data["port"])]
    )


class ArtnetRelayLight(LightEntity):
    """A whole-relay light entity controlled via the artnet-relay /all endpoint."""

    _attr_should_poll = False
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_supported_features = LightEntityFeature.TRANSITION | LightEntityFeature.EFFECT
    _attr_effect_list = EFFECTS

    def __init__(self, hass: HomeAssistant, name: str, host: str, port: int) -> None:
        self._hass = hass
        self._attr_name = name
        self._host = host
        self._port = port
        self._attr_unique_id = f"{host}_{port}_light"
        self._attr_is_on = False
        self._attr_brightness = 255
        self._attr_rgb_color = (255, 255, 255)
        self._attr_effect = None
        self._attr_available = False
        self._sse_task: asyncio.Task | None = None

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, f"{self._host}:{self._port}")},
            "name": self._attr_name,
            "manufacturer": "Lab271",
            "model": "Art-Net Relay",
        }

    @property
    def _base_url(self) -> str:
        return f"http://{self._host}:{self._port}"

    async def async_added_to_hass(self) -> None:
        self._sse_task = self._hass.loop.create_task(self._sse_loop())

    async def async_will_remove_from_hass(self) -> None:
        if self._sse_task and not self._sse_task.done():
            self._sse_task.cancel()
            try:
                await self._sse_task
            except asyncio.CancelledError:
                pass

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the lights on, applying any color/brightness/transition/effect kwargs."""
        if ATTR_RGB_COLOR in kwargs:
            self._attr_rgb_color = tuple(kwargs[ATTR_RGB_COLOR])
        if ATTR_BRIGHTNESS in kwargs:
            self._attr_brightness = kwargs[ATTR_BRIGHTNESS]

        body: dict[str, Any] = {
            "r": self._attr_rgb_color[0],
            "g": self._attr_rgb_color[1],
            "b": self._attr_rgb_color[2],
            "brightness": (self._attr_brightness or 255) / 255,
        }

        if ATTR_EFFECT in kwargs and kwargs[ATTR_EFFECT] in EFFECTS:
            effect = kwargs[ATTR_EFFECT]
            await self._post(f"/effects/{effect}", json=body)
            return

        if ATTR_TRANSITION in kwargs:
            body["transition_ms"] = int(kwargs[ATTR_TRANSITION] * 1000)

        await self._post("/all", json=body)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the lights off by fading brightness to zero (honours transition)."""
        body: dict[str, Any] = {
            "r": self._attr_rgb_color[0],
            "g": self._attr_rgb_color[1],
            "b": self._attr_rgb_color[2],
            "brightness": 0.0,
        }
        if ATTR_TRANSITION in kwargs:
            body["transition_ms"] = int(kwargs[ATTR_TRANSITION] * 1000)

        await self._post("/all", json=body)

    async def _post(self, path: str, json: dict | None = None) -> bool:
        url = f"{self._base_url}{path}"
        session = async_get_clientsession(self._hass)
        try:
            async with session.post(
                url,
                json=json,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                response.raise_for_status()
                return True
        except aiohttp.ClientError as e:
            _LOGGER.error("POST %s failed: %s", url, e)
            return False

    async def _sse_loop(self) -> None:
        url = f"{self._base_url}/events"
        session = async_get_clientsession(self._hass)
        while True:
            try:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=None, sock_read=None),
                ) as resp:
                    resp.raise_for_status()
                    while True:
                        line = await resp.content.readline()
                        if not line:
                            break
                        decoded = line.decode("utf-8").strip()
                        if not decoded.startswith("data:"):
                            continue
                        try:
                            payload = json.loads(decoded[5:].strip())
                        except json.JSONDecodeError:
                            continue
                        if payload.get("type") == "state":
                            self._apply_snapshot(payload.get("state") or {})
                            self._attr_available = True
                            self.async_write_ha_state()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                _LOGGER.warning("SSE stream to %s dropped (%s); reconnecting in %ds",
                                url, e, SSE_RECONNECT_DELAY)
                if self._attr_available:
                    self._attr_available = False
                    self.async_write_ha_state()
                await asyncio.sleep(SSE_RECONNECT_DELAY)

    def _apply_snapshot(self, state: dict) -> None:
        strips = state.get("strips") or []
        if strips:
            first = strips[0]
            rgb = first.get("rgb")
            if isinstance(rgb, list) and len(rgb) == 3:
                self._attr_rgb_color = tuple(rgb)
            bri = first.get("brightness")
            if isinstance(bri, (int, float)):
                self._attr_brightness = max(0, min(255, int(round(bri * 255))))
        self._attr_effect = state.get("effect")
        any_on = any(
            isinstance(s.get("brightness"), (int, float)) and s["brightness"] > 0
            for s in strips
        )
        self._attr_is_on = bool(self._attr_effect) or any_on
