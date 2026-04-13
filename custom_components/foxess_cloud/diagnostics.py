"""Diagnostics support for Fox ESS Cloud."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, DOMAIN
from .coordinator import FoxESSCloudCoordinator

TO_REDACT = {CONF_API_KEY, "device_sn"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: FoxESSCloudCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Redact sensitive fields from coordinator data
    safe_data = None
    if coordinator.data:
        safe_data = {
            k: v for k, v in coordinator.data.items()
            if k != "device_detail"
        }
        # Include device_detail without sensitive fields
        detail = coordinator.data.get("device_detail", {})
        safe_data["device_detail"] = {
            k: v for k, v in detail.items()
            if k not in ("deviceSN", "moduleSN", "plantName", "stationName")
        }

    return {
        "config_entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "coordinator_data": safe_data,
        "is_online": coordinator.is_online,
        "last_update_success": coordinator.last_update_success,
    }
