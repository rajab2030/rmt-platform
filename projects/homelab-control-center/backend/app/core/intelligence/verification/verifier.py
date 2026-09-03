from app.core.intelligence.verification.models import (
    VerificationResult,
    VerificationStatus,
    ExpectedOutcome,
    ObservedState,
)


class Verifier:
    """
    Generic post-execution verifier.

    Compares an explicit ExpectedOutcome against an ObservedState and
    returns one of the four supported verification outcomes:

        - verified_success
        - state_mismatch
        - observation_unavailable
        - verification_failure

    The verifier never derives or manufactures the expected outcome. It only
    compares the expectation it is given against the observed state.
    """

    def verify(
        self,
        execution_id: str,
        expected: ExpectedOutcome | None,
        observed: ObservedState | None,
    ) -> VerificationResult:

        if expected is None:
            return VerificationResult(
                execution_id=execution_id,
                status=VerificationStatus.VERIFICATION_FAILURE,
                expected=None,
                observed=observed,
                reason="No expected outcome supplied",
            )

        if observed is None:
            return VerificationResult(
                execution_id=execution_id,
                status=VerificationStatus.OBSERVATION_UNAVAILABLE,
                expected=expected,
                observed=None,
                reason="Observation unavailable",
            )

        if observed.state == expected.expected_state:
            return VerificationResult(
                execution_id=execution_id,
                status=VerificationStatus.VERIFIED_SUCCESS,
                expected=expected,
                observed=observed,
                reason="Observed state matches expected outcome",
            )

        return VerificationResult(
            execution_id=execution_id,
            status=VerificationStatus.STATE_MISMATCH,
            expected=expected,
            observed=observed,
            reason=(
                f"Expected state '{expected.expected_state}' "
                f"but observed '{observed.state}'"
            ),
        )


verifier = Verifier()
