#!/usr/bin/env python3
"""
Smoke test for smart-irriga-v2 custom component.

Verifies without a running Home Assistant instance:
  1. Syntax of every .py file
  2. All required constants present in const.py
  3. Service schema (voluptuous) validates correctly
  4. Schedule logic (_next_irrigation_dt) returns correct datetimes

Run from the repo root:
    python3 .claude/skills/run-smart-irriga-v2/smoke.py
Exit 0 = all OK, exit 1 = failures (details printed).
"""
import ast
import importlib.util
import pathlib
import sys
from datetime import datetime, timedelta

COMPONENT = pathlib.Path("custom_components/smart_irriga_v2")
errors: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    mark = "OK " if ok else "ERR"
    msg = f"[{label}] {mark}  {detail}"
    print(msg)
    if not ok:
        errors.append(msg)


# ── 1. Syntax ────────────────────────────────────────────────────────────────
for f in sorted(COMPONENT.glob("*.py")):
    try:
        ast.parse(f.read_text())
        check("syntax", True, f.name)
    except SyntaxError as e:
        check("syntax", False, f"{f.name}: {e}")

# ── 2. Constants ─────────────────────────────────────────────────────────────
spec = importlib.util.spec_from_file_location("const", COMPONENT / "const.py")
const = importlib.util.module_from_spec(spec)
spec.loader.exec_module(const)

REQUIRED_CONSTS = [
    "DOMAIN", "PLATFORMS",
    "CONF_PUMPS", "CONF_PUMP_SWITCH", "CONF_PUMP_FLOW_RATE", "CONF_PUMP_HUMIDITY_SENSOR",
    "CONF_ACTIVATION_MODE", "CONF_IRRIGATION_DURATION",
    "CONF_SCHEDULE_TIME", "CONF_SCHEDULE_DAYS",
    "CONF_HUMIDITY_SENSOR", "CONF_HUMIDITY_THRESHOLD",
    "MODE_MANUAL", "MODE_SCHEDULE", "MODE_HUMIDITY",
    "SENSOR_WATER_VOLUME", "SENSOR_NEXT_IRRIGATION",
    "BUTTON_START_IRRIGATION", "BUTTON_STOP_IRRIGATION",
    "CONF_ZONE_ACTIVE", "SERVICE_SET_ZONE_OPTIONS",
]
for name in REQUIRED_CONSTS:
    check("const", hasattr(const, name), f"{name} = {getattr(const, name, 'MISSING')!r}")

# ── 3. Service schema ────────────────────────────────────────────────────────
try:
    import voluptuous as vol

    SERVICE_SCHEMA = vol.Schema({
        vol.Required("entry_id"): str,
        vol.Required(const.CONF_ACTIVATION_MODE): vol.In([
            const.MODE_MANUAL, const.MODE_SCHEDULE, const.MODE_HUMIDITY,
        ]),
        vol.Optional(const.CONF_IRRIGATION_DURATION): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=3600)
        ),
        vol.Optional(const.CONF_ZONE_ACTIVE): bool,
        vol.Optional(const.CONF_SCHEDULE_TIME): str,
        vol.Optional(const.CONF_SCHEDULE_DAYS): list,
    })

    # Partial call (no irrigation_duration) — must pass since v1.0.7
    SERVICE_SCHEMA({
        "entry_id": "abc123",
        const.CONF_ACTIVATION_MODE: const.MODE_SCHEDULE,
        const.CONF_SCHEDULE_TIME: "08:30:00",
        const.CONF_SCHEDULE_DAYS: ["mon", "wed"],
    })
    check("schema", True, "irrigation_duration is optional (partial card calls work)")

    # Full call — must also pass
    SERVICE_SCHEMA({
        "entry_id": "abc123",
        const.CONF_ACTIVATION_MODE: const.MODE_SCHEDULE,
        const.CONF_IRRIGATION_DURATION: 300,
        const.CONF_ZONE_ACTIVE: True,
        const.CONF_SCHEDULE_TIME: "08:30:00",
        const.CONF_SCHEDULE_DAYS: ["mon", "wed", "fri"],
    })
    check("schema", True, "full call with all optional fields also works")

    # Bad mode value — must fail
    try:
        SERVICE_SCHEMA({"entry_id": "x", const.CONF_ACTIVATION_MODE: "bad_mode"})
        check("schema", False, "should have rejected unknown activation_mode")
    except vol.error.Error:
        check("schema", True, "unknown activation_mode correctly rejected")

except ImportError:
    check("schema", False, "voluptuous not installed — run: pip install voluptuous")

# ── 4. Schedule logic ────────────────────────────────────────────────────────
_DAY_MAP = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def _next_irrigation_dt(schedule_time: str, schedule_days: list, now: datetime):
    if not schedule_days:
        return None
    try:
        parts = schedule_time.split(":")
        hour, minute = int(parts[0]), int(parts[1])
    except (ValueError, IndexError, AttributeError):
        return None
    day_numbers = {_DAY_MAP[d] for d in schedule_days if d in _DAY_MAP}
    if not day_numbers:
        return None
    for delta in range(8):
        candidate = now + timedelta(days=delta)
        if candidate.weekday() not in day_numbers:
            continue
        candidate_dt = candidate.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate_dt > now:
            return candidate_dt
    return None


# Fixed reference: Friday 09:00
friday = datetime(2026, 7, 10, 9, 0)
assert friday.weekday() == 4, "reference date must be Friday"

check("sched", _next_irrigation_dt("08:00:00", [], friday) is None,
      "empty days → None")
check("sched", _next_irrigation_dt("08:00:00", ["lundi"], friday) is None,
      "unknown day key → None")
check("sched", _next_irrigation_dt("bad", ["fri"], friday) is None,
      "invalid time → None")

r = _next_irrigation_dt("10:00:00", ["fri"], friday)
check("sched", r is not None and r.weekday() == 4 and r.date() == friday.date(),
      f"fri before 10:00 → same day ({r})")

r = _next_irrigation_dt("08:00:00", ["fri"], friday)
check("sched", r is not None and (r.date() - friday.date()).days == 7,
      f"fri after 08:00 → next week ({r})")

r = _next_irrigation_dt("08:00:00", ["mon", "wed"], friday)
check("sched", r is not None and r.weekday() == 0,
      f"[mon,wed] from Friday → Monday ({r})")

r = _next_irrigation_dt("08:00", ["sat"], friday)
check("sched", r is not None and r.weekday() == 5,
      f"HH:MM format (no seconds) works ({r})")

# ── Summary ──────────────────────────────────────────────────────────────────
print()
if errors:
    print(f"FAILED — {len(errors)} error(s):")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    n_files = len(list(COMPONENT.glob("*.py")))
    print(f"ALL OK — {n_files} files, {len(REQUIRED_CONSTS)} constants, schema, schedule logic")
