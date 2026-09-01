"""Config flow for XPS Network."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .api import XpsApiClient, XpsApiError, XpsAuthError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class XpsNetworkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for XPS Network."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            async with aiohttp.ClientSession() as session:
                client = XpsApiClient(
                    session, user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
                try:
                    await client.async_login()
                    members = await client.async_get_family_members()
                except XpsAuthError:
                    errors["base"] = "invalid_auth"
                except XpsApiError:
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"XPS Network ({user_input[CONF_USERNAME]})",
                        data=user_input,
                    )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
