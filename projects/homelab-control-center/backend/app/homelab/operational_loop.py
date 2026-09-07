"""Above-Core Homelab continuous operational loop (RMT-CAP-04).

Runs the *existing* single-shot Homelab governed lifecycle on a cadence, under
supervision. This module adds **cadence and guardrails only** -- it introduces
no new mutation path.

  cycle -> for each policy component -> remediate_component(component)
        -> classify governed outcome -> update per-component loop state
        -> append a bounded cycle record

``remediate_component`` is the existing entrypoint
(``app/homelab/remediation.py``); it routes through
``execute_governed_action`` -> Govern -> Authorize -> Execute -> Verify ->
Learn. The loop calls that and nothing lower.

Guarantees (see ``docs/RMT_CAP_04_PROPOSAL.md``):
  * Approval retained -- a ``manual_approval_required`` outcome is recorded and
    surfaced; the loop NEVER continues a hold. A human calls
    ``POST /homelab/approve``. ``continue_remediation`` is not imported here.
  * Flap guard -- after N held/failed attempts in a window a component is
    quarantined; the loop stops attempting it (read-only health checks only)
    until it recovers or is manually cleared.
  * Cooldown -- after any remediation attempt a component is skipped until the
    cooldown elapses.
  * Single-flight -- cycles never overlap.
  * Fail-safe -- a per-component or per-cycle fault is recorded; the loop task
    stays alive and never raises into the app.
  * Learning stays append-only / read-only: the loop only *records* state
    transitions (quarantine / recovery) via the existing Core memory
    capability; it does not authorize or execute.

No ``app/core/**`` file is touched.
"""
import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.homelab import loop_config
from app.homelab.remediation import REMEDIATION_POLICY, remediate_component
from app.homelab.observer import observe_container_state
from app.core.intelligence.memory.models import MemoryRecord
from app.core.intelligence.memory.service import remember


# Governed-outcome classification (statuses come from
# app/core/intelligence/actions/service.py + the homelab wiring).
_HEALTHY = {"no_remediation"}
_HELD = {"manual_approval_required"}
_COUNTS_TOWARD_FLAP = {
    "manual_approval_required",
    "policy_denied",
    "rejected",
    "authorization_not_created",
    "error",
}
_SETS_COOLDOWN = _COUNTS_TOWARD_FLAP | {"executed"}

# Read-only recovery signal for a quarantined component.
_HEALTHY_OBSERVED_STATES = {"running"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value):
    return value.isoformat() if isinstance(value, datetime) else None


@dataclass
class ComponentLoopState:
    component: str
    last_outcome: str | None = None
    last_detail: str | None = None
    last_attempt_at: datetime | None = None
    cooldown_until: datetime | None = None
    attempt_times: list = field(default_factory=list)
    consecutive_failures: int = 0
    healthy_streak: int = 0
    quarantined: bool = False
    quarantined_at: datetime | None = None
    quarantine_reason: str | None = None

    def prune_window(self, window_seconds: int, now: datetime) -> None:
        self.attempt_times = [
            t
            for t in self.attempt_times
            if (now - t).total_seconds() <= window_seconds
        ]

    def as_dict(self) -> dict:
        return {
            "component": self.component,
            "last_outcome": self.last_outcome,
            "last_detail": self.last_detail,
            "last_attempt_at": _iso(self.last_attempt_at),
            "cooldown_until": _iso(self.cooldown_until),
            "attempts_in_window": len(self.attempt_times),
            "consecutive_failures": self.consecutive_failures,
            "healthy_streak": self.healthy_streak,
            "quarantined": self.quarantined,
            "quarantined_at": _iso(self.quarantined_at),
            "quarantine_reason": self.quarantine_reason,
        }


class HomelabOperationalLoop:
    """Supervised periodic driver around the existing governed Homelab
    lifecycle. Holds all loop state in memory; owns a single asyncio task."""

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._cycle_in_progress = False
        self.reset()

    # -- lifecycle -------------------------------------------------------

    def reset(self) -> None:
        """Drop all loop state (test helper / clean restart). Does not touch
        the asyncio task."""
        self._components: dict[str, ComponentLoopState] = {}
        self._history = deque(maxlen=loop_config.LOOP_HISTORY_MAX)
        self._cycle_count = 0
        self._last_cycle_at: datetime | None = None
        self._last_cycle_error: str | None = None
        self._enabled = False
        self._cycle_in_progress = False

    def start(self) -> dict:
        """Enable the loop and create the driving task if the event loop is
        running. Idempotent."""
        self._enabled = True
        try:
            if self._task is None or self._task.done():
                self._task = asyncio.get_running_loop().create_task(self.run())
        except RuntimeError:
            # No running loop (e.g. called from a plain sync context in a
            # test). Enabled flag is set; the caller drives cycles directly.
            pass
        return self.get_status()

    def stop(self) -> dict:
        """Disable the loop and cancel the driving task. Idempotent."""
        self._enabled = False
        if self._task is not None and not self._task.done():
            self._task.cancel()
        self._task = None
        return self.get_status()

    async def run(self) -> None:
        """Driving coroutine: one cycle, then sleep, forever. A cycle fault is
        contained; only cancellation stops the loop.

        ``run_cycle_once`` is called directly (not off-thread): at a 120s
        cadence over a tiny component set the brief blocking is acceptable and
        keeps loop state single-threaded and overlap-free.
        """
        try:
            while True:
                try:
                    self.run_cycle_once()
                except Exception as exc:  # defensive: never kill the loop
                    self._last_cycle_error = repr(exc)
                await asyncio.sleep(loop_config.LOOP_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            raise

    # -- one cycle ----------------------------------------------------------

    def run_cycle_once(self) -> dict:
        """Process every policy component once. Single-flight: a re-entrant
        call is refused. Never raises."""
        if self._cycle_in_progress:
            return {"status": "cycle_already_in_progress"}

        self._cycle_in_progress = True
        try:
            now = _now()
            self._cycle_count += 1
            self._last_cycle_at = now
            results = []
            for component in list(REMEDIATION_POLICY.keys()):
                try:
                    results.append(self._process_component(component, now))
                except Exception as exc:  # defensive: isolate one component
                    state = self._get_state(component)
                    self._register_failure(state, "error", repr(exc), now)
                    self._maybe_quarantine(state, now)
                    results.append(
                        {
                            "component": component,
                            "outcome": "error",
                            "detail": repr(exc),
                        }
                    )

            record = {
                "cycle": self._cycle_count,
                "at": _iso(now),
                "results": results,
            }
            self._history.append(record)
            return {"status": "ok", **record}
        finally:
            self._cycle_in_progress = False

    def _process_component(self, component: str, now: datetime) -> dict:
        state = self._get_state(component)

        # Quarantined: read-only recovery check only. Never remediate.
        if state.quarantined:
            return self._check_recovery(state, now)

        # Cooldown: skip until it elapses.
        if state.cooldown_until is not None and now < state.cooldown_until:
            return {
                "component": component,
                "outcome": "skipped_cooldown",
                "detail": f"cooldown until {_iso(state.cooldown_until)}",
            }

        outcome = remediate_component(component)
        status = str(outcome.get("status", "unknown"))
        detail = outcome.get("reason") or outcome.get("approval_id") or status

        state.last_outcome = status
        state.last_detail = str(detail)
        state.last_attempt_at = now

        if status in _HEALTHY:
            state.attempt_times = []
            state.consecutive_failures = 0
            state.healthy_streak += 1
        elif status == "executed":
            state.attempt_times = []
            state.consecutive_failures = 0
            state.healthy_streak = 0
            state.cooldown_until = self._cooldown_from(now)
        elif status == "no_observation":
            # Missing data, not a flap; record and move on.
            pass
        else:
            self._register_failure(state, status, str(detail), now)

        self._maybe_quarantine(state, now)

        return {
            "component": component,
            "outcome": status,
            "detail": str(detail),
            "quarantined": state.quarantined,
        }

    # -- state transitions ------------------------------------------------

    def _register_failure(
        self, state: ComponentLoopState, status: str, detail: str, now: datetime
    ) -> None:
        state.last_outcome = status
        state.last_detail = detail
        state.last_attempt_at = now
        state.consecutive_failures += 1
        if status in _COUNTS_TOWARD_FLAP:
            state.attempt_times.append(now)
        if status in _SETS_COOLDOWN:
            state.cooldown_until = self._cooldown_from(now)

    def _maybe_quarantine(
        self, state: ComponentLoopState, now: datetime
    ) -> None:
        if state.quarantined:
            return
        state.prune_window(loop_config.LOOP_FLAP_WINDOW_SECONDS, now)
        if len(state.attempt_times) >= loop_config.LOOP_MAX_ATTEMPTS_PER_WINDOW:
            state.quarantined = True
            state.quarantined_at = now
            state.quarantine_reason = (
                f"{len(state.attempt_times)} held/failed remediation attempts "
                f"within {loop_config.LOOP_FLAP_WINDOW_SECONDS}s "
                f"(last: {state.last_outcome})"
            )
            state.healthy_streak = 0
            self._record_transition(
                state.component,
                "homelab_loop_quarantine",
                {
                    "reason": state.quarantine_reason,
                    "last_outcome": state.last_outcome,
                    "attempts_in_window": len(state.attempt_times),
                },
            )

    def _check_recovery(
        self, state: ComponentLoopState, now: datetime
    ) -> dict:
        observed = observe_container_state(state.component)
        observed_state = observed.state if observed is not None else None
        healthy = observed_state in _HEALTHY_OBSERVED_STATES

        if healthy:
            state.healthy_streak += 1
        else:
            state.healthy_streak = 0

        cleared = False
        if (
            healthy
            and state.healthy_streak
            >= loop_config.LOOP_RECOVERY_HEALTHY_STREAK
        ):
            self._do_clear_quarantine(
                state, now, "homelab_loop_recovery", observed_state
            )
            cleared = True

        return {
            "component": state.component,
            "outcome": "quarantined",
            "detail": (
                f"observed={observed_state} healthy_streak={state.healthy_streak}"
                + (" -> cleared" if cleared else "")
            ),
            "quarantined": state.quarantined,
        }

    def clear_quarantine(self, component: str) -> dict:
        """Manually clear a component's quarantine (operator action)."""
        state = self._components.get(component)
        if state is None or not state.quarantined:
            return {
                "component": component,
                "status": "not_quarantined",
                "state": state.as_dict() if state is not None else None,
            }
        self._do_clear_quarantine(
            state, _now(), "homelab_loop_quarantine_cleared", "manual"
        )
        return {
            "component": component,
            "status": "quarantine_cleared",
            "state": state.as_dict(),
        }

    def _do_clear_quarantine(
        self,
        state: ComponentLoopState,
        now: datetime,
        event_type: str,
        trigger,
    ) -> None:
        state.quarantined = False
        state.quarantined_at = None
        prior_reason = state.quarantine_reason
        state.quarantine_reason = None
        state.attempt_times = []
        state.consecutive_failures = 0
        state.cooldown_until = None
        self._record_transition(
            state.component,
            event_type,
            {"trigger": trigger, "prior_reason": prior_reason},
        )

    def _record_transition(
        self, component: str, event_type: str, data: dict
    ) -> None:
        """Append-only Learn record for a loop state transition, via the
        existing Core memory capability. Distinct ``event_type`` keeps these
        out of the remediation-outcome record stream."""
        try:
            remember(
                MemoryRecord(
                    component=component,
                    event_type=event_type,
                    timestamp=_now(),
                    data=data,
                )
            )
        except Exception as exc:  # recording must never break the loop
            self._last_cycle_error = f"transition-record-failed: {exc!r}"

    # -- helpers ----------------------------------------------------------

    def _get_state(self, component: str) -> ComponentLoopState:
        state = self._components.get(component)
        if state is None:
            state = ComponentLoopState(component=component)
            self._components[component] = state
        return state

    @staticmethod
    def _cooldown_from(now: datetime) -> datetime:
        from datetime import timedelta

        return now + timedelta(seconds=loop_config.LOOP_COOLDOWN_SECONDS)

    # -- read-only status -----------------------------------------------

    def get_status(self) -> dict:
        return {
            "enabled": self._enabled,
            "running": self._task is not None and not self._task.done(),
            "interval_seconds": loop_config.LOOP_INTERVAL_SECONDS,
            "cycle_count": self._cycle_count,
            "last_cycle_at": _iso(self._last_cycle_at),
            "last_cycle_error": self._last_cycle_error,
            "policy_components": list(REMEDIATION_POLICY.keys()),
            "components": {
                name: state.as_dict()
                for name, state in self._components.items()
            },
            "history": list(self._history),
            "config": {
                "flap_window_seconds": loop_config.LOOP_FLAP_WINDOW_SECONDS,
                "max_attempts_per_window": (
                    loop_config.LOOP_MAX_ATTEMPTS_PER_WINDOW
                ),
                "cooldown_seconds": loop_config.LOOP_COOLDOWN_SECONDS,
                "recovery_healthy_streak": (
                    loop_config.LOOP_RECOVERY_HEALTHY_STREAK
                ),
            },
        }


# Module-level singleton driven by app/main.py.
operational_loop = HomelabOperationalLoop()
