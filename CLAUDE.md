# foxess-cloud-ha

Home Assistant custom integration (HACS) for Fox ESS Cloud inverters: sensors, battery Min SoC controls,
work mode select and Mode Scheduler services. **Public repo**: anything committed is visible to everyone.

## Working here

- Shared rules for all of Ahmed's repos (Git workflow, security, how to talk to him) are in
  `C:\Users\ahmed\Development\CLAUDE.md` when working on his PC. In short: branch + PR, Conventional Commits,
  never commit secrets, update the README with every change, give commit message + PR title + PR description.
- Code is in `custom_components/foxess_cloud/`. `api.py` talks to the Fox ESS Open API, `coordinator.py`
  polls it; entities are in `sensor.py`, `number.py`, `select.py`, `button.py`; services in `services.py`
  and `services.yaml`.
- The API allows 1440 calls a day per key. Any new polling or service call must fit inside that budget
  (keep the staggered polling).
- Never log or expose the API key or inverter serial: `diagnostics.py` redacts them, keep it that way.
- User-facing text goes in `strings.json` and `translations/en.json` together.
- Releases: bump `version` in `manifest.json`, tag `vX.Y.Z` on `main`, generate release notes. HACS reads
  the GitHub releases.
- `examples/` holds automations (e.g. Flow Power Happy Hour); keep them working when services change.

## Check before done

```bash
python -m compileall -q custom_components   # CI also runs hassfest and HACS validation
```
