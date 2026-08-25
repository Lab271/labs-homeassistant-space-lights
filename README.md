# labs-homeassistant-space-lights

Home Assistant custom integration that drives RGB lighting installations through the Lab271 [Art-Net Relay](https://github.com/Lab271/labs-artnet-relay) REST API. Runs on the Lab271 Home Assistant instance and is also installable via HACS.

## Status

Active. Drives a Lab271 Art-Net Relay over its REST API and subscribes to the relay's `/events` SSE stream for real-time state — one shared stream per config entry, however many entities it creates.

Entities are built from what the relay reports at setup, not from a hardcoded list:

- **Whole-relay light** (`POST /all`) — RGB, brightness, transition, and every effect the relay lists on `GET /effects`. That is currently 17: `rainbow`, `chase`, `breathe`, `strobe`, `police`, `fire`, `sparkle`, `wave`, `comet`, `snake`, and the field effects `spot`, `ripple`, `plasma`, `blobs`, `tunnel`, `sweep`, `aurora`. Effects added to the relay appear in Home Assistant after a reload, with no integration release.
- **One light per group** (`POST /groups/{name}`) — RGB, brightness, transition. Group membership comes from `GET /config`, so a group light reads its own state out of the SSE snapshot.
- **One scene entity per relay scene** (`POST /scenes/{name}`).
- **Services** `artnet_relay.start_effect` and `artnet_relay.stop_effect` for effects with explicit parameters (direction, spread, x/y, diameter, …), which HA's built-in effect picker can't pass.

External changes (relay web UI, other clients) propagate to HA without polling. Per-strip and per-pixel addressing are not wired up yet.

## Rename history

This repo was previously named `ha-space-lights` and was renamed to `labs-homeassistant-space-lights` to match the [Lab271 naming convention](https://github.com/LAB271/labs-infra-overview/blob/main/CONVENTIONS.md) (`labs-homeassistant-<thing>`).

The HA integration domain has also been renamed twice. Each domain rename is a breaking change for existing HA config entries (remove and re-add the integration after upgrading):

| Old domain | New domain | Reason |
| --- | --- | --- |
| (initial) | `enttec_led_mapper` | grouped the integration with the device that drove the lights |
| `enttec_led_mapper` | `artnet_relay` | reflects the upstream service the integration now talks to (the Art-Net Relay REST API) |

## Scope

**In scope:**

- Home Assistant custom component that talks to a Lab271 Art-Net Relay endpoint over HTTP.
- One whole-relay `light` entity plus one per relay group (RGB, brightness, transition; effects on the whole-relay light).
- `scene` entities for the scenes defined in the relay's `config.yaml`.
- Services for starting an effect with explicit parameters and for stopping it.
- Per-instance config flow (host + port + friendly name).

**Out of scope:**

- Direct Art-Net / sACN output — the relay does the pixel mapping. See [`labs-artnet-relay`](https://github.com/Lab271/labs-artnet-relay) for the upstream controller.
- Fixture-level addressing — entities go down to relay groups, not to individual strips or pixels.
- Audio / video routing — see the audio and videowall repos.

## Quick start

Install via HACS as a custom repository — in HACS → Integrations → ⋮ → *Custom repositories*, add this repo's URL with category *Integration*. Then install the **Art-Net Relay** integration and restart Home Assistant. Alternatively, copy `custom_components/artnet_relay/` into your Home Assistant `config/custom_components/` directory and restart.

Add the integration from **Settings → Devices & Services → Add Integration → Art-Net Relay** and enter:

- **Host** — the Art-Net Relay's IP or hostname.
- **Port** — the HTTP port the relay listens on (default `80`).
- **Name** — friendly name for the resulting device.

Effects with parameters go through the service, targeting the whole-relay light:

```yaml
service: artnet_relay.start_effect
target:
  entity_id: light.space_light
data:
  effect: aurora
  params:
    speed: 0.4
    scale: 3.0
```

The relay ignores parameters an effect doesn't declare, and rejects out-of-range ones with a 422.

## Inventory / targets

Lab271 Art-Net Relay instances driving the lab's RGB LED strips. Hosts and ports are configured per-instance via the HA UI.

## Naming

Hostnames for the HA host and any networked Art-Net Relay follow the [Lab271 naming convention](https://github.com/Lab271/labs-infra-overview/blob/main/naming.md). The HA host itself uses `homeassistant` as a grandfathered exception per HA's own default.

## Dependencies

- Home Assistant 2024.x or newer (config flow + `async_forward_entry_setups`).
- A reachable [Art-Net Relay](https://github.com/Lab271/labs-artnet-relay) endpoint on the configured `host:port`.
- No external secrets or API tokens.

## Owner

[@LAB271](https://github.com/orgs/Lab271/people).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

Please report vulnerabilities privately, not as a GitHub issue. See
[SECURITY.md](SECURITY.md).

## License

Copyright 2024-2026 Schuberg Philis B.V.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use
these files except in compliance with the License. You may obtain a copy of the
License in [LICENSE](LICENSE) or at <https://www.apache.org/licenses/LICENSE-2.0>.

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
language governing permissions and limitations under the License.
