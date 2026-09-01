"""Sensor platform for XPS Network."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
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
        XpsNetworkNextSessionSensor(coordinator, athlete_id)
        for athlete_id in coordinator.data["athletes"]
    )


class XpsNetworkNextSessionSensor(CoordinatorEntity[XpsNetworkCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Next session"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: XpsNetworkCoordinator, athlete_id: str) -> None:
        super().__init__(coordinator)
        self._athlete_id = athlete_id
        self._attr_unique_id = f"{athlete_id}_next_session"
        athlete = coordinator.data["athletes"][athlete_id]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, athlete_id)},
            name=athlete.get("name"),
            manufacturer="XPS Network",
        )

    def _next_session(self) -> dict | None:
        now = dt_util.utcnow()
        for session in self.coordinator.data["sessions_by_athlete"].get(self._athlete_id, []):
            if session["start"] >= now and not session.get("cancelled"):
                return session
        return None

    @property
    def native_value(self):
        session = self._next_session()
        return session["start"] if session else None

    @property
    def extra_state_attributes(self):
        session = self._next_session()
        if not session:
            return {}
        return {
            "name": session["name"],
            "end": session["end"],
            "location": session.get("location"),
            "team": session.get("team"),
            "session_type": session.get("session_type"),
            "attendance_status": session.get("attendance_status"),
            "session_id": session["id"],
        }
