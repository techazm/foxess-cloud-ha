"""Services for Fox ESS Cloud: read and write the inverter Mode Scheduler."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import homeassistant.helpers.config_validation as cv

from .api import FoxESSCloudApiError
from .const import (
    DEFAULT_MAX_GROUPS,
    DOMAIN,
    LOGGER,
    SCHEDULER_EXTRA_PARAMS,
    SCHEDULER_WORK_MODES,
    SECOND_WORK_MODES,
    SERVICE_GET_SCHEDULE,
    SERVICE_SET_SCHEDULE,
)
from .coordinator import FoxESSCloudCoordinator

FORCE_ONLY = {"fd_soc", "fd_pwr", "second_work_mode"}
ALWAYS_SENT = {"min_soc_on_grid"}  # core field, not listed in v3 "properties"


def _hhmm(value: Any) -> tuple[int, int]:
    """Parse 'HH:MM' (or 'HH:MM:SS') into (hour, minute)."""
    parts = str(value).split(":")
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except (IndexError, ValueError) as err:
        raise vol.Invalid(f"expected HH:MM, got {value!r}") from err
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise vol.Invalid(f"time out of range: {value!r}")
    return hour, minute


GROUP_SCHEMA = vol.Schema(
    {
        vol.Required("start"): _hhmm,
        vol.Required("end"): _hhmm,  # inclusive, as shown in the app (e.g. 17:29)
        vol.Required("work_mode"): vol.In(SCHEDULER_WORK_MODES),
        vol.Optional("min_soc_on_grid"): vol.All(vol.Coerce(int), vol.Range(0, 100)),
        vol.Optional("max_soc"): vol.All(vol.Coerce(int), vol.Range(0, 100)),
        vol.Optional("fd_soc"): vol.All(vol.Coerce(int), vol.Range(0, 100)),
        vol.Optional("fd_pwr"): vol.All(vol.Coerce(int), vol.Range(0, 30000)),
        vol.Optional("second_work_mode"): vol.In(SECOND_WORK_MODES),
        vol.Optional("import_limit"): vol.All(vol.Coerce(int), vol.Range(0, 100000)),
        vol.Optional("export_limit"): vol.All(vol.Coerce(int), vol.Range(0, 100000)),
        vol.Optional("pv_limit"): vol.All(vol.Coerce(int), vol.Range(0, 100000)),
    }
)

SET_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Optional("device_sn"): cv.string,
        vol.Optional("enable", default=True): cv.boolean,
        vol.Required("groups"): vol.All(cv.ensure_list, [GROUP_SCHEMA]),
    }
)

GET_SCHEDULE_SCHEMA = vol.Schema({vol.Optional("device_sn"): cv.string})


def _coordinator(hass: HomeAssistant, device_sn: str | None) -> FoxESSCloudCoordinator:
    """Pick the coordinator for device_sn, or the only one configured."""
    coordinators: list[FoxESSCloudCoordinator] = list(hass.data.get(DOMAIN, {}).values())
    if device_sn:
        for coord in coordinators:
            if coord.device_sn == device_sn:
                return coord
        raise ServiceValidationError(f"No Fox ESS inverter with SN {device_sn}")
    if len(coordinators) == 1:
        return coordinators[0]
    raise ServiceValidationError(
        "device_sn is required when more than one inverter is configured"
        if coordinators
        else "Fox ESS Cloud is not set up"
    )


def _check_range(field: str, value: Any, prop: Any) -> None:
    """Reject values outside the range the inverter advertises."""
    rng = prop.get("range") if isinstance(prop, dict) else None
    if not rng or not isinstance(value, (int, float)):
        return
    lo, hi = rng.get("min"), rng.get("max")
    if (lo is not None and value < lo) or (hi is not None and value > hi):
        raise ServiceValidationError(f"{field}={value} outside inverter range {lo}-{hi}")


def is_remaining_time_group(group: dict[str, Any]) -> bool:
    """The inverter reports its Remaining Time Mode as a 00:00-23:59 group."""
    return (
        int(group.get("startHour", -1)) == 0
        and int(group.get("startMinute", -1)) == 0
        and int(group.get("endHour", -1)) == 23
        and int(group.get("endMinute", -1)) == 59
    )


def build_groups(
    groups: list[dict[str, Any]],
    properties: dict[str, Any],
    max_groups: int | None,
) -> list[dict[str, Any]]:
    """Validate service groups and convert them to Open API v3 groups."""
    limit = max_groups or DEFAULT_MAX_GROUPS
    if len(groups) > limit:
        raise ServiceValidationError(f"{len(groups)} groups given, inverter accepts {limit}")

    spans: list[tuple[int, int]] = []
    out: list[dict[str, Any]] = []
    for group in groups:
        (sh, sm), (eh, em) = group["start"], group["end"]
        start, end = sh * 60 + sm, eh * 60 + em
        if end < start:
            raise ServiceValidationError(
                f"{sh:02d}:{sm:02d}-{eh:02d}:{em:02d} crosses midnight; split it into two groups"
            )
        for s, e in spans:
            if start <= e and s <= end:
                raise ServiceValidationError(f"group starting {sh:02d}:{sm:02d} overlaps another group")
        spans.append((start, end))

        mode = group["work_mode"]
        modes = (properties.get("workmode") or {}).get("enumList")
        if modes and mode not in modes:
            raise ServiceValidationError(f"work_mode {mode} not supported; inverter accepts {modes}")
        extra: dict[str, Any] = {}
        if mode.startswith("ForceDischarge") and "second_work_mode" not in group and (
            not properties or "secondworkmode" in properties
        ):
            # Explicit fallback after fd_soc is reached, so the inverter never
            # drops into Standby and imports while the battery still has charge
            group = {**group, "second_work_mode": "SelfUse"}
        for field, api_key in SCHEDULER_EXTRA_PARAMS.items():
            if field not in group:
                continue
            if field in FORCE_ONLY and not mode.startswith("Force"):
                LOGGER.warning("Dropping %s for %s group (Force modes only)", field, mode)
                continue
            if properties and field not in ALWAYS_SENT and api_key.lower() not in properties:
                LOGGER.warning("Dropping %s: not supported by this inverter", field)
                continue
            _check_range(field, group[field], properties.get(api_key.lower()))
            extra[api_key] = group[field]

        out.append(
            {
                "startHour": sh,
                "startMinute": sm,
                "endHour": eh,
                "endMinute": em,
                "workMode": mode,
                "extraParam": extra,
            }
        )
    return sorted(out, key=lambda g: (g["startHour"], g["startMinute"]))


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_SCHEDULE):
        return

    async def _set_schedule(call: ServiceCall) -> None:
        coord = _coordinator(hass, call.data.get("device_sn"))
        groups = build_groups(
            call.data["groups"], coord.scheduler_properties, coord.scheduler_max_groups
        )
        LOGGER.debug("Writing scheduler for %s: %s", coord.device_sn, groups)
        try:
            await coord.api.set_scheduler(coord.device_sn, groups, call.data["enable"])
        except FoxESSCloudApiError as err:
            raise HomeAssistantError(f"Fox ESS rejected the schedule: {err}") from err
        await coord.async_refresh_scheduler()

    async def _get_schedule(call: ServiceCall) -> ServiceResponse:
        coord = _coordinator(hass, call.data.get("device_sn"))
        try:
            sched = await coord.api.get_scheduler(coord.device_sn)
            flag = await coord.api.get_scheduler_flag(coord.device_sn)
        except FoxESSCloudApiError as err:
            raise HomeAssistantError(f"Could not read schedule: {err}") from err
        return {
            "enabled": str(flag.get("enable")) in ("1", "True", "true"),
            "max_groups": sched.get("maxGroupCount"),
            "groups": [
                {**g, "remaining_time_mode": is_remaining_time_group(g)}
                for g in sched.get("groups") or []
            ],
            "properties": sched.get("properties") or {},
        }

    hass.services.async_register(
        DOMAIN, SERVICE_SET_SCHEDULE, _set_schedule, schema=SET_SCHEDULE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_SCHEDULE,
        _get_schedule,
        schema=GET_SCHEDULE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
