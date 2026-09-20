"""Strict, simulated banking-transaction risk supervisor.

This API never sends a payment instruction anywhere. The protected release
queue is the sole simulated consequential effect and is writable only by the
MCR database role. Risk policy (single-transaction limit, exposure and
concentration caps, velocity and structuring detection, sanctions and
counterparty risk tier, FX conversion and correspondent-bank screening for
cross-border transfers) is evaluated fresh against the ledger on every
proposal — nothing about it is cached in the subordinate or trusted from the
request.
"""

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
import hashlib
import hmac
import json
import os
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .database import (
    correspondent_bank_reference,
    counterparty_reference,
    fx_rate_reference,
    make_engine,
    simulated_release_queue,
    supervisory_audit_log,
)

PROPOSE_PATH = "/api/v1/supervise/propose-action"
MAX_BODY_BYTES = 16_384

# Channels are a schema-valid shape check only. Only channels this MVP has a
# real settlement policy for are authorized. internal_transfer and
# domestic_wire settle in USD only; cross_border_wire additionally requires
# an onboarded correspondent bank and goes through FX conversion.
SUPPORTED_CHANNELS = {"internal_transfer", "domestic_wire", "cross_border_wire"}
CROSS_BORDER_CHANNEL = "cross_border_wire"


class TransactionIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    transaction_id: str = Field(min_length=1, max_length=35, pattern=r"^[A-Za-z0-9/._-]+$")
    amount: str = Field(pattern=r"^(?:0|[1-9][0-9]{0,11})\.[0-9]{2}$")
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    counterparty_id: str = Field(min_length=2, max_length=35, pattern=r"^[A-Z0-9][A-Z0-9-]{1,34}$")
    correspondent_bank_id: str | None = Field(default=None, min_length=2, max_length=35, pattern=r"^[A-Z0-9][A-Z0-9-]{1,34}$")


class ActionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    agent_id: str = Field(min_length=1, max_length=64)
    channel: Literal["internal_transfer", "domestic_wire", "cross_border_wire"]
    payload: TransactionIntent

    @model_validator(mode="after")
    def _correspondent_bank_matches_channel(self):
        is_cross_border = self.channel == CROSS_BORDER_CHANNEL
        has_correspondent = self.payload.correspondent_bank_id is not None
        if is_cross_border and not has_correspondent:
            raise ValueError("correspondent_bank_id is required for cross_border_wire")
        if not is_cross_border and has_correspondent:
            raise ValueError("correspondent_bank_id is only valid for cross_border_wire")
        return self


@dataclass(frozen=True)
class RiskConfig:
    window_start: time
    window_end: time
    base_single_tx_limit: Decimal
    tier_multiplier: dict[str, Decimal]
    cross_border_limit_mult: Decimal
    counterparty_exposure_cap: Decimal
    agent_exposure_cap: Decimal
    exposure_window_hours: int
    velocity_window_seconds: int
    velocity_max_tx: int
    structuring_window_seconds: int
    structuring_near_limit_fraction: Decimal
    structuring_count_threshold: int


def _decimal_env(name: str, default: str) -> Decimal:
    value = Decimal(os.getenv(name, default))
    if not value.is_finite() or value <= 0:
        raise ValueError(f"{name} must be positive and finite")
    return value


def _int_env(name: str, default: str) -> int:
    value = int(os.getenv(name, default))
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _risk_config() -> RiskConfig:
    start = time.fromisoformat(os.getenv("MCR_WINDOW_START_UTC", "06:00"))
    end = time.fromisoformat(os.getenv("MCR_WINDOW_END_UTC", "22:00"))
    if start == end:
        raise ValueError("processing window must have nonzero duration")
    medium_mult = _decimal_env("MCR_RISK_TIER_MEDIUM_MULT", "0.50")
    high_mult = _decimal_env("MCR_RISK_TIER_HIGH_MULT", "0.10")
    cross_border_mult = _decimal_env("MCR_CROSS_BORDER_LIMIT_MULT", "0.50")
    if medium_mult > 1 or high_mult > 1 or cross_border_mult > 1:
        raise ValueError("risk tier and cross-border multipliers must not exceed 1")
    return RiskConfig(
        window_start=start,
        window_end=end,
        base_single_tx_limit=_decimal_env("MCR_BASE_RISK_LIMIT", "10000.00"),
        tier_multiplier={"LOW": Decimal("1"), "MEDIUM": medium_mult, "HIGH": high_mult},
        cross_border_limit_mult=cross_border_mult,
        counterparty_exposure_cap=_decimal_env("MCR_COUNTERPARTY_EXPOSURE_CAP", "25000.00"),
        agent_exposure_cap=_decimal_env("MCR_AGENT_EXPOSURE_CAP", "60000.00"),
        exposure_window_hours=_int_env("MCR_EXPOSURE_WINDOW_HOURS", "24"),
        velocity_window_seconds=_int_env("MCR_VELOCITY_WINDOW_SECONDS", "60"),
        velocity_max_tx=_int_env("MCR_VELOCITY_MAX_TX", "5"),
        structuring_window_seconds=_int_env("MCR_STRUCTURING_WINDOW_SECONDS", "600"),
        structuring_near_limit_fraction=_decimal_env("MCR_STRUCTURING_NEAR_LIMIT_FRACTION", "0.80"),
        structuring_count_threshold=_int_env("MCR_STRUCTURING_COUNT_THRESHOLD", "3"),
    )


def _fx_rate(connection, currency: str) -> Decimal | None:
    if currency == "USD":
        return Decimal("1")
    row = connection.execute(select(fx_rate_reference.c.usd_rate).where(fx_rate_reference.c.currency == currency)).one_or_none()
    return row.usd_rate if row else None


def evaluate_risk(proposal: ActionProposal, connection, config: RiskConfig, now: datetime | None = None) -> dict:
    """Evaluate every policy against the ledger. Read-only against the ledger;
    the caller decides whether to also write it, inside the same transaction
    so the read this decision was based on and the write it produces are
    consistent for sequential requests. Concurrent requests from the same
    agent racing inside the same window can each observe the pre-write totals
    and both pass — this MVP does not serialize proposals against each other,
    only against replay of the same transaction_id.

    All exposure, velocity, and structuring math is denominated in USD
    equivalent so a cross-currency proposal is measured on the same footing
    as a domestic one."""
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    current_time = now.time()
    in_window = (
        config.window_start <= current_time < config.window_end
        if config.window_start < config.window_end
        else current_time >= config.window_start or current_time < config.window_end
    )
    channel_supported = proposal.channel in SUPPORTED_CHANNELS
    is_cross_border = proposal.channel == CROSS_BORDER_CHANNEL
    amount = Decimal(proposal.payload.amount)

    # internal_transfer / domestic_wire settle in USD only. cross_border_wire
    # goes through the FX reference table (which also prices USD at 1:1), so
    # an unrecognized currency is rejected the same way an unrecognized
    # domestic currency would be.
    fx_rate = _fx_rate(connection, proposal.payload.currency) if is_cross_border else (Decimal("1") if proposal.payload.currency == "USD" else None)
    currency_supported = fx_rate is not None
    usd_equivalent = (amount * fx_rate).quantize(Decimal("0.01")) if fx_rate is not None else None

    reference = connection.execute(
        select(counterparty_reference.c.risk_tier, counterparty_reference.c.sanctioned).where(
            counterparty_reference.c.counterparty_id == proposal.payload.counterparty_id
        )
    ).one_or_none()
    risk_tier = reference.risk_tier if reference else "MEDIUM"
    sanctioned = bool(reference.sanctioned) if reference else False

    channel_mult = config.cross_border_limit_mult if is_cross_border else Decimal("1")
    single_tx_limit = (config.base_single_tx_limit * config.tier_multiplier[risk_tier] * channel_mult).quantize(Decimal("0.01"))
    within_single_tx_limit = usd_equivalent is not None and usd_equivalent <= single_tx_limit

    exposure_since = now - timedelta(hours=config.exposure_window_hours)
    correspondent_bank_id = proposal.payload.correspondent_bank_id
    correspondent_approved = None
    correspondent_sanctioned = None
    correspondent_nostro_used = None
    correspondent_nostro_cap = None
    within_correspondent_nostro_cap = True
    if correspondent_bank_id is not None:
        correspondent = connection.execute(
            select(
                correspondent_bank_reference.c.approved,
                correspondent_bank_reference.c.sanctioned,
                correspondent_bank_reference.c.nostro_exposure_cap,
            ).where(correspondent_bank_reference.c.correspondent_bank_id == correspondent_bank_id)
        ).one_or_none()
        correspondent_approved = bool(correspondent.approved) if correspondent else False
        correspondent_sanctioned = bool(correspondent.sanctioned) if correspondent else False
        correspondent_nostro_cap = correspondent.nostro_exposure_cap if correspondent else Decimal("0")
        correspondent_nostro_used = connection.execute(
            select(func.coalesce(func.sum(simulated_release_queue.c.amount_usd_equivalent), 0)).where(
                simulated_release_queue.c.correspondent_bank_id == correspondent_bank_id,
                simulated_release_queue.c.created_at >= exposure_since,
            )
        ).scalar_one()
        within_correspondent_nostro_cap = usd_equivalent is not None and (correspondent_nostro_used + usd_equivalent) <= correspondent_nostro_cap

    counterparty_used = connection.execute(
        select(func.coalesce(func.sum(simulated_release_queue.c.amount_usd_equivalent), 0)).where(
            simulated_release_queue.c.agent_id == proposal.agent_id,
            simulated_release_queue.c.counterparty_id == proposal.payload.counterparty_id,
            simulated_release_queue.c.created_at >= exposure_since,
        )
    ).scalar_one()
    agent_used = connection.execute(
        select(func.coalesce(func.sum(simulated_release_queue.c.amount_usd_equivalent), 0)).where(
            simulated_release_queue.c.agent_id == proposal.agent_id,
            simulated_release_queue.c.created_at >= exposure_since,
        )
    ).scalar_one()
    within_counterparty_exposure = usd_equivalent is not None and (counterparty_used + usd_equivalent) <= config.counterparty_exposure_cap
    within_agent_exposure = usd_equivalent is not None and (agent_used + usd_equivalent) <= config.agent_exposure_cap

    velocity_since = now - timedelta(seconds=config.velocity_window_seconds)
    velocity_count = connection.execute(
        select(func.count())
        .select_from(simulated_release_queue)
        .where(
            simulated_release_queue.c.agent_id == proposal.agent_id,
            simulated_release_queue.c.created_at >= velocity_since,
        )
    ).scalar_one()
    within_velocity_limit = velocity_count < config.velocity_max_tx

    # Scoped to (agent, counterparty): real structuring/smurfing is breaking
    # one transfer to a single beneficiary into several near-limit pieces. A
    # global per-agent count would let an unrelated near-limit transaction to
    # a completely different counterparty (with its own limit context) flag
    # an unrelated proposal here.
    structuring_since = now - timedelta(seconds=config.structuring_window_seconds)
    near_limit_floor = (single_tx_limit * config.structuring_near_limit_fraction).quantize(Decimal("0.01"))
    structuring_count = connection.execute(
        select(func.count())
        .select_from(simulated_release_queue)
        .where(
            simulated_release_queue.c.agent_id == proposal.agent_id,
            simulated_release_queue.c.counterparty_id == proposal.payload.counterparty_id,
            simulated_release_queue.c.created_at >= structuring_since,
            simulated_release_queue.c.amount_usd_equivalent >= near_limit_floor,
        )
    ).scalar_one()
    structuring_suspected = (
        usd_equivalent is not None and usd_equivalent >= near_limit_floor and (structuring_count + 1) >= config.structuring_count_threshold
    )

    reasons = []
    if sanctioned:
        reasons.append("sanctioned_counterparty")
    if not channel_supported:
        reasons.append("unsupported_channel")
    if not in_window:
        reasons.append("outside_processing_window")
    if not currency_supported:
        reasons.append("unsupported_currency")
    if correspondent_bank_id is not None:
        if correspondent_sanctioned:
            reasons.append("correspondent_bank_sanctioned")
        if not correspondent_approved:
            reasons.append("correspondent_bank_not_approved")
        if not within_correspondent_nostro_cap:
            reasons.append("correspondent_nostro_exposure_exceeded")
    if not within_single_tx_limit:
        reasons.append("single_transaction_limit_exceeded")
    if not within_counterparty_exposure:
        reasons.append("counterparty_exposure_exceeded")
    if not within_agent_exposure:
        reasons.append("agent_exposure_exceeded")
    if not within_velocity_limit:
        reasons.append("velocity_limit_exceeded")
    if structuring_suspected:
        reasons.append("structuring_pattern_suspected")

    return {
        "schema_valid": True,
        "evaluated_at_utc": now.isoformat(),
        "processing_window_utc": [config.window_start.isoformat(timespec="minutes"), config.window_end.isoformat(timespec="minutes")],
        "within_processing_window": in_window,
        "channel": proposal.channel,
        "channel_supported": channel_supported,
        "currency": proposal.payload.currency,
        "currency_supported": currency_supported,
        "proposed_amount": str(amount),
        "usd_equivalent_amount": str(usd_equivalent) if usd_equivalent is not None else None,
        "counterparty_id": proposal.payload.counterparty_id,
        "counterparty_risk_tier": risk_tier,
        "counterparty_sanctioned": sanctioned,
        "correspondent_bank_id": correspondent_bank_id,
        "correspondent_bank_approved": correspondent_approved,
        "correspondent_bank_sanctioned": correspondent_sanctioned,
        "correspondent_nostro_exposure_used": str(correspondent_nostro_used) if correspondent_nostro_used is not None else None,
        "correspondent_nostro_exposure_cap": str(correspondent_nostro_cap) if correspondent_nostro_cap is not None else None,
        "within_correspondent_nostro_exposure_cap": within_correspondent_nostro_cap,
        "single_transaction_limit": str(single_tx_limit),
        "within_single_transaction_limit": within_single_tx_limit,
        "counterparty_exposure_window_hours": config.exposure_window_hours,
        "counterparty_exposure_used": str(counterparty_used),
        "counterparty_exposure_cap": str(config.counterparty_exposure_cap),
        "within_counterparty_exposure_cap": within_counterparty_exposure,
        "agent_exposure_used": str(agent_used),
        "agent_exposure_cap": str(config.agent_exposure_cap),
        "within_agent_exposure_cap": within_agent_exposure,
        "velocity_window_seconds": config.velocity_window_seconds,
        "velocity_count_in_window": velocity_count,
        "velocity_max_tx": config.velocity_max_tx,
        "within_velocity_limit": within_velocity_limit,
        "structuring_window_seconds": config.structuring_window_seconds,
        "structuring_near_limit_floor": str(near_limit_floor),
        "structuring_count_in_window": structuring_count,
        "structuring_pattern_suspected": structuring_suspected,
        "reasons": reasons,
    }


def _digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _record_rejection(request: Request, body: bytes, reason: str, vector: dict, channel: str | None = None) -> int:
    agent_id = os.environ["MCR_AGENT_ID"] if _token_is_valid(request) else "unidentified"
    with request.app.state.engine.begin() as connection:
        return connection.execute(
            insert(supervisory_audit_log).values(
                agent_id=agent_id,
                channel=channel,
                payload_hash=_digest(body),
                risk_evaluation_result=vector,
                final_decision="Rejected",
                request_path=request.url.path,
                violation_reason=reason,
            ).returning(supervisory_audit_log.c.id)
        ).scalar_one()


def _token_is_valid(request: Request) -> bool:
    supplied = request.headers.get("authorization", "")
    expected = "Bearer " + os.environ["MCR_AGENT_TOKEN"]
    return hmac.compare_digest(supplied, expected)


def _parse_json(body: bytes):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(body, object_pairs_hook=unique_pairs, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


async def authenticated_proposal(request: Request) -> tuple[ActionProposal, bytes]:
    """FastAPI dependency: authenticate, strictly validate schema and identity.
    Risk-policy evaluation happens later, inside the same transaction as the
    ledger write, because it depends on ledger state."""
    body = await request.body()
    if not _token_is_valid(request):
        audit_id = _record_rejection(request, body, "invalid_agent_token", {"schema_valid": None, "reasons": ["invalid_agent_token"]})
        raise HTTPException(status_code=401, detail={"decision": "Rejected", "audit_id": audit_id, "reasons": ["invalid_agent_token"]})
    if len(body) > MAX_BODY_BYTES or request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        audit_id = _record_rejection(request, body, "invalid_request_format", {"schema_valid": False, "reasons": ["invalid_request_format"]})
        raise HTTPException(status_code=400, detail={"decision": "Rejected", "audit_id": audit_id, "reasons": ["invalid_request_format"]})
    try:
        proposal = ActionProposal.model_validate(_parse_json(body))
    except (ValueError, ValidationError, UnicodeDecodeError) as exc:
        vector = {"schema_valid": False, "reasons": ["malformed_proposal"], "validation_error": str(exc)[:500]}
        audit_id = _record_rejection(request, body, "malformed_proposal", vector)
        raise HTTPException(status_code=400, detail={"decision": "Rejected", "audit_id": audit_id, "reasons": ["malformed_proposal"]}) from exc
    if proposal.agent_id != os.environ["MCR_AGENT_ID"]:
        audit_id = _record_rejection(request, body, "agent_identity_mismatch", {"schema_valid": True, "reasons": ["agent_identity_mismatch"]}, proposal.channel)
        raise HTTPException(status_code=403, detail={"decision": "Rejected", "audit_id": audit_id, "reasons": ["agent_identity_mismatch"]})
    return proposal, body


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.risk_config = _risk_config()
    app.state.engine = make_engine()
    with app.state.engine.connect() as connection:
        connection.execute(select(supervisory_audit_log.c.id).limit(1))
    try:
        yield
    finally:
        app.state.engine.dispose()


app = FastAPI(title="MCR 2.0 Banking Risk Management Control", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)


@app.middleware("http")
async def block_alternate_paths(request: Request, call_next):
    if request.url.path not in (PROPOSE_PATH, "/health"):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            body = await request.body()
            try:
                audit_id = _record_rejection(request, body, "alternate_endpoint_attempt", {"schema_valid": None, "reasons": ["alternate_endpoint_attempt"]})
            except SQLAlchemyError:
                return JSONResponse(status_code=503, content={"decision": "Rejected", "reason": "audit_unavailable"})
            return JSONResponse(status_code=404, content={"decision": "Rejected", "audit_id": audit_id, "reasons": ["alternate_endpoint_attempt"]})
        return JSONResponse(status_code=404, content={"decision": "Rejected", "reasons": ["unknown_endpoint"]})
    try:
        return await call_next(request)
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"decision": "Rejected", "reason": "audit_unavailable"})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post(PROPOSE_PATH)
def propose_action(request: Request, evaluated: tuple[ActionProposal, bytes] = Depends(authenticated_proposal)):
    proposal, body = evaluated
    config: RiskConfig = request.app.state.risk_config
    try:
        with request.app.state.engine.begin() as connection:
            vector = evaluate_risk(proposal, connection, config)
            values = dict(
                agent_id=proposal.agent_id,
                channel=proposal.channel,
                payload_hash=_digest(body),
                risk_evaluation_result=vector,
                request_path=PROPOSE_PATH,
            )
            if vector["reasons"]:
                audit_id = connection.execute(
                    insert(supervisory_audit_log).values(**values, final_decision="Rejected", violation_reason=",".join(vector["reasons"])).returning(supervisory_audit_log.c.id)
                ).scalar_one()
                return {"decision": "Rejected", "audit_id": audit_id, "reasons": vector["reasons"]}
            audit_id = connection.execute(
                insert(supervisory_audit_log).values(**values, final_decision="Authorized").returning(supervisory_audit_log.c.id)
            ).scalar_one()
            connection.execute(
                insert(simulated_release_queue).values(
                    audit_id=audit_id,
                    agent_id=proposal.agent_id,
                    transaction_id=proposal.payload.transaction_id,
                    counterparty_id=proposal.payload.counterparty_id,
                    currency=proposal.payload.currency,
                    amount=Decimal(proposal.payload.amount),
                    amount_usd_equivalent=Decimal(vector["usd_equivalent_amount"]),
                    correspondent_bank_id=proposal.payload.correspondent_bank_id,
                    payload_hash=_digest(body),
                )
            )
    except IntegrityError as exc:
        if getattr(getattr(exc.orig, "diag", None), "constraint_name", None) != "uq_release_agent_transaction":
            raise
        audit_id = _record_rejection(request, body, "replayed_transaction_id", {"reasons": ["replayed_transaction_id"]}, proposal.channel)
        return {"decision": "Rejected", "audit_id": audit_id, "reasons": ["replayed_transaction_id"]}
    return {"decision": "Authorized", "audit_id": audit_id, "reasons": [], "payload_hash": _digest(body)}
