# Flow Power Happy Hour optimiser (Home Assistant)

Maximises Flow Power Happy Hour earnings on a FoxESS KH10 + CQ6 (~38 kWh usable) without buying power back overnight, while planning to still have 40% in the battery at 08:00. Uses the `foxess_cloud` integration (>= 1.1.1) in this repo.

**Two SoC levels**
- `hh_morning_target_soc` (40%): the *plan*. Tonight's cut-off is sized so the battery should still be at this level at 08:00.
- `hh_floor_soc` (10%): the *hard* inverter floor. Kept lower on purpose, so a heavier-than-expected night drains a bit below 40% instead of importing at 42c (or at spike prices).

Zero grid import can't be guaranteed by any schedule: big loads starting (aircon compressor, kettle) pull a few Wh before the inverter reacts, and anything above ~10 kW comes from the grid. Expect 0.2-0.4 kWh/day from that.

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
   `reserve = 08:00 target + (overnight load avg x (1 + margin) [+ extra if tomorrow's forecast < threshold] [+ extra if a price spike is forecast overnight]) / usable kWh` (capped at 95%)
   Force discharge 17:30-21:29 at `hh_fd_power_w` (default 10 kW) with cut-off = reserve. The inverter's own cut-off enforces it. In Force Discharge the inverter outputs only the set power, and any house load above it comes from the grid, so keep this high.
   If a price spike overlaps 17:30-21:30, the evening block also gets `import_limit: 0`, so house load is never topped up from the grid while discharging.
2. **17:29** - presses *Refresh All Data* so the 17:30 export counter starts from fresh daily totals.
3. **15 kWh exported** (`utility_meter` reset at 17:30) - keeps selling at 10c only if surplus above reserve >= `hh_surplus_min_kwh` **and** tomorrow's solar is good. Otherwise it rewrites 17:30-21:29 as Self-use (second and final write).
4. **21:30 / 08:00** - learns overnight load 21:30-08:00 (EMA, alpha 0.25) and notifies if overnight import exceeds `hh_import_alert_kwh`. Uses never-resetting utility meters so the midnight reset of the daily sensors doesn't break the maths.
5. **08:00** - if SoC is below the 08:00 target and the night started at the planned cut-off, adds 5 to `hh_margin_bump_pct` (learned extra margin, max 50) and notifies. Nights that started low (export stopped early, battery never filled) don't count.

Cloud API budget: 2 schedule writes/day (4 calls each) + 1 forced refresh. Well within 1440/day.

**Granularity:** daily feed-in comes from the cloud report (~15 min), so the cap can overshoot by about 1 kWh. That energy sells at 10c and the reserve cut-off still holds, so the cost is small.

## Setup
1. Update the `foxess_cloud` integration to 1.1.1 and restart HA.
2. Copy `flow_happy_hour.yaml` to `config/packages/` and enable packages.
3. Replace the placeholder `fox_ess_inverter` in the YAML with your device's entity slug (default: `fox_ess_<serial in lower case>`).
4. Optional: add a PV forecast. The YAML uses the built-in **Forecast.Solar** sensor `sensor.energy_production_tomorrow` (Settings -> Devices & services -> Add -> Forecast.Solar). For Solcast (HACS, more accurate), replace it with `sensor.solcast_pv_forecast_forecast_tomorrow`. Without a forecast the package still works; it just can't hold extra back before cloudy days.
5. In **Developer Tools -> Actions**, run `foxess_cloud.get_schedule` (Return response) and confirm `properties` lists `fdsoc`/`fdpwr`/`secondworkmode`. On a KH10, `fd_pwr` max is 10500 W and SoC fields can't go below 10%.
6. Optional: add `flow_power_prices.yaml` for price-spike handling (see below).
7. Optional: add `flow_bill.yaml` for "since last bill" figures (see below).
8. Optional: add the dashboard (see below).
9. Turn on `input_boolean.hh_dry_run` and `input_boolean.hh_enabled`, watch the notifications for 2-3 days, then turn dry run off.

## Dashboard (`dashboard.yaml`, optional)
Built-in cards only (no HACS). Settings -> Dashboards -> Add dashboard -> open it -> Edit -> Raw configuration editor, paste the file, then replace `fox_ess_inverter` with your slug.

| Section | Shows |
|---|---|
| Tonight | Live status line (what the optimiser does next), key numbers, battery and export gauges |
| Graphs | Battery vs reserve / armed cut-off / 08:00 target (24 h), export vs 35c cap (24 h), wholesale price + spikes (48 h), daily export/import/load bars (14 days) |
| Since last bill | Happy Hour kWh and $ at each rate, import, supply, net, PEA estimate; bill start, rates and running totals (needs `flow_bill.yaml`) |
| Controls | On/off, dry run and every tuning helper; Flow Power prices and PEA; logbook of automation runs and margin changes |

The logbook uses automation entity IDs derived from the aliases (e.g. `automation.happy_hour_arm_tonight`). If you renamed them, update the list.

## Tuning
| Setting | Default | When to change |
|---|---|---|
| `hh_morning_target_soc` | 40% | SoC you want left at 08:00 (backup + morning load) |
| `hh_floor_soc` | 10% | Hard inverter floor; keep below the target so the battery, not the grid, covers a heavy night |
| `hh_reserve_margin_pct` | 15% | Base margin on the learned overnight load |
| `hh_margin_bump_pct` | 0% | Learned: +5 each time 08:00 SoC misses the target. Set back to 0 after a heatwave |
| `hh_poor_solar_kwh` / `_extra_kwh` | 30 / 5 | Hold more back before cloudy days |
| `hh_surplus_min_kwh` | 3 | Minimum spare kWh worth selling at 10c |
| `hh_fd_power_w` | 10000 | Max 10500 on a KH10. Higher = less chance of house load being topped up from the grid while discharging. The inverter's export limit still applies |
| `hh_import_alert_kwh` | 0.5 | Overnight import that triggers an alert. Below ~0.3 it will alert most nights (load-step transients) |

Summer aircon: the overnight EMA adapts within a few nights, and the 08:00 check raises the margin if it's still short. For a known heatwave, temporarily raise `hh_reserve_margin_pct`.

The overnight load figure includes anything PV supplies after sunrise, so in summer it slightly over-reserves (safe side).

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
- Spike between 21:30 and 08:00: reserve gets `hh_spike_extra_kwh` (default 3 kWh).
- A notification when a new spike first appears in the forecast.

**API notes:** `POST https://api.kwatch.com.au/api/v1/<method>` with header `x-api-key`. Responses are a JSON string containing JSON. Prices are $/MWh. Timestamps are NEM time (+10:00, no daylight saving) and mark the **end** of each interval. Polling: 288 + 144 + 24 calls/day.

## Since last bill (`flow_bill.yaml`, optional)
A running estimate of the current bill from local meters. Needs `flow_happy_hour.yaml` (`hh_export_window`, `hh_import_total`); `flow_power_prices.yaml` adds the PEA lines.

**Nothing is ever zeroed.** The counters only go up, and `sensor.flow_bill_daily_log` snapshots them at 00:00 every day (last 100 days, kept across restarts). "Since last bill" is *counters now - snapshot on `flow_bill_start`*. Moving the bill start, by hand or on bill day, recalculates the whole period exactly from the snapshot for that date. That means you don't need to know the bill date in advance.

| Figure | How |
|---|---|
| Usage | `sensor.flow_bill_import` = `hh_import_total` now - its snapshot on the bill start |
| Revenue | At 21:30: refresh, wait 1 min, then add `min(window, cap) x high rate + max(window - cap, 0) x low rate` to the lifetime totals `flow_hh_revenue_total`, `flow_hh_high_kwh_total`, `flow_hh_low_kwh_total`. Once per window (`flow_hh_last_close`). `sensor.flow_bill_revenue` / `_happy_hour_high_kwh` / `_low_kwh` = lifetime - snapshot |
| Cost | `sensor.flow_bill_cost` = import kWh x `flow_rate_import` + `sensor.flow_bill_days` x `flow_rate_supply` (days include today) |
| Net | `sensor.flow_bill_net` = revenue - cost (positive = credit) |
| PEA | `sensor.flow_bill_pea_estimate` = import kWh x `sensor.flow_pea_30_days` / 100. Flow's 30-day rolling figure, **not bill-aligned**: an indication only |

**Helpers** (no `initial`, so edits survive restarts)
| Helper | Default | Notes |
|---|---|---|
| `flow_rate_hh_high` / `_low` | $0.35 / $0.10 per kWh | Happy Hour export rates |
| `flow_rate_hh_cap` | 15 kWh | High-rate kWh per day (tariff; separate from the optimiser's `hh_cap_kwh`) |
| `flow_rate_import` | $0.4226/kWh | Import before PEA |
| `flow_rate_supply` | $2.2256/day | Daily supply |
| `flow_bill_start` | today, on first run | Bill start date. Drives the snapshot used and the supply-day count |
| `flow_bill_day` | 0 (unknown) | Day of month for the monthly auto-advance. Set automatically when you change `flow_bill_start` by hand; 29-31 fall back to the month's last day |
| `flow_bill_pre_*` | 0 | Import, Happy Hour kWh and $ between the bill start and the first snapshot. Only used while the bill start is earlier than the oldest snapshot |

Default rates are filled in by `flow_bill_seed` only while a rate is 0, so a rate you change in the UI stays changed.

**Bill date not known yet (new customer)**
1. Set `flow_bill_start` to your switch date. That also sets `flow_bill_day`, so the period auto-advances monthly on that day.
2. Fill the `flow_bill_pre_*` helpers for the switch date up to the day you installed the package. Import comes from the Flow app; the nightly Happy Hour kWh are in the history of `sensor.hh_export_window`, as its value at 21:30 each night (split at 15 kWh).
3. When the first bill arrives, set `flow_bill_start` to the day after the bill's end date. The current period recalculates and the bill day is relearned. Compare the bill's totals with the closing notification.

**Bill day:** at 00:00:30 on `flow_bill_day` it notifies the closing period's totals (estimate), then moves `flow_bill_start` to today. The window closed at 21:30 the night before stays on the old bill. Automatic moves don't relearn the bill day; only your own edits do.

**Fixing by hand:** edit `flow_bill_start` for a missed or moved bill. Edit the lifetime totals for a missing or wrong Happy Hour night (past snapshots don't change, so the correction lands in the current period). If no snapshot exists for the bill start (HA down at midnight), the next day's is used.

If HA is down at 21:30, the window is closed on the next start, as long as that's before 06:00 (after that the counter may include 0c morning solar export, so the night is skipped; add it to the lifetime totals by hand). Revenue uses the rates in force at 21:30 each night; the dashboard's per-rate $ use today's rates. Cloud API: +1 refresh/day.

## Winter
Around April, switch back to a plan with a free midday window and turn off `hh_enabled`.

## Not yet included
- Reconciling actual Happy Hour kWh from the Flow Power API against the local counter.

## Troubleshooting
| Symptom | Cause / fix |
|---|---|
| Flow sensors `unknown`, log shows *"do not have permission to perform this action"* | API key rejected. Check Web Data Access is on in the Flow app, copy the current key into `secrets.yaml`, then reload *REST entities* (Developer Tools -> YAML) or restart |
| `Solar tomorrow` far below what you produce | Forecast.Solar location (lat/long, from HA's home location), modules power (W), inverter size or damping. Set `hh_poor_solar_kwh` to 0 until fixed |

## Changelog
- 2026-10-28 - v1.7: optional `flow_bill.yaml` and a *Since last bill* dashboard section: import kWh, Happy Hour kWh and $ at each rate (closed nightly at 21:30), supply, net, and a PEA estimate labelled as 30-day rolling. Lifetime counters plus a daily snapshot log, so the bill start can be set or moved at any time (no need to know the bill date in advance); the bill day is learned from manual edits. Rates are helpers.
- 2026-10-12 - v1.6.1: Flow Power sensors go `unknown` on API errors (e.g. rejected key) instead of failing to load with a template error; troubleshooting section.
- 2026-10-12 - v1.6: optional `dashboard.yaml` (status, gauges, history/statistics graphs, controls, logbook) using built-in cards.
- 2026-10-12 - v1.5: plan for 40% SoC at 08:00 (`hh_morning_target_soc`) on top of a lower hard floor; replaces `hh_morning_buffer_kwh`. Overnight learning runs to 08:00 and adds a learned extra margin when the target is missed. Learned helpers no longer have `initial`, so they survive HA restarts (the overnight average used to reset to 6 kWh). Force discharge power defaults to 10 kW. Configurable import alert.
- 2026-10-12 - v1.4: optional Flow Power price-spike package (current/forecast prices, PEA); spike-aware reserve and `import_limit: 0` during evening spikes; placeholder entity slug instead of a real inverter serial.
- 2026-10-11 - v1.3: PV forecast is optional; a missing/unavailable forecast no longer counts as a poor solar day (it was adding ~13% to the reserve).
- 2026-10-11 - v1.2: Force Discharge falls back to Self-use after the cut-off (`second_work_mode`); floor SoC minimum raised to 10% to match the inverter.
- 2026-10-11 - v1.1: wired to `foxess_cloud.set_schedule`; real entity IDs; never-resetting load/import meters for overnight learning; pre-window refresh.
- 2026-10-11 - v1: reserve-based cut-off, 35c cap handling, overnight learning, import alerts, dry-run mode.
