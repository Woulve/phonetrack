from __future__ import annotations

import logging
import re
from typing import Any

import async_timeout
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_DEVICE_NAME,
    CONF_LAST_UPDATE_TIMEOUT,
    CONF_MAX_GPS_ACCURACY,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
    redact_url,
)

_LOGGER = logging.getLogger(__name__)


class InvalidURL(HomeAssistantError):
    """Error to indicate invalid URL format."""


class InvalidPhoneTrackURL(HomeAssistantError):
    """Error to indicate URL is not a valid PhoneTrack endpoint."""


class InvalidDeviceName(HomeAssistantError):
    """Error to indicate invalid device name."""


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect to PhoneTrack."""


class DeviceNotFound(HomeAssistantError):
    """Error to indicate device was not found in PhoneTrack."""


class InvalidTimeoutConfiguration(HomeAssistantError):
    """Error to indicate timeout is too short relative to polling interval."""


def _normalize_url(url: str) -> str:
    return url.strip().rstrip("/")


def _normalize_device_name(name: str) -> str:
    return name.strip()


class PhoneTrackConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await self._validate_input(user_input)
            except InvalidURL:
                errors["base"] = "invalid_url"
            except InvalidPhoneTrackURL:
                errors["base"] = "invalid_phonetrack_url"
            except InvalidDeviceName:
                errors["base"] = "invalid_device_name"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except DeviceNotFound:
                errors["base"] = "device_not_found"
            except InvalidTimeoutConfiguration:
                errors["base"] = "invalid_timeout_configuration"
            except Exception:
                _LOGGER.exception("Unexpected exception during validation")
                errors["base"] = "unknown"
            else:
                unique_id = f"{info[CONF_URL]}_{info[CONF_DEVICE_NAME]}".lower()
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info[CONF_NAME],
                    data=info,
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_URL): str,
                vol.Required(CONF_DEVICE_NAME): str,
                vol.Required(CONF_NAME, default="PhoneTrack"): str,
                vol.Required(CONF_MAX_GPS_ACCURACY, default=100): vol.Coerce(int),
                vol.Required(CONF_UPDATE_INTERVAL, default=60): vol.Coerce(int),
                vol.Required(CONF_LAST_UPDATE_TIMEOUT, default=30): vol.Coerce(int),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "url": "Full PhoneTrack API endpoint with token",
                "device_name": "Name of the device as reported by PhoneTrack",
                "name": "Friendly name for this integration in Home Assistant",
                "max_gps_accuracy": (
                    "Maximum allowed GPS accuracy (in meters). "
                    "Location updates with worse accuracy will be ignored."
                ),
                "update_interval": (
                    "How often to poll the PhoneTrack API (in seconds)."
                ),
                "last_update_timeout": (
                    "Mark device as unavailable after this many minutes "
                    "without updates."
                ),
            },
        )

    async def _validate_input(self, data: dict[str, Any]) -> dict[str, Any]:
        api_url = _normalize_url(data[CONF_URL])
        device_name = _normalize_device_name(data[CONF_DEVICE_NAME])

        if not api_url or not re.match(r"^https?://", api_url):
            raise InvalidURL("URL must be a valid HTTP/HTTPS URL")
        if "getlastpositions" not in api_url:
            raise InvalidPhoneTrackURL(
                "URL must be a PhoneTrack getlastpositions endpoint"
            )
        if not device_name:
            raise InvalidDeviceName("Device name cannot be empty")

        update_interval_minutes = data[CONF_UPDATE_INTERVAL] / 60.0
        timeout_minutes = data[CONF_LAST_UPDATE_TIMEOUT]
        if timeout_minutes < (update_interval_minutes * 2):
            raise InvalidTimeoutConfiguration(
                f"Timeout ({timeout_minutes} min) must be at least 2x the polling "
                f"interval ({update_interval_minutes:.1f} min)"
            )

        session = async_get_clientsession(self.hass)
        try:
            async with async_timeout.timeout(10):
                _LOGGER.debug(
                    "Testing connection to PhoneTrack API: %s", redact_url(api_url)
                )
                resp = await session.get(api_url)
                if resp.status != 200:
                    _LOGGER.warning(
                        "PhoneTrack API test failed with HTTP %s for %s",
                        resp.status,
                        redact_url(api_url),
                    )
                    raise CannotConnect(f"API returned HTTP {resp.status}")

                try:
                    api_data = await resp.json()
                except Exception as json_err:
                    _LOGGER.debug(
                        "Failed to parse JSON from PhoneTrack API during validation"
                    )
                    raise CannotConnect("API returned invalid JSON") from json_err

                if not api_data or not isinstance(api_data, dict):
                    raise CannotConnect("API returned unexpected response format")

                token_data = next(iter(api_data.values()), None)
                if not token_data or device_name not in token_data:
                    available_devices = list(token_data.keys()) if token_data else []
                    _LOGGER.debug(
                        "Device '%s' not found during validation. Available: %s",
                        device_name,
                        available_devices,
                    )
                    raise DeviceNotFound(
                        f"Device '{device_name}' not found. "
                        f"Available devices: {available_devices}"
                    )

                _LOGGER.debug("Successfully validated PhoneTrack configuration")

        except (CannotConnect, DeviceNotFound):
            raise
        except Exception as err:
            _LOGGER.exception("Unexpected error during API validation")
            raise CannotConnect(f"Failed to connect to API: {err}") from err

        return {
            CONF_URL: api_url,
            CONF_DEVICE_NAME: device_name,
            CONF_NAME: data[CONF_NAME],
            CONF_MAX_GPS_ACCURACY: data[CONF_MAX_GPS_ACCURACY],
            CONF_UPDATE_INTERVAL: data[CONF_UPDATE_INTERVAL],
            CONF_LAST_UPDATE_TIMEOUT: data[CONF_LAST_UPDATE_TIMEOUT],
        }
