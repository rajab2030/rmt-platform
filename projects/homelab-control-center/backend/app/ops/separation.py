"""RMT-PROD P1 (S3) -- separation of duties for agent-originated approval holds.

Above-Core / operational. Config-gated by ``RMT_AUTH_SEPARATION`` (default
**off** -- opt-in, like every other P0/P1 toggle). No ``app/core/**`` change.

**S2-lite** made the granting / approving identity *recorded* (taken from the
authenticated operator, body values ignored). **S3** *enforces* the rule: for a
manual-approval hold that an **agent proposal** raised, the operator who
approves it (``POST /approve`` or ``POST /homelab/approve``) must not be the
operator who granted the agent's authority for it -- and must not be the
proposing agent id.

**Linking.** The Core hold carries no link back to the agent grant. So
``propose_and_govern`` records the provenance above-Core the moment it gets a
``manual_approval_required``::

    approval_id -> (grant_id, granted_by, agent_id, recorded_at)

and the two continuation routes call ``check_separation(approval_id, operator)``
before continuing.

**Scope.** Only agent-originated holds are gated (the S3 matrix line). A hold
with no provenance record -- e.g. the operator ``POST /execute`` -> hold flow --
is *not* an S3 concern and passes through.

**Lifetime.** In-memory, like ``authority_store``. A held agent proposal that
outlives a process restart cannot be continued anyway: its grant (also
in-memory) is gone and the Core hold TTL is short. Entries older than
``PROVENANCE_MAX_AGE_SECONDS`` are ignored and pruned opportunistically.

**Fail direction.** Recording provenance is fail-*open* (a bookkeeping failure
must not break a propose). The *check* is fail-*closed*: if it cannot decide it
denies the continuation, and ``RMT_AUTH_SEPARATION=false`` is the escape hatch.
"""
import logging
import time
from dataclasses import dataclass

from app.ops import ops_config

logger = logging.getLogger("rmt.ops.separation")

# Generous -- well past the Core approval-hold TTL (300s). Provenance for a
# hold that can no longer be continued is just dropped.
PROVENANCE_MAX_AGE_SECONDS = 3600


@dataclass
class HoldProvenance:
    approval_id: str
    grant_id: str | None
    granted_by: str | None
    agent_id: str | None
    recorded_at: float


_provenance: dict[str, HoldProvenance] = {}


def reset() -> None:
    """Test hook."""
    _provenance.clear()


def _prune(now: float) -> None:
    stale = [
        k
        for k, v in _provenance.items()
        if now - v.recorded_at > PROVENANCE_MAX_AGE_SECONDS
    ]
    for k in stale:
        _provenance.pop(k, None)


def record_hold_provenance(
    approval_id: str | None,
    *,
    grant_id: str | None,
    granted_by: str | None,
    agent_id: str | None,
) -> None:
    """Record who is behind an agent-raised manual-approval hold. Fail-open."""
    try:
        if not approval_id:
            return
        now = time.time()
        _prune(now)
        _provenance[approval_id] = HoldProvenance(
            approval_id=approval_id,
            grant_id=grant_id,
            granted_by=granted_by,
            agent_id=agent_id,
            recorded_at=now,
        )
        logger.debug(
            "S3: recorded hold provenance approval=%s granted_by=%s agent=%s",
            approval_id,
            granted_by,
            agent_id,
        )
    except Exception as exc:  # fail-open -- bookkeeping only
        logger.warning("S3 provenance recording skipped (non-fatal): %r", exc)


def get_hold_provenance(approval_id: str | None) -> HoldProvenance | None:
    if not approval_id:
        return None
    prov = _provenance.get(approval_id)
    if prov is None:
        return None
    if time.time() - prov.recorded_at > PROVENANCE_MAX_AGE_SECONDS:
        _provenance.pop(approval_id, None)
        return None
    return prov


def separation_enabled() -> bool:
    return ops_config.separation_enabled()


def check_separation(approval_id: str | None, approver: str | None):
    """Return ``(ok: bool, reason: str)`` for continuing ``approval_id`` as
    ``approver``.

    ``ok`` values / reasons:
      * ``True,  "separation_disabled"``  -- toggle off (the default)
      * ``True,  "not_agent_originated"`` -- no provenance -> not an S3 concern
      * ``True,  "ok"``                   -- distinct identities
      * ``False, "approver_is_grantor"``  -- approver granted the authority
      * ``False, "approver_is_proposer"`` -- approver == the proposing agent id
      * ``False, "separation_check_error"`` -- fail-closed on an internal error
    """
    try:
        if not separation_enabled():
            return True, "separation_disabled"

        prov = get_hold_provenance(approval_id)
        if prov is None:
            return True, "not_agent_originated"

        if approver and prov.granted_by and approver == prov.granted_by:
            logger.warning(
                "S3: blocked continuation of agent hold %s -- approver %r is "
                "the grantor of grant %s",
                approval_id,
                approver,
                prov.grant_id,
            )
            return False, "approver_is_grantor"

        if approver and prov.agent_id and approver == prov.agent_id:
            logger.warning(
                "S3: blocked continuation of agent hold %s -- approver %r is "
                "the proposing agent",
                approval_id,
                approver,
            )
            return False, "approver_is_proposer"

        return True, "ok"
    except Exception as exc:  # fail-closed -- this is a security gate
        logger.error(
            "S3 separation check failed for approval=%s (denying; set "
            "RMT_AUTH_SEPARATION=false to bypass): %r",
            approval_id,
            exc,
        )
        return False, "separation_check_error"
