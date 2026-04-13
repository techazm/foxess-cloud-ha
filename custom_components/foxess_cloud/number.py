"""Number platform for Fox ESS Cloud integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import FoxESSCloudApiError
from .const import DOMAIN, LOGGER
from .coordinator import FoxESSCloudCoordinator
from .entity import FoxESSEntity


@dataclass(frozen=True)
class FoxESSNumberDescription(NumberEntityDescription):
    """Describe a Fox ESS number entity."""

    soc_key: str = ""  # Key in the battery_soc response


NUMBER_DESCRIPTIONS: tuple[FoxESSNumberDescription, ...] = (
    FoxESSNumberDescription(
        key="min_soc",
        name="Min SoC",
        icon="mdi:battery-low",
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.SLIDER,
        soc_key="minSoc",
    ),
    FoxESSNumberDescription(
        key="min_soc_on_grid",
        name="Min SoC on Grid",
        icon="mdi:battery-outline",
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.SLIDER,
        soc_key="minSocOnGrid",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Fox ESS Cloud number entities."""
    coordinator: FoxESSCloudCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        FoxESSNumberEntity(coordinator, description)
        for description in NUMBER_DESCRIPTIONS
    )


class FoxESSNumberEntity(FoxESSEntity, NumberEntity):
    """Fox ESS Cloud number entity for battery SOC settings."""

    entity_description: FoxESSNumberDescription

    def __init__(
        self,
        coordinator: FoxESSCloudCoordinator,
        description: FoxESSNumberDescription,
    ) -> None:
        """Initialize number entity."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if not self.coordinator.data:
            return None
        battery_soc = self.coordinator.data.get("battery_soc", {})
        value = battery_soc.get(self.entity_description.soc_key)
        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the battery SOC value."""
        # Clamp value to valid range
        clamped = max(10, min(100, int(value)))
        battery_soc = self.coordinator.data.get("battery_soc", {})
        try:
            current_min_soc = int(battery_soc.get("minSoc", 10))
            current_min_soc_on_grid = int(battery_soc.get("minSocOnGrid", 10))
        except (ValueError, TypeError):
            current_min_soc = 10
            current_min_soc_on_grid = 10

        if self.entity_description.soc_key == "minSoc":
            new_min_soc = clamped
            new_min_soc_on_grid = current_min_soc_on_grid
        else:
            new_min_soc = current_min_soc
            new_min_soc_on_grid = clamped

        try:
            await self.coordinator.api.set_battery_soc(
                self.coordinator.device_sn, new_min_soc, new_min_soc_on_grid
            )
            # Update local cache
            self.coordinator.data["battery_soc"][self.entity_description.soc_key] = clamped
            self.async_write_ha_state()
        except FoxESSCloudApiError as err:
            LOGGER.error("Failed to set %s: %s", self.entity_description.key, err)
