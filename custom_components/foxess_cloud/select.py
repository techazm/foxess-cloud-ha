"""Select platform for Fox ESS Cloud integration."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import FoxESSCloudApiError
from .const import DOMAIN, LOGGER, WORK_MODES
from .coordinator import FoxESSCloudCoordinator
from .entity import FoxESSEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Fox ESS Cloud select entities."""
    coordinator: FoxESSCloudCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FoxESSWorkModeSelect(coordinator)])


class FoxESSWorkModeSelect(FoxESSEntity, SelectEntity):
    """Select entity for inverter work mode."""

    _attr_name = "Work Mode"
    _attr_icon = "mdi:solar-power"
    _attr_options = WORK_MODES

    def __init__(self, coordinator: FoxESSCloudCoordinator) -> None:
        """Initialize work mode select."""
        super().__init__(coordinator, "work_mode")

    @property
    def current_option(self) -> str | None:
        """Return the current work mode."""
        if not self.coordinator.data:
            return None
        work_mode = self.coordinator.data.get("work_mode", {})
        value = work_mode.get("value")
        if value and value in WORK_MODES:
            return value
        return None

    async def async_select_option(self, option: str) -> None:
        """Set the work mode."""
        if option not in WORK_MODES:
            LOGGER.error("Invalid work mode: %s", option)
            return

        try:
            await self.coordinator.api.set_device_setting(
                self.coordinator.device_sn, "WorkMode", option
            )
            # Update local cache
            if "work_mode" not in self.coordinator.data:
                self.coordinator.data["work_mode"] = {}
            self.coordinator.data["work_mode"]["value"] = option
            self.async_write_ha_state()
        except FoxESSCloudApiError as err:
            LOGGER.error("Failed to set work mode to %s: %s", option, err)
