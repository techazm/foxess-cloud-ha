"""Button platform for Fox ESS Cloud integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LOGGER
from .coordinator import FoxESSCloudCoordinator
from .entity import FoxESSEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Fox ESS Cloud button entities."""
    coordinator: FoxESSCloudCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FoxESSRefreshButton(coordinator)])


class FoxESSRefreshButton(FoxESSEntity, ButtonEntity):
    """Button to force a full refresh of all Fox ESS data."""

    _attr_name = "Refresh All Data"
    _attr_icon = "mdi:refresh"
    _attr_device_class = ButtonDeviceClass.UPDATE

    def __init__(self, coordinator: FoxESSCloudCoordinator) -> None:
        """Initialize refresh button."""
        super().__init__(coordinator, "refresh_all")

    async def async_press(self) -> None:
        """Handle button press — fetch all data sections immediately."""
        LOGGER.debug("Manual full refresh triggered for %s", self.coordinator.device_sn)
        await self.coordinator.async_force_full_refresh()
