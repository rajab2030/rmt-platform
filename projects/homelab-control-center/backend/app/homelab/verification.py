"""Above-Core Homelab/Docker post-execution verification integration (G1).

Uses the existing frozen verification mechanism (verifier.verify) and the
existing verification storage. The above-Core Docker observer supplies the
observed state; the existing verifier decides the outcome. This is NOT a
parallel verification system - it is the same verification boundary, fed by
an above-Core observer.

Outcomes (via the existing verifier):
  * verified_success        - observed state matches expected
  * state_mismatch          - observed state differs from expected
  * observation_unavailable - state could not be observed
  * verification_failure    - verifier itself failed (e.g. no expected outcome)
"""
from app.core.intelligence.verification.verifier import verifier
from app.core.intelligence.verification.storage import verification_storage
from app.homelab.observer import observe_container_state


def verify_docker_execution(execution_id: str, expected, target: str):
    """Verify a governed Docker execution against actual container state.

    Resolves the trusted Docker observer, then delegates to the existing
    verifier and persists the result through the existing verification
    storage. Returns the VerificationResult.
    """
    observed = observe_container_state(target)
    result = verifier.verify(execution_id, expected, observed)
    verification_storage.save(result)
    return result
