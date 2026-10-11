"""RMT-CAP-13 -- orchestration: bundle -> prompt -> model -> validate -> store.

The model client is injected (anything with ``generate(prompt) -> str``); the
default is CAP-05's stdlib Ollama client. Every outcome -- success or refusal --
is stored. Nothing here can execute, authorize or approve anything.
"""
import logging

from app.reasoning import collect, prompt as prompt_mod, store, validate as validate_mod
from app.reasoning.validate import ExplainError

logger = logging.getLogger("rmt.reasoning")


def default_client():
    from app.agent.llm_client import LlmClient

    return LlmClient()


def explain(
    *,
    incident_ref: str,
    action_id=None,
    approval_id=None,
    execution_id=None,
    requested_by: str | None = None,
    client=None,
) -> dict:
    """Returns the stored attempt record (``status`` ``ok`` or a refusal)."""
    bundle = collect.build_bundle(
        incident_ref=incident_ref,
        action_id=action_id,
        approval_id=approval_id,
        execution_id=execution_id,
    )
    bundle_hash = bundle.sha256()

    if bundle.is_empty:
        # No evidence: do not ask a model to speak about nothing.
        return store.append(
            incident_ref=incident_ref,
            requested_by=requested_by,
            status="no_evidence",
            input_bundle_sha256=bundle_hash,
            detail="no evidence records found for this incident",
        )

    prompt_text = prompt_mod.build_prompt(bundle)
    common = dict(
        incident_ref=incident_ref,
        requested_by=requested_by,
        prompt_sha256=prompt_mod.prompt_sha256(prompt_text),
        input_bundle_sha256=bundle_hash,
    )

    raw = None
    model = host = temperature = None
    try:
        client = client or default_client()
        model = getattr(client, "model", None)
        host = getattr(client, "host", None)
        from app.agent import loop_config

        temperature = loop_config.AGENT_LLM_TEMPERATURE
        raw = client.generate(prompt_text)
    except Exception as exc:  # noqa: BLE001 -- any model failure is a stored refusal
        logger.warning("reasoning.explain: llm error: %r", exc)
        return store.append(
            **common,
            model=model,
            host=host,
            temperature=temperature,
            status="llm_error",
            detail=f"{type(exc).__name__}: {exc}",
        )

    meta = dict(model=model, host=host, temperature=temperature, raw_output=raw)
    try:
        result = validate_mod.validate(raw, bundle)
    except ExplainError as err:
        return store.append(**common, **meta, status=err.status, detail=err.detail)
    except Exception as exc:  # noqa: BLE001 -- never let validation bugs escape as 500s
        logger.exception("reasoning.explain: validator crashed")
        return store.append(**common, **meta, status="invalid", detail=f"validator error: {exc}")

    return store.append(
        **common,
        **meta,
        status="ok",
        validated=result.as_dict(),
        dropped_claims=result.dropped_claims,
        detail="; ".join(result.notes),
    )
