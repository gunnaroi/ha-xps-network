"""The XPS Network integration."""
from __future__ import annotations

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .api import XpsApiClient, XpsApiError
from .const import (
    ATTENDANCE_STATUSES,
    ATTR_ATHLETE_ID,
    ATTR_COMMENT,
    ATTR_SESSION_ID,
    ATTR_STATUS,
    DOMAIN,
    SERVICE_SET_ATTENDANCE,
)
from .coordinator import XpsNetworkCoordinator

PLATFORMS = ["calendar", "sensor"]

SET_ATTENDANCE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ATHLETE_ID): cv.string,
        vol.Required(ATTR_SESSION_ID): cv.string,
        vol.Required(ATTR_STATUS): vol.In(ATTENDANCE_STATUSES),
        vol.Optional(ATTR_COMMENT, default=""): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = aiohttp.ClientSession()
    client = XpsApiClient(session, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    coordinator = XpsNetworkCoordinator(hass, entry, client)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
        "session": session,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _handle_set_attendance(call: ServiceCall) -> None:
        for entry_data in hass.data[DOMAIN].values():
            try:
                await entry_data["client"].async_set_attendance(
                    call.data[ATTR_SESSION_ID],
                    call.data[ATTR_ATHLETE_ID],
                    call.data[ATTR_STATUS],
                    call.data[ATTR_COMMENT],
                )
            except XpsApiError as err:
                raise HomeAssistantError(f"XPS Network: {err}") from err
            await entry_data["coordinator"].async_request_refresh()
            return

    hass.services.async_register(
        DOMAIN, SERVICE_SET_ATTENDANCE, _handle_set_attendance, schema=SET_ATTENDANCE_SCHEMA
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        await entry_data["session"].close()
    return unload_ok
