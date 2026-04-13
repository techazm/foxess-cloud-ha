"""Fox ESS Cloud API client."""
from __future__ import annotations

import asyncio
import hashlib
import time
from datetime import datetime
from typing import Any

import aiohttp

from .const import (
    BASE_URL,
    ENDPOINT_BATTERY_SOC_GET,
    ENDPOINT_BATTERY_SOC_SET,
    ENDPOINT_DEVICE_DETAIL,
    ENDPOINT_DEVICE_LIST,
    ENDPOINT_GENERATION,
    ENDPOINT_REAL_QUERY,
    ENDPOINT_REPORT_QUERY,
    ENDPOINT_SETTING_GET,
    ENDPOINT_SETTING_SET,
    LOGGER,
)


class FoxESSCloudApiError(Exception):
    """Base exception for Fox ESS Cloud API errors."""


class FoxESSAuthError(FoxESSCloudApiError):
    """Authentication error."""


class FoxESSConnectionError(FoxESSCloudApiError):
    """Connection error."""


class FoxESSRateLimitError(FoxESSCloudApiError):
    """Rate limit exceeded."""


class FoxESSCloudApi:
    """Fox ESS Cloud API client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._api_key = api_key
        self._last_request_time: float = 0

    @staticmethod
    def _md5(text: str) -> str:
        """Generate MD5 hash."""
        return hashlib.md5(text.encode("UTF-8")).hexdigest()

    def _build_headers(self, path: str) -> dict[str, str]:
        """Build request headers with signature."""
        timestamp = str(round(time.time() * 1000))
        signature_text = f"{path}\\r\\n{self._api_key}\\r\\n{timestamp}"
        signature = self._md5(signature_text)
        return {
            "Content-Type": "application/json",
            "User-Agent": "FoxESSCloud-HA/1.0.0",
            "token": self._api_key,
            "timestamp": timestamp,
            "signature": signature,
            "lang": "en",
        }

    async def _rate_limit(self) -> None:
        """Enforce minimum 1-second gap between requests."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
        self._last_request_time = time.time()

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an API request."""
        await self._rate_limit()
        url = f"{BASE_URL}{path}"
        headers = self._build_headers(path)

        try:
            if method == "GET":
                async with self._session.get(
                    url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    data = await resp.json(content_type=None)
            else:
                async with self._session.post(
                    url,
                    headers=headers,
                    json=body,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    data = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise FoxESSConnectionError(f"Connection error: {err}") from err
        except asyncio.TimeoutError as err:
            raise FoxESSConnectionError("Request timed out") from err

        if data is None:
            raise FoxESSCloudApiError("Empty response from API")

        LOGGER.debug("API %s %s -> errno=%s, keys=%s", method, path, data.get("errno"), list(data.keys()) if isinstance(data, dict) else type(data))

        errno = data.get("errno", -1)
        if errno == 40257:
            raise FoxESSAuthError("Invalid API key or parameters")
        if errno == 40256:
            raise FoxESSAuthError("Missing request header parameters")
        if errno in (40400, 40402):
            raise FoxESSRateLimitError("API rate limit exceeded")
        if errno == 41809:
            raise FoxESSAuthError("Invalid token")
        if errno == 41930:
            raise FoxESSCloudApiError("Device does not exist")
        if errno != 0:
            msg = data.get("msg", "Unknown error")
            raise FoxESSCloudApiError(f"API error {errno}: {msg}")

        return data

    # ── Device endpoints ──────────────────────────────────

    async def get_device_list(self) -> list[dict[str, Any]]:
        """Get list of devices under this account."""
        body = {"currentPage": 1, "pageSize": 100}
        data = await self._request("POST", ENDPOINT_DEVICE_LIST, body=body)
        result = data.get("result", {})
        return result.get("data", [])

    async def get_device_detail(self, sn: str) -> dict[str, Any]:
        """Get device detail by serial number."""
        data = await self._request("GET", ENDPOINT_DEVICE_DETAIL, params={"sn": sn})
        return data.get("result", {})

    # ── Real-time data ────────────────────────────────────

    async def get_real_time_data(
        self, sn: str, variables: list[str] | None = None
    ) -> dict[str, Any]:
        """Get real-time data for a device (v1 API)."""
        body: dict[str, Any] = {"sn": sn}
        if variables:
            body["variables"] = variables
        data = await self._request("POST", ENDPOINT_REAL_QUERY, body=body)
        result = data.get("result")
        LOGGER.debug("Real-time raw result type=%s", type(result))

        parsed: dict[str, Any] = {}
        if isinstance(result, list):
            # v1-style: list of device results
            for device in result:
                if isinstance(device, dict):
                    for item in device.get("datas", []):
                        var_name = item.get("variable")
                        if var_name:
                            parsed[var_name] = item.get("value")
        elif isinstance(result, dict):
            # v0-style: single result with datas array
            for item in result.get("datas", []):
                var_name = item.get("variable")
                if var_name:
                    parsed[var_name] = item.get("value")

        LOGGER.debug("Real-time parsed %d variables: %s", len(parsed), list(parsed.keys())[:10])
        return parsed

    # ── Report data ───────────────────────────────────────

    async def get_report_data(
        self,
        sn: str,
        variables: list[str] | None = None,
        dimension: str = "day",
    ) -> dict[str, float]:
        """Get report data (daily totals) for a device."""
        today = datetime.now()
        body: dict[str, Any] = {
            "sn": sn,
            "year": today.year,
            "month": today.month,
            "day": today.day,
            "dimension": dimension,
        }
        if variables:
            body["variables"] = variables

        data = await self._request("POST", ENDPOINT_REPORT_QUERY, body=body)
        result = data.get("result", [])
        LOGGER.debug("Report raw result type=%s, len=%s", type(result), len(result) if isinstance(result, list) else "N/A")

        parsed: dict[str, float] = {}
        if isinstance(result, list):
            for dataset in result:
                var_name = dataset.get("variable")
                values = dataset.get("values", [])
                try:
                    total = sum(float(v) for v in values if v is not None)
                except (ValueError, TypeError):
                    total = 0.0
                if var_name:
                    parsed[var_name] = round(total, 3)

        LOGGER.debug("Report parsed: %s", parsed)
        return parsed

    # ── Generation ────────────────────────────────────────

    async def get_generation(self, sn: str) -> dict[str, Any]:
        """Get generation data for a device."""
        data = await self._request(
            "GET", ENDPOINT_GENERATION, params={"sn": sn}
        )
        result = data.get("result", {})
        LOGGER.debug("Generation result keys: %s", list(result.keys()) if isinstance(result, dict) else type(result))
        return result if isinstance(result, dict) else {}

    # ── Battery SOC ───────────────────────────────────────

    async def get_battery_soc(self, sn: str) -> dict[str, Any]:
        """Get battery minimum SoC settings."""
        data = await self._request(
            "GET", ENDPOINT_BATTERY_SOC_GET, params={"sn": sn}
        )
        return data.get("result", {})

    async def set_battery_soc(
        self, sn: str, min_soc: int, min_soc_on_grid: int
    ) -> bool:
        """Set battery minimum SoC values."""
        body = {
            "sn": sn,
            "minSoc": min_soc,
            "minSocOnGrid": min_soc_on_grid,
        }
        await self._request("POST", ENDPOINT_BATTERY_SOC_SET, body=body)
        return True

    # ── Device settings (work mode, etc.) ─────────────────

    async def get_device_setting(self, sn: str, setting: str) -> dict[str, Any]:
        """Get a device setting (e.g., WorkMode)."""
        body = {"sn": sn, "key": setting}
        data = await self._request("POST", ENDPOINT_SETTING_GET, body=body)
        return data.get("result", {})

    async def set_device_setting(
        self, sn: str, setting: str, value: str
    ) -> bool:
        """Set a device setting (e.g., WorkMode)."""
        body = {"sn": sn, "key": setting, "value": value}
        await self._request("POST", ENDPOINT_SETTING_SET, body=body)
        return True
