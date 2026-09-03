from app.core.intelligence.verification.models import (
    VerificationResult,
    VerificationStatus,
    ExpectedOutcome,
    ObservedState,
)
from app.core.intelligence.verification.verifier import verifier
from app.core.intelligence.verification.storage import verification_storage
from app.core.module_registry.registry import get_modules


def _module_registry_observer(target: str):
    """
    Trusted internal observer that reads actual module-registry state.

    This is the C06 module-change verification authority. It is never
    caller-controlled: it reports the observed registry state, which the
    verifier compares against the expected outcome. Adapter success alone
    cannot manufacture verified_success.
    """
    def observe():
        modules = get_modules()
        for m in modules:
            if m.name == target or m.runtime.container == target:
                return ObservedState(
                    target=target,
                    state="registered",
                    source="module_registry",
                )
        return ObservedState(
            target=target,
            state="not_registered",
            source="module_registry",
        )
    return observe


def _resolve_trusted_observer(execution_request):
    """
    Resolve a trusted internal observer for a governed execution request.

    Returns None when no trusted observer applies, so verification fails safe
    (observation_unavailable) rather than manufacturing verified_success.
    """
    if execution_request is None:
        return None
    operation = (execution_request.operation or "").lower()
    parameters = execution_request.parameters or {}
    if operation == "create" and parameters.get("module_name"):
        return _module_registry_observer(parameters["module_name"])
    return None


def verify_execution(
    execution_id: str,
    expected: ExpectedOutcome | None,
    execution_request=None,
) -> VerificationResult:
    """
    Execute -> Observe -> Verify -> Record.

    The observer is resolved internally from a trusted source based on the
    execution request; it is never accepted from a caller. If observation is
    unavailable, or the verifier itself fails, the corresponding verification
    outcome is recorded.

    The expected outcome is passed in explicitly; it is never derived here.
    """
    observer = _resolve_trusted_observer(execution_request)

    observed = None
    if observer is not None:
        try:
            observed = observer()
        except Exception:
            observed = None

    try:
        result = verifier.verify(execution_id, expected, observed)
    except Exception:
        result = VerificationResult(
            execution_id=execution_id,
            status=VerificationStatus.VERIFICATION_FAILURE,
            expected=expected,
            observed=observed,
            reason="Verifier failure",
        )

    verification_storage.save(result)

    return result
