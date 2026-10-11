# Fox ESS Cloud — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A modern Home Assistant custom integration for [Fox ESS Cloud](https://www.foxesscloud.com/) solar inverters. Monitor your solar installation and control battery settings directly from Home Assistant — fully UI-configured, no YAML editing required.

<p align="center">
  <img src="https://brands.home-assistant.io/foxess/logo.png" alt="Fox ESS" width="200">
</p>

---

## Features

- **UI Config Flow** — Enter your API key, select your inverter from a dropdown. Done.
- **40+ Sensors** — Real-time power, PV strings 1–4, grid, load, battery, phase R/S/T, temperatures, generation totals.
- **Battery Controls** — Adjust Min SoC and Min SoC on Grid via sliders.
- **Work Mode Select** — Switch between SelfUse, Backup, Feedin, and PeakShaving.
- **Mode Scheduler services** — Read and write the inverter's time-of-day schedule (Self-use, Force Discharge, Force Charge…) from automations.
- **Refresh Button** — Force an immediate full data refresh.
- **Options Flow** — Change the polling interval without reconfiguring.
- **HA Device Registry** — All entities grouped under a single device with model and firmware info.
- **Energy Dashboard Ready** — Daily energy sensors with correct device classes for the HA Energy Dashboard.
- **Diagnostics** — Built-in diagnostics with automatic redaction of sensitive data.
- **Rate-Limit Aware** — Staggered polling stays well within the 1440 calls/day API limit.

---

## Prerequisites

Before installing, you need a **Fox ESS Cloud API key**:

1. Log in to [foxesscloud.com](https://www.foxesscloud.com/)
2. Click the **profile icon** (top-right corner) → **User Profile**
3. Select **API Management** from the left menu
4. Click **Generate API Key**
5. **Copy and save the key** — you'll need it during setup

> **Important:** Generating a new key invalidates the old one. If you're already using an API key with another integration (e.g., foxess-ha), do **not** generate a new one — use the same key.

---

## Installation

### Option 1: HACS (Recommended)

1. Open **HACS** in Home Assistant
2. Go to **Integrations**
3. Click the **⋮** menu (top-right) → **Custom repositories**
4. Enter the repository URL and select category **Integration**:
   ```
   https://github.com/techazm/foxess-cloud-ha
   ```
5. Click **Add**
6. Search for **Fox ESS Cloud** and click **Download**
7. **Restart Home Assistant**

### Option 2: Manual Installation

1. Download the [latest release](https://github.com/techazm/foxess-cloud-ha/releases) or clone this repository
2. Copy the entire `custom_components/foxess_cloud` folder into your Home Assistant `config/custom_components/` directory:
   ```
   config/
   └── custom_components/
       └── foxess_cloud/
           ├── __init__.py
           ├── api.py
           ├── brand/
           │   ├── icon.png
           │   ├── icon@2x.png
           │   └── logo.png
           ├── button.py
           ├── config_flow.py
           ├── const.py
           ├── coordinator.py
           ├── diagnostics.py
           ├── entity.py
           ├── manifest.json
           ├── number.py
           ├── select.py
           ├── sensor.py
           ├── services.py
           ├── services.yaml
           ├── strings.json
           └── translations/
               └── en.json
   ```
3. **Restart Home Assistant**

---

## Configuration

### Adding the Integration

1. Go to **Settings → Devices & Services**
2. Click **+ Add Integration** (bottom-right)
3. Search for **Fox ESS Cloud**
4. **Step 1 — API Key:** Paste your Fox ESS Cloud API key
5. **Step 2 — Select Device:** Choose your inverter from the dropdown (the integration auto-discovers all inverters linked to your account)
6. Click **Submit** — all entities are created automatically

### Changing Options

After setup, click **Configure** on the integration card to adjust:

- **Update interval** — How often to poll the API (default: 5 minutes, range: 3–60 minutes)

### Multiple Inverters

If you have more than one inverter, simply add the integration again. Each inverter gets its own device and set of entities.

---

## Provided Entities

All entities are grouped under a single device in the HA device registry (e.g., "Fox ESS 60KB103062CB096") with manufacturer, model, and firmware information.

### Controls

| Entity | Type | Description |
|--------|------|-------------|
| Min SoC | Number (slider) | Battery minimum State of Charge (10–100%) |
| Min SoC on Grid | Number (slider) | Battery minimum SoC when grid is available (10–100%) |
| Work Mode | Select | SelfUse / Backup / Feedin / PeakShaving |
| Refresh All Data | Button | Force immediate refresh of all data from Fox ESS Cloud |

> **Work Mode vs Mode Scheduler:** while the Mode Scheduler is enabled it overrides the Work Mode select. Use the services below to change scheduled behaviour.

### Mode Scheduler

| Entity | Description |
|--------|-------------|
| Mode Scheduler (sensor) | `enabled` / `disabled`; attribute `groups` lists the current time groups. Refreshed hourly and after every write. |

### Sensors — Real-time Power

These update every polling cycle (default 5 minutes):

| Entity | Unit | Description |
|--------|------|-------------|
| PV Power | kW | Total solar power from all strings |
| PV1–4 Power | kW | Per-string solar power |
| PV1–4 Voltage | V | Per-string voltage |
| PV1–4 Current | A | Per-string current |
| Generation Power | kW | Total power generation |
| Grid Consumption Power | kW | Power drawn from grid |
| Feed-in Power | kW | Power exported to grid |
| Load Power | kW | Home consumption |
| Battery Charge Power | kW | Power going into the battery |
| Battery Discharge Power | kW | Power coming from the battery |
| Inverter Battery Power | kW | Net battery power (negative=charging) |
| Meter 2 Power | kW | Secondary meter power |

### Sensors — Battery

| Entity | Unit | Description |
|--------|------|-------------|
| Battery SoC | % | Current State of Charge |
| Battery SoH | % | State of Health |
| Battery Temperature | °C | Battery temperature |
| Residual Energy | kWh | Remaining battery energy |

### Sensors — Phase Data (R/S/T)

| Entity | Unit | Description |
|--------|------|-------------|
| R/S/T Voltage | V | Per-phase voltage |
| R/S/T Current | A | Per-phase current |
| R/S/T Power | kW | Per-phase power |
| R/S/T Frequency | Hz | Per-phase grid frequency |

### Sensors — Temperatures

| Entity | Unit | Description |
|--------|------|-------------|
| Ambient Temperature | °C | Ambient temperature near inverter |
| Boost Temperature | °C | Boost circuit temperature |
| Inverter Temperature | °C | Inverter internal temperature |

### Sensors — Status

| Entity | Description |
|--------|-------------|
| Running State | On Grid, Off Grid, Standby, Fault, etc. |
| Power Factor | Power factor percentage |
| Reactive Power | Reactive power in kVar |

### Sensors — Daily Reports

These update every 3rd polling cycle (~15 minutes):

| Entity | Unit | Description |
|--------|------|-------------|
| Daily Generation | kWh | Total solar generation today |
| Daily Feed-in | kWh | Total exported to grid today |
| Daily Grid Consumption | kWh | Total imported from grid today |
| Daily Load | kWh | Total home consumption today |
| Daily Battery Charge | kWh | Total energy into battery today |
| Daily Battery Discharge | kWh | Total energy from battery today |

### Sensors — Generation Totals

These update every 12th polling cycle (~60 minutes):

| Entity | Unit | Description |
|--------|------|-------------|
| Today Generation | kWh | Same-day generation total |
| Month Generation | kWh | Current month total |
| Total Generation | kWh | Lifetime cumulative generation |

---

## Energy Dashboard Setup

Go to **Settings → Dashboards → Energy** and configure:

### Solar Panels
- **Solar production:** select your `Daily Generation` sensor

### Grid
- **Grid consumption** (energy FROM grid): select your `Daily Grid Consumption` sensor
- **Return to grid** (energy TO grid): select your `Daily Feed-in` sensor

### Home Battery
- **Energy going IN to the battery:** select your `Daily Battery Charge` sensor
- **Energy coming OUT of the battery:** select your `Daily Battery Discharge` sensor

> **Note:** After first setup, the energy dashboard may show partial data for the current day. Full accurate tracking starts from the next day when the daily counters reset at midnight.

---

## Services

### `foxess_cloud.set_schedule`

Replaces **all** Mode Scheduler groups (Open API v3), then turns the scheduler on (or off with `enable: false`). Times are local `HH:MM`; `end` is inclusive, as shown in the Fox app (e.g. `17:30`–`21:29`). Groups can't cross midnight or overlap. Time not covered by a group falls back to the inverter's *Remaining Time Mode*.

```yaml
action: foxess_cloud.set_schedule
data:
  groups:
    - { start: "00:00", end: "17:29", work_mode: SelfUse, min_soc_on_grid: 10 }
    - { start: "17:30", end: "21:29", work_mode: ForceDischarge,
        min_soc_on_grid: 10, fd_soc: 40, fd_pwr: 5500 }
    - { start: "21:30", end: "23:59", work_mode: SelfUse, min_soc_on_grid: 10 }
```

| Field | Notes |
|-------|-------|
| `work_mode` | `SelfUse`, `Feedin`, `Backup`, `ForceCharge`, `ForceDischarge` |
| `min_soc_on_grid` | Always sent |
| `fd_soc`, `fd_pwr` | Force modes only: discharge cut-off SoC (%) and power (W) |
| `max_soc`, `import_limit`, `export_limit`, `pv_limit` | Sent only if your inverter advertises them |
| `device_sn` | Needed only with more than one inverter |

Unsupported fields are dropped with a log warning rather than sent (the v3 API rejects them). Each call uses 2 API calls to write plus 2 to re-read.

### `foxess_cloud.get_schedule`

Returns the live schedule (`enabled`, `groups`, `max_groups`, `properties`). Call it from **Developer Tools → Actions** with *Return response*.

---

## API Rate Limits

Fox ESS allows **1440 API calls per day per inverter**. This integration uses staggered polling to stay well within that limit:

| Data | Poll Frequency | Calls/Day (5 min interval) |
|------|---------------|---------------------------|
| Real-time data | Every cycle | ~288 |
| Device detail + Reports | Every 3rd cycle (~15 min) | ~192 |
| Battery SOC + Generation + Work Mode + Scheduler | Every 12th cycle (~60 min) | ~120 |
| **Total** | | **~600** |

Schedule writes add 4 calls each.

This leaves plenty of headroom. If you increase the polling interval (e.g., to 10 minutes), the daily call count drops proportionally.

---

## Troubleshooting

### Enable Debug Logging

Add this to your `configuration.yaml` and restart:

```yaml
logger:
  default: warning
  logs:
    custom_components.foxess_cloud: debug
```

### Download Diagnostics

Go to **Settings → Devices & Services → Fox ESS Cloud → ⋮ → Download diagnostics**. Sensitive data (API key, serial number, plant name) is automatically redacted — safe to share publicly.

### Common Issues

| Problem | Solution |
|---------|----------|
| All sensors show "Unavailable" | Check your API key is valid. Go to foxesscloud.com → API Management to verify. |
| All sensors show "Unknown" | The API call may be failing. Enable debug logging and check for error messages. |
| Rate limit error (40400) | Reduce the polling interval in the integration options, or wait until the daily limit resets at midnight. |
| "Device does not exist" (41930) | The inverter serial number doesn't match your account. Remove and re-add the integration. |
| Energy dashboard shows wrong values on first day | This is normal. Accurate tracking starts from the next full day. |
| Entities go *Unavailable* briefly | The real-time poll failed (cloud outage or rate limit). Entities recover on the next successful poll; stale values are no longer shown as live. |
| `set_schedule` fails with 40257 | A parameter isn't accepted for that work mode. Run `get_schedule` and check `properties`. |

### API Error Codes

| Code | Meaning |
|------|---------|
| 40256 | Missing request headers — possible signature issue |
| 40257 | Invalid request body parameters |
| 40400 / 40402 | API rate limit exceeded |
| 41809 | Invalid or expired API token |
| 41930 | Device does not exist or belongs to another account |

---

## Changelog

### 1.1.0 (2026-10-11)
- **New:** `foxess_cloud.set_schedule` / `foxess_cloud.get_schedule` services (Mode Scheduler, Open API v3) and a *Mode Scheduler* sensor.
- **Fix:** daily report totals used the container clock (`datetime.now()`), which is UTC in most Docker installs — after local midnight they showed yesterday's totals until UTC rolled over. Now uses HA's configured timezone.
- **Fix:** daily energy sensors' `last_reset` now follows the date of the cached report, so the Energy dashboard can't count yesterday's total again just after midnight.
- **Fix:** a failed real-time poll now marks entities unavailable (and `online` false) instead of serving stale values as current.
- **Fix:** options flow no longer assigns `config_entry` explicitly (breaks on HA 2025.12+); uses `ConfigFlowResult`.
- **Fix:** API calls are serialised with a lock so polls and writes can't break the 1 s spacing.

### 1.0.0
- Initial release.

## Credits

Inspired by [macxq/foxess-ha](https://github.com/macxq/foxess-ha) and [SoftXperience/home-assistant-foxess-api](https://github.com/SoftXperience/home-assistant-foxess-api). 
Fox ESS brand images from the [HA brands repository](https://github.com/home-assistant/brands).

## License

[MIT](LICENSE)
