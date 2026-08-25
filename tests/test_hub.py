# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2024-2026 Schuberg Philis / Lab271
"""Tests for the relay hub's parsing of what the relay reports.

Home Assistant and aiohttp aren't installed in CI, so the few names hub.py
imports from them are stubbed. Everything under test here is pure parsing.
"""
import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PKG = _ROOT / "custom_components" / "artnet_relay"


def _stub(name: str, **attrs) -> None:
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module


def _load_hub():
    _stub("aiohttp", ClientError=Exception, ClientTimeout=lambda **kw: None)
    _stub("homeassistant")
    _stub("homeassistant.core", HomeAssistant=object)
    _stub("homeassistant.helpers")
    _stub(
        "homeassistant.helpers.aiohttp_client",
        async_get_clientsession=lambda hass: None,
    )
    package = types.ModuleType("artnet_relay")
    package.__path__ = [str(_PKG)]
    sys.modules["artnet_relay"] = package
    for name in ("const", "hub"):
        spec = importlib.util.spec_from_file_location(
            f"artnet_relay.{name}", _PKG / f"{name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"artnet_relay.{name}"] = module
        spec.loader.exec_module(module)
    return sys.modules["artnet_relay.hub"]


hub_module = _load_hub()


def _hub():
    return hub_module.ArtnetRelayHub(None, "Space Light", "192.0.2.20", 80)


class CurrentEffectTest(unittest.TestCase):
    """The relay reports the effect as {"name": ..., "params": {...}}."""

    def test_dict_effect_yields_name_and_params(self):
        h = _hub()
        h.state = {"effect": {"name": "aurora", "params": {"speed": 0.4}}}
        self.assertEqual(h.current_effect, "aurora")
        self.assertEqual(h.current_effect_params, {"speed": 0.4})

    def test_no_effect(self):
        h = _hub()
        h.state = {"effect": None}
        self.assertIsNone(h.current_effect)
        self.assertEqual(h.current_effect_params, {})

    def test_plain_string_effect_still_works(self):
        h = _hub()
        h.state = {"effect": "rainbow"}
        self.assertEqual(h.current_effect, "rainbow")
        self.assertEqual(h.current_effect_params, {})


class StripStatesTest(unittest.TestCase):
    def setUp(self):
        self.hub = _hub()
        self.hub.state = {
            "strips": [
                {"name": "a", "brightness": 1.0},
                {"name": "b", "brightness": 0.0},
                {"name": "c", "brightness": 0.5},
            ]
        }

    def test_all_strips(self):
        self.assertEqual(len(self.hub.strip_states()), 3)

    def test_filtered_by_group_members(self):
        got = [s["name"] for s in self.hub.strip_states(["a", "c", "missing"])]
        self.assertEqual(got, ["a", "c"])


class DiscoverTest(unittest.TestCase):
    """Capabilities come from the relay, never from a hardcoded list."""

    def setUp(self):
        self.hub = _hub()
        self.responses = {
            "/effects": {
                "effects": [
                    {"name": "rainbow", "params": [{"name": "speed", "default": 0.05}]},
                    {"name": "snake", "params": []},
                    {"name": "aurora", "params": [{"name": "scale", "default": 1.0}]},
                ]
            },
            "/info": {
                "effects": ["rainbow"],
                "scenes": ["warm_wit", "blackout"],
                "groups": ["universe_0"],
            },
            "/config": {"groups": {"universe_0": ["strip_1", "strip_2"]}},
        }

        async def _get(path):
            return self.responses.get(path)

        self.hub._get = _get

    def test_discovery_reads_effects_scenes_and_group_members(self):
        asyncio.run(self.hub.async_discover())
        self.assertEqual(self.hub.effects, ["rainbow", "snake", "aurora"])
        self.assertEqual(self.hub.effect_params["rainbow"], {"speed": 0.05})
        self.assertEqual(self.hub.scenes, ["warm_wit", "blackout"])
        self.assertEqual(self.hub.groups, {"universe_0": ["strip_1", "strip_2"]})

    def test_group_names_survive_a_config_endpoint_failure(self):
        self.responses["/config"] = None
        asyncio.run(self.hub.async_discover())
        self.assertEqual(self.hub.groups, {"universe_0": []})

    def test_effects_fall_back_to_info(self):
        self.responses["/effects"] = None
        asyncio.run(self.hub.async_discover())
        self.assertEqual(self.hub.effects, ["rainbow"])


if __name__ == "__main__":
    unittest.main()
