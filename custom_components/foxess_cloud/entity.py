"""Base entity for Fox ESS Cloud integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BASE_URL, DOMAIN
from .coordinator import FoxESSCloudCoordinator


class FoxESSEntity(CoordinatorEntity[FoxESSCloudCoordinator]):
    """Base class for Fox ESS entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FoxESSCloudCoordinator,
        entity_key: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_sn}_{entity_key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        detail = self.coordinator.device_detail
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.device_sn)},
            manufacturer="Fox ESS",
            model=detail.get("deviceType", "Inverter"),
            name=f"Fox ESS {self.coordinator.device_sn}",
            sw_version=detail.get("masterVersion"),
            hw_version=detail.get("productType"),
            configuration_url=BASE_URL,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Stay available as long as the coordinator has returned data at least once
        return self.coordinator.data is not None
