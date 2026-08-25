# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2024-2026 Schuberg Philis / Lab271
"""Shared connection to one artnet-relay instance.

Every entity from a config entry talks to the relay through this hub, so the
relay sees a single /events subscriber no matter how many lights and scenes
Home Assistant creates from it.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, REQUEST_TIMEOUT, SSE_RECONNECT_DELAY

_LOGGER = logging.getLogger(__name__)


class ArtnetRelayHub:
    """REST + SSE client for one relay, plus the capabilities it reports."""

    def __init__(self, hass: HomeAssistant, name: str, host: str, port: int) -> None:
        self.hass = hass
        self.name = name
        self.host = host
        self.port = port
        self.available = False
        self.state: dict[str, Any] = {}
        # Discovered at setup from /effects, /info and /config — the relay is the
        # source of truth for what it can do, so nothing here is hardcoded.
        self.effects: list[str] = []
        self.effect_params: dict[str, dict[str, Any]] = {}
        self.scenes: list[str] = []
        self.groups: dict[str, list[str]] = {}
        self._listeners: list[Callable[[], None]] = []
        self._sse_task: asyncio.Task | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def device_id(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": self.name,
            "manufacturer": "Lab271",
            "model": "Art-Net Relay",
            "configuration_url": self.base_url,
        }

    @property
    def current_effect(self) -> str | None:
        """Name of the running effect.

        The relay reports `{"name": ..., "params": {...}}`; Home Assistant wants
        the bare name.
        """
        effect = self.state.get("effect")
        if isinstance(effect, dict):
            return effect.get("name")
        if isinstance(effect, str):
            return effect
        return None

    @property
    def current_effect_params(self) -> dict[str, Any]:
        effect = self.state.get("effect")
        if isinstance(effect, dict) and isinstance(effect.get("params"), dict):
            return effect["params"]
        return {}

    def strip_states(self, names: list[str] | None = None) -> list[dict[str, Any]]:
        """Snapshot entries for `names`, or for every strip when None."""
        strips = self.state.get("strips") or []
        if names is None:
            return strips
        wanted = set(names)
        return [s for s in strips if s.get("name") in wanted]

    # ------------------------------------------------------------
    # Lifecycle

    async def async_discover(self) -> None:
        """Read the relay's capabilities. Failures leave the lists empty."""
        effects = await self._get("/effects")
        if isinstance(effects, dict):
            listed = effects.get("effects") or []
            self.effects = [e["name"] for e in listed if e.get("name")]
            self.effect_params = {
                e["name"]: {
                    p["name"]: p.get("default")
                    for p in (e.get("params") or [])
                    if p.get("name")
                }
                for e in listed
                if e.get("name")
            }

        info = await self._get("/info")
        if isinstance(info, dict):
            self.scenes = list(info.get("scenes") or [])
            if not self.effects:
                self.effects = list(info.get("effects") or [])

        # /info only names the groups; /config carries their membership, which is
        # what a group light needs to read its own state out of the snapshot.
        config = await self._get("/config")
        if isinstance(config, dict):
            groups = config.get("groups") or {}
            self.groups = {
                name: list(members)
                for name, members in groups.items()
                if isinstance(members, list)
            }
        elif info and isinstance(info, dict):
            self.groups = {name: [] for name in (info.get("groups") or [])}

    def start(self) -> None:
        if self._sse_task is None or self._sse_task.done():
            self._sse_task = self.hass.loop.create_task(self._sse_loop())

    async def stop(self) -> None:
        if self._sse_task and not self._sse_task.done():
            self._sse_task.cancel()
            try:
                await self._sse_task
            except asyncio.CancelledError:
                pass
        self._sse_task = None

    def add_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Register a state callback; returns the unsubscribe function."""
        self._listeners.append(callback)

        def _remove() -> None:
            if callback in self._listeners:
                self._listeners.remove(callback)

        return _remove

    def _notify(self) -> None:
        for callback in list(self._listeners):
            callback()

    # ------------------------------------------------------------
    # REST

    async def _get(self, path: str) -> Any | None:
        url = f"{self.base_url}{path}"
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as response:
                response.raise_for_status()
                return await response.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            _LOGGER.warning("GET %s failed: %s", url, err)
            return None

    async def post(
        self,
        path: str,
        json_body: dict | None = None,
        params: dict | None = None,
    ) -> bool:
        url = f"{self.base_url}{path}"
        session = async_get_clientsession(self.hass)
        try:
            async with session.post(
                url,
                json=json_body,
                params=params,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                response.raise_for_status()
                return True
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("POST %s failed: %s", url, err)
            return False

    # ------------------------------------------------------------
    # SSE

    async def _sse_loop(self) -> None:
        url = f"{self.base_url}/events"
        session = async_get_clientsession(self.hass)
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
                        if payload.get("type") != "state":
                            continue
                        self.state = payload.get("state") or {}
                        self.available = True
                        self._notify()
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 - keep the stream alive
                _LOGGER.warning(
                    "SSE stream to %s dropped (%s); reconnecting in %ds",
                    url,
                    err,
                    SSE_RECONNECT_DELAY,
                )
                if self.available:
                    self.available = False
                    self._notify()
                await asyncio.sleep(SSE_RECONNECT_DELAY)
