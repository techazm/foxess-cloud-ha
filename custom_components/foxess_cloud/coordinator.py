"""Data update coordinator for Fox ESS Cloud."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FoxESSCloudApi, FoxESSCloudApiError, FoxESSRateLimitError
from .const import (
    DEFAULT_SCAN_INTERVAL,
    LOGGER,
    REALTIME_VARIABLES,
    REPORT_VARIABLES,
    RUNNING_STATES,
)


class FoxESSCloudCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that manages polling Fox ESS Cloud at multiple intervals.

    Base interval (configurable, default 5 min): real-time data
    Every 3rd poll (~15 min): report data + device detail
    Every 12th poll (~60 min): battery SOC settings, generation, work mode
    """

    def __init__(
        self,
        hass: HomeAssistant,
        api: FoxESSCloudApi,
        device_sn: str,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize coordinator."""
        self.api = api
        self.device_sn = device_sn
        self._poll_count: int = 0
        self._force_full: bool = False

        # Cached data sections
        self._data: dict[str, Any] = {
            "device_detail": {},
            "realtime": {},
            "report": {},
            "generation": {},
            "battery_soc": {},
            "work_mode": {},
            "online": False,
        }

        super().__init__(
            hass,
            LOGGER,
            name=f"foxess_cloud_{device_sn}",
            update_interval=timedelta(minutes=scan_interval),
        )

    @property
    def device_detail(self) -> dict[str, Any]:
        """Get cached device detail."""
        return self._data.get("device_detail", {})

    @property
    def device_model(self) -> str:
        """Get device model name."""
        return self.device_detail.get("deviceType", "Fox ESS Inverter")

    @property
    def firmware_version(self) -> str | None:
        """Get firmware version."""
        return self.device_detail.get("masterVersion")

    @property
    def is_online(self) -> bool:
        """Check if the device is online."""
        return self._data.get("online", False)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API with staggered intervals."""
        self._poll_count += 1
        try:
            await self._fetch_data(force_all=self._force_full)
        except Exception as err:
            LOGGER.error("Unexpected error during data fetch: %s", err)
        finally:
            self._force_full = False
        return self._data

    async def async_force_full_refresh(self) -> None:
        """Force a full refresh of all data sections on next update."""
        self._force_full = True
        await self.async_refresh()

    async def _fetch_data(self, force_all: bool = False) -> None:
        """Fetch data sections. If force_all, fetch everything regardless of interval."""
        # ── Always: real-time data ──
        try:
            realtime = await self.api.get_real_time_data(
                self.device_sn, variables=REALTIME_VARIABLES
            )
            self._data["realtime"] = realtime
            self._data["online"] = True

            # Parse running state safely
            running_state = realtime.get("runningState")
            if running_state is not None:
                try:
                    state_val = int(float(running_state))
                    self._data["online"] = state_val in (163, 164)
                    self._data["realtime"]["runningStateText"] = RUNNING_STATES.get(
                        state_val, f"Unknown ({state_val})"
                    )
                except (ValueError, TypeError):
                    LOGGER.warning("Could not parse runningState: %s", running_state)
        except Exception as err:
            LOGGER.warning("Error fetching real-time data: %s", err)

        # ── Every 3rd poll (~15 min) or forced: report data + device detail ──
        if force_all or self._poll_count % 3 == 1:
            try:
                detail = await self.api.get_device_detail(self.device_sn)
                self._data["device_detail"] = detail
            except Exception as err:
                LOGGER.warning("Error fetching device detail: %s", err)

            try:
                report = await self.api.get_report_data(
                    self.device_sn, variables=REPORT_VARIABLES
                )
                self._data["report"] = report
            except Exception as err:
                LOGGER.warning("Error fetching report data: %s", err)

        # ── Every 12th poll (~60 min) or forced: battery, generation, work mode ──
        if force_all or self._poll_count % 12 == 1:
            try:
                battery = await self.api.get_battery_soc(self.device_sn)
                self._data["battery_soc"] = battery
            except Exception as err:
                LOGGER.warning("Error fetching battery SOC: %s", err)

            try:
                generation = await self.api.get_generation(self.device_sn)
                self._data["generation"] = generation
            except Exception as err:
                LOGGER.warning("Error fetching generation data: %s", err)

            try:
                work_mode = await self.api.get_device_setting(
                    self.device_sn, "WorkMode"
                )
                self._data["work_mode"] = work_mode
            except Exception as err:
                LOGGER.warning("Error fetching work mode: %s", err)
