from typing import Any
from datetime import timedelta

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util.dt import utc_from_timestamp, as_local, utcnow
from homeassistant.util import slugify

from .const import (
    CONF_DEVICE_NAME,
    CONF_LAST_UPDATE_TIMEOUT,
    CONF_MAX_GPS_ACCURACY,
    DOMAIN,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]
    device_name = entry.data[CONF_DEVICE_NAME]
    max_gps_accuracy = entry.data[CONF_MAX_GPS_ACCURACY]
    last_update_timeout = entry.data[CONF_LAST_UPDATE_TIMEOUT]

    async_add_entities(
        [
            PhoneTrackDeviceTracker(
                coordinator,
                device_name,
                entry.entry_id,
                max_gps_accuracy,
                last_update_timeout,
            )
        ]
    )


class PhoneTrackDeviceTracker(CoordinatorEntity, TrackerEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_source_type = SourceType.GPS

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device_name: str,
        entry_id: str,
        max_gps_accuracy: int,
        last_update_timeout: int,
    ) -> None:
        super().__init__(coordinator)
        self._device_name = device_name
        self._entry_id = entry_id
        self._max_gps_accuracy = max_gps_accuracy
        self._last_update_timeout = last_update_timeout
        self._attr_unique_id = slugify(f"{entry_id}_{self._device_name}")

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id or "")},
            name=self._device_name,
            manufacturer="PhoneTrack",
            model="Tracked Device",
            sw_version="1.0.0",
        )

    @property
    def _data(self) -> dict[str, Any] | None:
        return self.coordinator.data

    @property
    def available(self) -> bool:
        return (
            self.coordinator.last_update_success
            and self._data is not None
            and self._is_accurate_enough()
            and self._is_within_timeout()
        )

    @property
    def latitude(self) -> float | None:
        if self._data and self._is_accurate_enough():
            lat = self._data.get("lat")
            return float(lat) if lat is not None else None
        return None

    @property
    def longitude(self) -> float | None:
        if self._data and self._is_accurate_enough():
            lon = self._data.get("lon")
            return float(lon) if lon is not None else None
        return None

    @property
    def battery_level(self) -> int | None:
        if self._data and (batt := self._data.get("batterylevel")) is not None:
            try:
                batt = int(float(batt))
                return max(0, min(100, batt))
            except (ValueError, TypeError):
                return None
        return None

    @property
    def location_accuracy(self) -> int:
        if self._data and (acc := self._data.get("accuracy")) is not None:
            try:
                return int(acc)
            except (ValueError, TypeError):
                return 0
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self._data:
            return {}

        last_seen = self._data.get("timestamp")
        if last_seen is not None:
            try:
                last_seen = as_local(utc_from_timestamp(float(last_seen)))
            except (ValueError, TypeError, OSError):
                pass

        attributes = {
            "device_name": self._device_name,
            "battery_level": self._data.get("batterylevel"),
            "last_seen": last_seen,
        }

        return attributes

    def _is_accurate_enough(self) -> bool:
        acc = self._data.get("accuracy") if self._data else None
        try:
            if acc is None:
                return False
            acc = float(acc)
            return 0 < acc <= self._max_gps_accuracy
        except (ValueError, TypeError):
            return False

    def _is_within_timeout(self) -> bool:
        if not self._data:
            return False

        timestamp = self._data.get("timestamp")
        if timestamp is None:
            return False

        try:
            last_update = utc_from_timestamp(float(timestamp))
            timeout_threshold = utcnow() - timedelta(minutes=self._last_update_timeout)
            return last_update > timeout_threshold
        except (ValueError, TypeError, OSError):
            return False
