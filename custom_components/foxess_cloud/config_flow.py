"""Config flow for Fox ESS Cloud integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FoxESSAuthError, FoxESSCloudApi, FoxESSConnectionError
from .const import (
    CONF_API_KEY,
    CONF_DEVICE_SN,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
)


async def _validate_api_key(
    hass: HomeAssistant, api_key: str
) -> list[dict[str, Any]]:
    """Validate the API key by fetching the device list."""
    session = async_get_clientsession(hass)
    api = FoxESSCloudApi(session, api_key)
    devices = await api.get_device_list()
    if not devices:
        raise NoDevicesFound
    return devices


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fox ESS Cloud."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._api_key: str | None = None
        self._devices: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: Enter API key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            try:
                self._devices = await _validate_api_key(self.hass, api_key)
                self._api_key = api_key
                return await self.async_step_device()
            except FoxESSAuthError:
                errors["base"] = "invalid_auth"
            except FoxESSConnectionError:
                errors["base"] = "cannot_connect"
            except NoDevicesFound:
                errors["base"] = "no_devices"
            except Exception:  # noqa: BLE001
                LOGGER.exception("Unexpected exception during config flow")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2: Select device from discovered list."""
        errors: dict[str, str] = {}

        if user_input is not None:
            device_sn = user_input[CONF_DEVICE_SN]

            # Prevent duplicate entries for the same device
            await self.async_set_unique_id(device_sn)
            self._abort_if_unique_id_configured()

            # Find device info for the title
            device_name = device_sn
            for dev in self._devices:
                if dev.get("deviceSN") == device_sn:
                    device_name = dev.get("deviceType", device_sn)
                    break

            return self.async_create_entry(
                title=f"Fox ESS {device_name} ({device_sn})",
                data={
                    CONF_API_KEY: self._api_key,
                    CONF_DEVICE_SN: device_sn,
                },
            )

        # Build a dropdown of available devices
        device_options = {}
        for dev in self._devices:
            sn = dev.get("deviceSN", "")
            dtype = dev.get("deviceType", "Unknown")
            station = dev.get("stationName", "")
            label = f"{dtype} - {sn}"
            if station:
                label += f" ({station})"
            device_options[sn] = label

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {vol.Required(CONF_DEVICE_SN): vol.In(device_options)}
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Get the options flow handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Fox ESS Cloud."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=current_interval,
                    ): vol.All(vol.Coerce(int), vol.Range(min=3, max=60)),
                }
            ),
        )


class NoDevicesFound(HomeAssistantError):
    """Error to indicate no devices found."""
