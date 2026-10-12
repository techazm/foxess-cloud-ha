# Flow Power Happy Hour optimiser (Home Assistant)

Maximises Flow Power Happy Hour earnings on a FoxESS KH10 + CQ6 (~38 kWh usable) without buying power back overnight. Uses the `foxess_cloud` integration (>= 1.1.1) in this repo.

## Tariff it optimises for (Endeavour, Oct 2026)
| Item | Rate |
|---|---|
| Export 17:30-21:30, first 15 kWh/day | 35c |
| Export 17:30-21:30, above 15 kWh | 10c |
| Export all other times | 0c |
| Import (base rate, variable) | 42.26c |
| Supply | 222.56c/day |

## How it works
1. **17:20** - computes a reserve SoC and writes tonight's schedule once via `foxess_cloud.set_schedule`:
   `reserve = (overnight load avg + morning buffer) x (1 + margin) [+ extra if tomorrow's forecast < threshold] [+ extra if a price spike is forecast overnight]`
   Force discharge 17:30-21:29 with cut-off = reserve. The inverter's own cut-off enforces the floor.
   If a price spike overlaps 17:30-21:30, the evening block also gets `import_limit: 0`, so house load is never topped up from the grid while discharging.
2. **17:29** - presses *Refresh All Data* so the 17:30 export counter starts from fresh daily totals.
3. **15 kWh exported** (`utility_meter` reset at 17:30) - keeps selling at 10c only if surplus above reserve >= `hh_surplus_min_kwh` **and** tomorrow's solar is good. Otherwise it rewrites 17:30-21:29 as Self-use (second and final write).
4. **21:30 / 07:00** - learns overnight load (EMA, alpha 0.25) and notifies if anything was imported overnight. Uses never-resetting utility meters so the midnight reset of the daily sensors doesn't break the maths.

Cloud API budget: 2 schedule writes/day (4 calls each) + 1 forced refresh. Well within 1440/day.

**Granularity:** daily feed-in comes from the cloud report (~15 min), so the cap can overshoot by about 1 kWh. That energy sells at 10c and the reserve cut-off still holds, so the cost is small.

## Setup
1. Update the `foxess_cloud` integration to 1.1.1 and restart HA.
2. Copy `flow_happy_hour.yaml` to `config/packages/` and enable packages.
3. Replace the placeholder `fox_ess_inverter` in the YAML with your device's entity slug (default: `fox_ess_<serial in lower case>`).
4. Optional: add a PV forecast. Easiest is the built-in **Forecast.Solar** integration (Settings -> Devices & services -> Add -> Forecast.Solar), then replace `sensor.solcast_pv_forecast_forecast_tomorrow` with `sensor.energy_production_tomorrow`. Solcast (HACS) is more accurate. Without a forecast the package still works; it just can't hold extra back before cloudy days.
5. In **Developer Tools -> Actions**, run `foxess_cloud.get_schedule` (Return response) and confirm `properties` lists `fdsoc`/`fdpwr`/`secondworkmode`. On a KH10, `fd_pwr` max is 10500 W and SoC fields can't go below 10%.
6. Optional: add `flow_power_prices.yaml` for price-spike handling (see below).
7. Turn on `input_boolean.hh_dry_run` and `input_boolean.hh_enabled`, watch the notifications for 2-3 days, then turn dry run off.

## Tuning
| Setting | Default | When to change |
|---|---|---|
| `hh_reserve_margin_pct` | 15% | Raise if you get overnight import alerts |
| `hh_morning_buffer_kwh` | 2 | Load between 07:00 and PV covering the house |
| `hh_poor_solar_kwh` / `_extra_kwh` | 30 / 5 | Hold more back before cloudy days |
| `hh_surplus_min_kwh` | 3 | Minimum spare kWh worth selling at 10c |
| `hh_fd_power_w` | 5500 | Lower to 5000 if your export approval is a fixed 5 kW |

Summer aircon: the overnight EMA adapts within a few nights. For a known heatwave, temporarily raise `hh_reserve_margin_pct` or `hh_morning_buffer_kwh`.

## Price spikes (`flow_power_prices.yaml`, optional)
Uses Flow Power's data API (kWatch) to see wholesale price spikes before they happen. On Flow your exports are paid a fixed 35c, but anything you **import** during a spike is priced against it in your PEA, so the goal is zero imports while prices are high.

**Setup**
1. Flow Power app -> More -> **Web Data Access** -> turn the API key on.
2. Add to `secrets.yaml` (never commit these):
   ```yaml
   flow_power_api_key: "<your key>"
   flow_power_summary_payload: '{"nmi":"<your NMI>"}'
   ```
   Your NMI is on your bill, or from the API's `GetResidentialSites` method.
3. Copy `flow_power_prices.yaml` to `config/packages/` and reload.

**Entities**
| Entity | What |
|---|---|
| `sensor.flow_price_now` | Current NSW 5-min price, $/kWh (every 5 min) |
| `sensor.flow_price_forecast_max_24h` | Highest pre-dispatch price in the next 24 h |
| `sensor.flow_price_spike_start` / `_end` | First/last interval at or above `input_number.flow_spike_threshold` (default $1/kWh) |
| `binary_sensor.flow_price_spike_active` | On during a spike: add it as a condition to pool pump, EV, dishwasher automations |
| `sensor.flow_pea_30_days` (+ `_imports`) | Your 30-day PEA, c/kWh (negative = good) |
| `sensor.flow_load_weighted_price_30_days` | What your imports have cost on average, c/kWh |

**What it changes in Happy Hour**
- Spike overlapping 17:30-21:30: evening block written with `import_limit: 0`.
- Spike between 21:30 and 07:00: reserve gets `hh_spike_extra_kwh` (default 3 kWh).
- A notification when a new spike first appears in the forecast.

**API notes:** `POST https://api.kwatch.com.au/api/v1/<method>` with header `x-api-key`. Responses are a JSON string containing JSON. Prices are $/MWh. Timestamps are NEM time (+10:00, no daylight saving) and mark the **end** of each interval. Polling: 288 + 144 + 24 calls/day.

## Winter
Around April, switch back to a plan with a free midday window and turn off `hh_enabled`.

## Not yet included
- Flow Power API (price signals and actual Happy Hour kWh to reconcile against the local counter). Add once the API fields are confirmed.

## Changelog
- 2026-10-12 - v1.4: optional Flow Power price-spike package (current/forecast prices, PEA); spike-aware reserve and `import_limit: 0` during evening spikes; placeholder entity slug instead of a real inverter serial.
- 2026-10-11 - v1.3: PV forecast is optional; a missing/unavailable forecast no longer counts as a poor solar day (it was adding ~13% to the reserve).
- 2026-10-11 - v1.2: Force Discharge falls back to Self-use after the cut-off (`second_work_mode`); floor SoC minimum raised to 10% to match the inverter.
- 2026-10-11 - v1.1: wired to `foxess_cloud.set_schedule`; real entity IDs; never-resetting load/import meters for overnight learning; pre-window refresh.
- 2026-10-11 - v1: reserve-based cut-off, 35c cap handling, overnight learning, import alerts, dry-run mode.
