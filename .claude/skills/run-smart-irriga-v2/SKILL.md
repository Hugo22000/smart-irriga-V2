---
name: run-smart-irriga-v2
description: >
  Verify, run smoke tests, and validate the smart-irriga-v2 Home Assistant
  custom component. Use when asked to run, test, verify, or check the
  integration after a code change.
---

# run-smart-irriga-v2

**smart-irriga-v2** is a Home Assistant custom component — a Python package
loaded inside a running HA instance. There is no standalone app to launch.
The driver is `smoke.py`, which validates the component in-place without a
running HA, using only Python stdlib + voluptuous.

---

## Prerequisites

```bash
pip install voluptuous --break-system-packages
```

voluptuous 0.16.0 confirmed working. No other packages needed.

---

## Run (agent path) — smoke.py

Run from the repo root:

```bash
python3 .claude/skills/run-smart-irriga-v2/smoke.py
```

Exit 0 = all checks pass. Exit 1 = failures printed.

Covers:
- **Syntax** — `ast.parse` every `.py` file in `custom_components/smart_irriga_v2/`
- **Constants** — all 21 required symbols present in `const.py` (DOMAIN, PLATFORMS, CONF_*, MODE_*, SERVICE_*)
- **Service schema** — voluptuous schema for `set_zone_options` validates correctly:
  - Partial call (no `irrigation_duration`) passes — regression test for v1.0.7 fix
  - Full call with all fields passes
  - Unknown `activation_mode` is rejected
- **Schedule logic** — `_next_irrigation_dt` returns correct datetimes (7 cases)

Typical output (all passing):

```
[syntax] OK   __init__.py
...
[const]  OK   DOMAIN = 'smart_irriga_v2'
...
[schema] OK   irrigation_duration is optional (partial card calls work)
...
[sched]  OK   fri before 10:00 → same day (2026-07-10 10:00:00)
...
ALL OK — 6 files, 21 constants, schema, schedule logic
```

---

## Run (human path)

Install this component in a real Home Assistant instance via HACS:
1. HACS → Custom repositories → add `Hugo22000/smart-irriga-V2` (Integration)
2. Install, restart HA
3. Settings → Integrations → Add → Smart Irrigation V2

No local launch possible — the component has no entry point outside HA.

---

## Gotchas

- **`pip install homeassistant` fails** (PyRIC build error on this container).
  Not needed — smoke.py only imports `const.py` and `voluptuous` directly.
- **`const.py` cannot be imported as a package** without HA installed
  (because `__init__.py` has `from homeassistant.* import ...` at module level).
  smoke.py uses `importlib.util.spec_from_file_location` to load `const.py`
  in isolation instead.
- **No test suite exists** for this project. smoke.py IS the test harness.
- **`pytest-homeassistant-custom-component` installation fails** on this
  container (PyRIC wheel build error). The voluptuous-only smoke approach
  was chosen as the reliable alternative.

---

## Troubleshooting

| Error | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'voluptuous'` | `pip install voluptuous --break-system-packages` |
| `AssertionError` on day-of-week test | Reference date `datetime(2026, 7, 10)` must be a Friday (weekday=4) — confirmed |
| `[const] ERR` on a constant | A constant was renamed or removed from `const.py` — check recent commits |
| `[schema] ERR irrigation_duration is optional` | Regression: `CONF_IRRIGATION_DURATION` was made Required again — must be Optional |
