"""Data update coordinator for XPS Network."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import XpsApiClient, XpsApiError, XpsAuthError
from .const import (
    AGENDA_PAGE_SIZE,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    SCHEDULE_LOOKAHEAD_DAYS,
    SCHEDULE_LOOKBACK_DAYS,
)

_LOGGER = logging.getLogger(__name__)


class XpsNetworkCoordinator(DataUpdateCoordinator):
    """Fetches family members + upcoming agenda from XPS Network."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: XpsApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="XPS Network",
            update_interval=timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES),
        )
        self.entry = entry
        self.client = client

    async def _async_update_data(self) -> dict:
        try:
            members = await self.client.async_get_family_members()
            lookback = dt_util.utcnow() - timedelta(days=SCHEDULE_LOOKBACK_DAYS)
            from_epoch_ms = int(lookback.timestamp() * 1000)
            raw_sessions = await self.client.async_get_agenda(
                from_epoch_ms, first=AGENDA_PAGE_SIZE
            )
        except XpsAuthError as err:
            raise UpdateFailed(
                "XPS Network login was rejected - check the username/password in the "
                "integration options"
            ) from err
        except XpsApiError as err:
            raise UpdateFailed(str(err)) from err

        athletes = {member["id"]: member for member in members if member.get("id")}
        lookahead_cutoff = dt_util.utcnow() + timedelta(days=SCHEDULE_LOOKAHEAD_DAYS)
        sessions_by_athlete: dict[str, list[dict]] = {athlete_id: [] for athlete_id in athletes}

        for raw in raw_sessions:
            start = _parse_epoch_ms(raw.get("start"))
            if start is None or start > lookahead_cutoff:
                continue
            duration = raw.get("durationMinutes") or 0
            end = start + timedelta(minutes=duration) if duration else start

            for attendance in raw.get("attendance") or []:
                athlete_id = attendance.get("athleteGuid")
                if athlete_id not in athletes:
                    continue
                sessions_by_athlete[athlete_id].append(
                    {
                        "id": raw.get("id"),
                        "name": raw.get("label"),
                        "description": raw.get("notes"),
                        "start": start,
                        "end": end,
                        "location": raw.get("location"),
                        "team": raw.get("teamName"),
                        "session_type": raw.get("session_type"),
                        "cancelled": raw.get("cancelled", False),
                        "attendance_status": attendance.get("attendance"),
                        "athlete_comment": attendance.get("athleteComment"),
                    }
                )

        for athlete_id in sessions_by_athlete:
            sessions_by_athlete[athlete_id].sort(key=lambda e: e["start"])

        return {"athletes": athletes, "sessions_by_athlete": sessions_by_athlete}


def _parse_epoch_ms(value) -> datetime | None:
    if value is None:
        return None
    try:
        return dt_util.utc_from_timestamp(int(value) / 1000)
    except (TypeError, ValueError):
        return None
