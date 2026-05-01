# labs-homeassistant-space-lights

Home Assistant custom integration that maps stage groups on an [Enttec LED Mapper](https://www.enttec.com/) to Home Assistant `light` entities. Runs on the Lab271 Home Assistant instance and is also installable via HACS.

## Status

WIP. Drives the Lab271 stage strips today; HA UI exposes RGB color, brightness, and a curated set of ELM media effects.

## Rename history

This repo was previously named `ha-space-lights`. It was renamed to `labs-homeassistant-space-lights` to match the [Lab271 naming convention](https://github.com/LAB271/labs-infra-overview/blob/main/CONVENTIONS.md) (`labs-homeassistant-<thing>`). The integration domain was also renamed from its initial value to `enttec_led_mapper` so it groups with the device that actually drives the lights; this is a breaking change for any existing HA config entries under the old domain (remove and re-add the integration).

## Scope

**In scope:**

- Home Assistant custom component for ELM stages exposed over HTTP.
- One `light` entity per configured stage (RGB, brightness, effects).
- A `number` platform for any continuous parameters surfaced by the stage.
- Per-stage config flow (host + friendly name + ELM stage slug).

**Out of scope:**

- Direct Art-Net / sACN output — the ELM does the pixel mapping. See [`artnet-relay`](https://github.com/Lab271/artnet-relay) for the upstream Art-Net controller.
- Fixture-level addressing — entities are per stage, not per pixel.
- Audio / video routing — see the audio and videowall repos.

## Quick start

Install via HACS as a custom repository (point HACS at this repo URL), or copy `custom_components/enttec_led_mapper/` into your Home Assistant `config/custom_components/` directory and restart. Then add the integration from **Settings → Devices & Services → Add Integration → Enttec LED Mapper** and enter:

- **Host** — the ELM's IP or hostname.
- **Name** — friendly name for the resulting light entity.
- **Stage** — the ELM stage slug (the path component used in `/elm/stages/<stage>/live`).

## Inventory / targets

Enttec LED Mapper on the Lab271 AV network, driving the lab's stage LED strips. Hosts are configured per-instance via the HA UI.

## Naming

Hostnames for the HA host and any networked Enttec controller follow the [Lab271 naming convention](https://github.com/Lab271/labs-infra-overview/blob/main/naming.md). The HA host itself uses `homeassistant` as a grandfathered exception per HA's own default.

## Dependencies

- Home Assistant 2024.x or newer (config flow + `async_forward_entry_setups`).
- Network reachability from the HA host to the ELM over HTTP.
- No external secrets or API tokens.

## Owner

[`@LAB271`](.github/CODEOWNERS).
