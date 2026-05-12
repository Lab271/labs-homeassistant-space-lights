# labs-homeassistant-space-lights

Home Assistant custom integration that drives RGB lighting installations through the Lab271 [Art-Net Relay](https://github.com/Lab271/artnet-relay) REST API. Runs on the Lab271 Home Assistant instance and is also installable via HACS.

## Status

Active. Drives a Lab271 Art-Net Relay over its REST API. One whole-relay `light` entity per config entry exposes RGB color, brightness, transition, and the relay's 8 named effects (rainbow, chase, breathe, strobe, police, fire, sparkle, wave) via HA's standard light controls. Per-strip / per-group addressing and scenes are not wired up yet.

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
- One `light` entity per configured relay instance (RGB, brightness, transition, effects).
- Per-instance config flow (host + port + friendly name).

**Out of scope:**

- Direct Art-Net / sACN output — the relay does the pixel mapping. See [`artnet-relay`](https://github.com/Lab271/artnet-relay) for the upstream controller.
- Fixture-level addressing — entities are per relay instance, not per pixel.
- Audio / video routing — see the audio and videowall repos.

## Quick start

Install via HACS as a custom repository — in HACS → Integrations → ⋮ → *Custom repositories*, add this repo's URL with category *Integration*. Then install the **Art-Net Relay** integration and restart Home Assistant. Alternatively, copy `custom_components/artnet_relay/` into your Home Assistant `config/custom_components/` directory and restart.

Add the integration from **Settings → Devices & Services → Add Integration → Art-Net Relay** and enter:

- **Host** — the Art-Net Relay's IP or hostname.
- **Port** — the HTTP port the relay listens on (default `80`).
- **Name** — friendly name for the resulting light entity.

## Inventory / targets

Lab271 Art-Net Relay instances driving the lab's RGB LED strips. Hosts and ports are configured per-instance via the HA UI.

## Naming

Hostnames for the HA host and any networked Art-Net Relay follow the [Lab271 naming convention](https://github.com/Lab271/labs-infra-overview/blob/main/naming.md). The HA host itself uses `homeassistant` as a grandfathered exception per HA's own default.

## Dependencies

- Home Assistant 2024.x or newer (config flow + `async_forward_entry_setups`).
- A reachable [Art-Net Relay](https://github.com/Lab271/artnet-relay) endpoint on the configured `host:port`.
- No external secrets or API tokens.

## Owner

[`@LAB271`](.github/CODEOWNERS).
