"""Above-Core configuration for the Homelab continuous operational loop
(RMT-CAP-04).

Plain module-level constants with environment-variable overrides. This layer
deliberately does NOT touch the Core configuration schema
(``app/core/configuration/**``) -- the loop is above-Core and its knobs live
here.

All durations are in seconds. ``LOOP_ENABLED`` is ``False`` by default: the
loop is opt-in and never runs unless explicitly turned on (env var or
``POST /homelab/loop/start``).

The values are read *dynamically* by the loop each cycle (not captured once at
construction), so a test may monkeypatch a constant on this module and the very
next cycle honours it.
"""
import os


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# Master switch. The loop task is only created when this is True.
LOOP_ENABLED = _env_bool("RMT_HOMELAB_LOOP_ENABLED", False)

# Seconds between loop cycles. The metrics collector refreshes every 60s, so
# 120s gives every cycle fresh observations.
LOOP_INTERVAL_SECONDS = _env_int("RMT_HOMELAB_LOOP_INTERVAL_SECONDS", 120)

# Flap guard: a component that accumulates LOOP_MAX_ATTEMPTS_PER_WINDOW
# held-or-failed remediation attempts within LOOP_FLAP_WINDOW_SECONDS is
# quarantined (the loop stops attempting it) until cleared.
LOOP_FLAP_WINDOW_SECONDS = _env_int("RMT_HOMELAB_LOOP_FLAP_WINDOW_SECONDS", 900)
LOOP_MAX_ATTEMPTS_PER_WINDOW = _env_int(
    "RMT_HOMELAB_LOOP_MAX_ATTEMPTS_PER_WINDOW", 3
)

# Cooldown: after any remediation attempt for a component (held, executed, or
# failed) the loop skips that component until the cooldown elapses, so
# verification / settling can complete.
LOOP_COOLDOWN_SECONDS = _env_int("RMT_HOMELAB_LOOP_COOLDOWN_SECONDS", 300)

# Consecutive healthy observations required to auto-clear a quarantine.
LOOP_RECOVERY_HEALTHY_STREAK = _env_int(
    "RMT_HOMELAB_LOOP_RECOVERY_HEALTHY_STREAK", 2
)

# Bounded in-memory cycle history retained for GET /homelab/loop/status.
LOOP_HISTORY_MAX = _env_int("RMT_HOMELAB_LOOP_HISTORY_MAX", 50)
