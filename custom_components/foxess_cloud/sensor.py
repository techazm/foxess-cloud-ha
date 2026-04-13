"""Sensor platform for Fox ESS Cloud integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN
from .coordinator import FoxESSCloudCoordinator
from .entity import FoxESSEntity


@dataclass(frozen=True)
class FoxESSSensorDescription(SensorEntityDescription):
    """Describe a Fox ESS sensor."""

    value_fn: Callable[[dict[str, Any]], StateType] | None = None


def _rt(variable: str) -> Callable[[dict[str, Any]], StateType]:
    """Helper: get a realtime variable, rounded to 3 decimals."""
    def _get(data: dict[str, Any]) -> StateType:
        val = data.get("realtime", {}).get(variable)
        if val is None:
            return None
        try:
            return round(float(val), 3)
        except (ValueError, TypeError):
            return val
    return _get


def _rpt(variable: str) -> Callable[[dict[str, Any]], StateType]:
    """Helper: get a report variable."""
    def _get(data: dict[str, Any]) -> StateType:
        return data.get("report", {}).get(variable)
    return _get


def _gen(key: str) -> Callable[[dict[str, Any]], StateType]:
    """Helper: get a generation variable."""
    def _get(data: dict[str, Any]) -> StateType:
        return data.get("generation", {}).get(key)
    return _get


# ── Sensor Definitions ──────────────────────────────────────

REALTIME_SENSORS: tuple[FoxESSSensorDescription, ...] = (
    # ── PV Total ──
    FoxESSSensorDescription(
        key="pv_power",
        name="PV Power",
        icon="mdi:solar-power-variant",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        value_fn=_rt("pvPower"),
    ),
    # ── PV Strings 1-4 ──
    *(
        desc
        for i in range(1, 5)
        for desc in (
            FoxESSSensorDescription(
                key=f"pv{i}_power",
                name=f"PV{i} Power",
                icon="mdi:lightning-bolt",
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                value_fn=_rt(f"pv{i}Power"),
            ),
            FoxESSSensorDescription(
                key=f"pv{i}_voltage",
                name=f"PV{i} Voltage",
                icon="mdi:sine-wave",
                device_class=SensorDeviceClass.VOLTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                value_fn=_rt(f"pv{i}Volt"),
            ),
            FoxESSSensorDescription(
                key=f"pv{i}_current",
                name=f"PV{i} Current",
                icon="mdi:current-dc",
                device_class=SensorDeviceClass.CURRENT,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                value_fn=_rt(f"pv{i}Current"),
            ),
        )
    ),
    # ── Grid / Load / Feed-in ──
    FoxESSSensorDescription(
        key="generation_power",
        name="Generation Power",
        icon="mdi:flash",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        value_fn=_rt("generationPower"),
    ),
    FoxESSSensorDescription(
        key="grid_consumption_power",
        name="Grid Consumption Power",
        icon="mdi:transmission-tower",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        value_fn=_rt("gridConsumptionPower"),
    ),
    FoxESSSensorDescription(
        key="feedin_power",
        name="Feed-in Power",
        icon="mdi:transmission-tower-export",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        value_fn=_rt("feedinPower"),
    ),
    FoxESSSensorDescription(
        key="load_power",
        name="Load Power",
        icon="mdi:home-lightning-bolt",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        value_fn=_rt("loadsPower"),
    ),
    # ── Battery ──
    FoxESSSensorDescription(
        key="bat_charge_power",
        name="Battery Charge Power",
        icon="mdi:battery-charging",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        value_fn=_rt("batChargePower"),
    ),
    FoxESSSensorDescription(
        key="bat_discharge_power",
        name="Battery Discharge Power",
        icon="mdi:battery-arrow-down",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        value_fn=_rt("batDischargePower"),
    ),
    FoxESSSensorDescription(
        key="bat_soc",
        name="Battery SoC",
        icon="mdi:battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_rt("SoC"),
    ),
    FoxESSSensorDescription(
        key="bat_soh",
        name="Battery SoH",
        icon="mdi:battery-heart-variant",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_rt("SoH"),
    ),
    FoxESSSensorDescription(
        key="bat_temperature",
        name="Battery Temperature",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=_rt("batTemperature"),
    ),
    FoxESSSensorDescription(
        key="residual_energy",
        name="Residual Energy",
        icon="mdi:battery-clock",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=_rt("ResidualEnergy"),
    ),
    FoxESSSensorDescription(
        key="inverter_bat_power",
        name="Inverter Battery Power",
        icon="mdi:battery-sync",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        value_fn=_rt("invBatPower"),
    ),
    # ── Phase R/S/T ──
    *(
        desc
        for phase in ("R", "S", "T")
        for desc in (
            FoxESSSensorDescription(
                key=f"{phase.lower()}_voltage",
                name=f"{phase} Voltage",
                icon="mdi:sine-wave",
                device_class=SensorDeviceClass.VOLTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                value_fn=_rt(f"{phase}Volt"),
            ),
            FoxESSSensorDescription(
                key=f"{phase.lower()}_current",
                name=f"{phase} Current",
                icon="mdi:current-ac",
                device_class=SensorDeviceClass.CURRENT,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                value_fn=_rt(f"{phase}Current"),
            ),
            FoxESSSensorDescription(
                key=f"{phase.lower()}_power",
                name=f"{phase} Power",
                icon="mdi:flash",
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                value_fn=_rt(f"{phase}Power"),
            ),
            FoxESSSensorDescription(
                key=f"{phase.lower()}_freq",
                name=f"{phase} Frequency",
                icon="mdi:sine-wave",
                device_class=SensorDeviceClass.FREQUENCY,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfFrequency.HERTZ,
                value_fn=_rt(f"{phase}Freq"),
            ),
        )
    ),
    # ── Temperatures ──
    FoxESSSensorDescription(
        key="ambient_temp",
        name="Ambient Temperature",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=_rt("ambientTemperation"),
    ),
    FoxESSSensorDescription(
        key="boost_temp",
        name="Boost Temperature",
        icon="mdi:thermometer-high",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=_rt("boostTemperation"),
    ),
    FoxESSSensorDescription(
        key="inv_temp",
        name="Inverter Temperature",
        icon="mdi:thermometer-alert",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=_rt("invTemperation"),
    ),
    # ── Misc ──
    FoxESSSensorDescription(
        key="running_state",
        name="Running State",
        icon="mdi:state-machine",
        value_fn=lambda data: data.get("realtime", {}).get("runningStateText"),
    ),
    FoxESSSensorDescription(
        key="power_factor",
        name="Power Factor",
        icon="mdi:math-cos",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_rt("PowerFactor"),
    ),
    FoxESSSensorDescription(
        key="reactive_power",
        name="Reactive Power",
        icon="mdi:flash-triangle",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kVar",
        value_fn=_rt("ReactivePower"),
    ),
    FoxESSSensorDescription(
        key="meter2_power",
        name="Meter 2 Power",
        icon="mdi:meter-electric",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        value_fn=_rt("meterPower2"),
    ),
)

REPORT_SENSORS: tuple[FoxESSSensorDescription, ...] = (
    FoxESSSensorDescription(
        key="daily_generation",
        name="Daily Generation",
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=_rpt("generation"),
    ),
    FoxESSSensorDescription(
        key="daily_feedin",
        name="Daily Feed-in",
        icon="mdi:transmission-tower-export",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=_rpt("feedin"),
    ),
    FoxESSSensorDescription(
        key="daily_grid_consumption",
        name="Daily Grid Consumption",
        icon="mdi:transmission-tower-import",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=_rpt("gridConsumption"),
    ),
    FoxESSSensorDescription(
        key="daily_load",
        name="Daily Load",
        icon="mdi:home-lightning-bolt",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=_rpt("loads"),
    ),
    FoxESSSensorDescription(
        key="daily_bat_charge",
        name="Daily Battery Charge",
        icon="mdi:battery-plus",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=_rpt("chargeEnergyToTal"),
    ),
    FoxESSSensorDescription(
        key="daily_bat_discharge",
        name="Daily Battery Discharge",
        icon="mdi:battery-minus",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=_rpt("dischargeEnergyToTal"),
    ),
)

GENERATION_SENSORS: tuple[FoxESSSensorDescription, ...] = (
    FoxESSSensorDescription(
        key="total_generation",
        name="Total Generation",
        icon="mdi:counter",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=_gen("cumulative"),
    ),
    FoxESSSensorDescription(
        key="today_generation",
        name="Today Generation",
        icon="mdi:white-balance-sunny",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=_gen("today"),
    ),
    FoxESSSensorDescription(
        key="month_generation",
        name="Month Generation",
        icon="mdi:calendar-month",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=_gen("month"),
    ),
)

ALL_SENSORS = REALTIME_SENSORS + REPORT_SENSORS + GENERATION_SENSORS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Fox ESS Cloud sensor entities."""
    coordinator: FoxESSCloudCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        FoxESSSensorEntity(coordinator, description)
        for description in ALL_SENSORS
    )


class FoxESSSensorEntity(FoxESSEntity, SensorEntity):
    """Fox ESS Cloud sensor entity."""

    entity_description: FoxESSSensorDescription

    def __init__(
        self,
        coordinator: FoxESSCloudCoordinator,
        description: FoxESSSensorDescription,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        """Return the sensor value."""
        if self.entity_description.value_fn is None:
            return None
        try:
            return self.entity_description.value_fn(self.coordinator.data or {})
        except (KeyError, TypeError, ValueError):
            return None
