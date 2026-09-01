"""Calendar platform for XPS Network."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import XpsNetworkCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: XpsNetworkCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        XpsNetworkCalendar(coordinator, athlete_id)
        for athlete_id in coordinator.data["athletes"]
    )


class XpsNetworkCalendar(CoordinatorEntity[XpsNetworkCoordinator], CalendarEntity):
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: XpsNetworkCoordinator, athlete_id: str) -> None:
        super().__init__(coordinator)
        self._athlete_id = athlete_id
        self._attr_unique_id = f"{athlete_id}_calendar"
        athlete = coordinator.data["athletes"][athlete_id]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, athlete_id)},
            name=athlete.get("name"),
            manufacturer="XPS Network",
        )

    def _sessions(self) -> list[dict]:
        return self.coordinator.data["sessions_by_athlete"].get(self._athlete_id, [])

    @property
    def event(self) -> CalendarEvent | None:
        now = dt_util.utcnow()
        for session in self._sessions():
            if session["end"] >= now:
                return _to_calendar_event(session)
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return [
            _to_calendar_event(session)
            for session in self._sessions()
            if session["start"] < end_date and session["end"] > start_date
        ]


def _to_calendar_event(session: dict) -> CalendarEvent:
    summary = session["name"] or session["session_type"].capitalize()
    if session.get("cancelled"):
        summary = f"CANCELLED: {summary}"
    return CalendarEvent(
        start=session["start"],
        end=session["end"],
        summary=summary,
        description=session.get("description"),
        location=session.get("location"),
        uid=session["id"],
    )
