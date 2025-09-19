import logging
import re
from datetime import timedelta
from typing import Any

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_DEVICE_NAME, CONF_UPDATE_INTERVAL, DOMAIN, redact_url

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api_url = entry.data[CONF_URL]
    device_name = entry.data[CONF_DEVICE_NAME]
    update_interval = timedelta(seconds=entry.data[CONF_UPDATE_INTERVAL])

    session = async_get_clientsession(hass)

    async def async_update_data() -> dict[str, Any]:
        try:
            async with async_timeout.timeout(30):
                _LOGGER.debug(
                    "Fetching data from PhoneTrack API: %s", redact_url(api_url)
                )
                resp = await session.get(api_url)
                resp.raise_for_status()

                try:
                    data = await resp.json()
                except Exception as json_err:
                    response_text = await resp.text()
                    _LOGGER.debug(
                        "Failed to parse JSON from PhoneTrack API %s. "
                        "Response snippet: %s",
                        redact_url(api_url),
                        (
                            response_text[:200] + "..."
                            if len(response_text) > 200
                            else response_text
                        ),
                    )
                    raise UpdateFailed(
                        f"Invalid JSON response: {json_err}"
                    ) from json_err

                if not data or not isinstance(data, dict):
                    raise UpdateFailed("Unexpected API response format")

                token_data = next(iter(data.values()), None)
                if not token_data or device_name not in token_data:
                    available_devices = list(token_data.keys()) if token_data else []
                    _LOGGER.warning(
                        "Device '%s' not found in PhoneTrack response. "
                        "Available devices: %s",
                        device_name,
                        available_devices,
                    )
                    raise UpdateFailed(
                        f"Device '{device_name}' temporarily unavailable"
                    )

                _LOGGER.debug("Successfully fetched data for device '%s'", device_name)
                return token_data[device_name]

        except Exception as err:
            if isinstance(err, UpdateFailed):
                raise
            _LOGGER.exception(
                "Unexpected error fetching PhoneTrack data from %s",
                redact_url(api_url),
            )
            raise UpdateFailed(f"Error fetching PhoneTrack data: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"PhoneTrack {device_name}",
        update_method=async_update_data,
        update_interval=update_interval,
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as err:
        raise ConfigEntryNotReady(
            f"Failed to validate PhoneTrack configuration: {err}"
        ) from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
