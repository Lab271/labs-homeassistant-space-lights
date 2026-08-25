# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2024-2026 Schuberg Philis / Lab271
"""Constants for the Art-Net Relay integration."""

DOMAIN = "artnet_relay"

PLATFORMS = ["light", "scene"]

# Seconds to wait before reconnecting a dropped /events stream.
SSE_RECONNECT_DELAY = 5

# Timeout for one-shot REST calls (the SSE stream uses no read timeout).
REQUEST_TIMEOUT = 5

# Effects the relay accepts a colour for. Every effect ignores the kwargs it
# doesn't declare (the relay filters against each effect's signature), so we
# always send the common r/g/b/brightness bag.
SERVICE_START_EFFECT = "start_effect"
SERVICE_STOP_EFFECT = "stop_effect"

ATTR_EFFECT_PARAMS = "params"
