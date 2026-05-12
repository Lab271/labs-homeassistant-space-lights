import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from .const import DOMAIN

class SpaceLightsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Space Lights."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default="192.0.2.20"): str,
                vol.Required(CONF_PORT, default=80): int,
                vol.Required(CONF_NAME, default="Space Light"): str,
            })
        )
