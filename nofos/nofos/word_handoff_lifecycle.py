"""Pure, synthetic-only lifecycle rules for proposed Word handoffs.

This module neither authenticates callers nor persists transitions. A future trusted
adapter must enforce authorization, atomic compare-and-swap, and side-effect safety.
"""

from dataclasses import dataclass, replace
from enum import StrEnum


class HandoffState(StrEnum):
    RECEIVED = "received"
    QUEUED = "queued"
    PROCESSING = "processing"
    AWAITING_REVIEW = "awaiting_review"
    ACCEPTED = "accepted"
    FAILED = "failed"
    REJECTED = "rejected"


class HandoffEvent(StrEnum):
    QUEUE = "queue"
    START = "start"
    COMPLETE_PROCESSING = "complete_processing"
    ACCEPT = "accept"
    REJECT = "reject"
    FAIL = "fail"
    RETRY = "retry"


class FailureCode(StrEnum):
    VALIDATION_FAILED = "VALIDATION_FAILED"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    PROCESSING_TIMEOUT = "PROCESSING_TIMEOUT"
    REVIEW_ARTIFACT_FAILED = "REVIEW_ARTIFACT_FAILED"


class TransitionError(ValueError):
    """A lifecycle event is invalid for the supplied snapshot."""


class StaleTransitionError(TransitionError):
    """The caller's expected state or revision does not match the snapshot."""


@dataclass(frozen=True)
class ReviewDecision:
    """Review evidence supplied by a future trusted authorization adapter.

    Constructing this value is *not* proof that the person was authenticated or
    authorized. The adapter must verify both before invoking a transition.
    """

    reviewer_id: str
    authorization_reference: str
    decision_id: str

    def __post_init__(self):
        if not all(
            isinstance(value, str) and value.strip()
            for value in (
                self.reviewer_id,
                self.authorization_reference,
                self.decision_id,
            )
        ):
            raise ValueError("Review evidence fields must be nonempty strings")


@dataclass(frozen=True)
class HandoffLifecycle:
    """Immutable lifecycle snapshot carrying the stable source identity."""

    handoff_id: str
    source_system: str
    source_record_id: str
    source_version: str
    state: HandoffState = HandoffState.RECEIVED
    revision: int = 0
    attempt: int = 0
    failure_code: FailureCode | None = None
    review: ReviewDecision | None = None

    def __post_init__(self):
        if not all(
            isinstance(value, str) and value.strip()
            for value in (
                self.handoff_id,
                self.source_system,
                self.source_record_id,
                self.source_version,
            )
        ):
            raise ValueError("Handoff identity fields must be nonempty strings")
        if not isinstance(self.state, HandoffState):
            raise ValueError("state must be a HandoffState")
        if type(self.revision) is not int or self.revision < 0:
            raise ValueError("revision must be a nonnegative integer")
        if type(self.attempt) is not int or self.attempt < 0:
            raise ValueError("attempt must be a nonnegative integer")

    @property
    def source_key(self) -> tuple[str, str, str]:
        return (self.source_system, self.source_record_id, self.source_version)


_NEXT_STATE = {
    (HandoffState.RECEIVED, HandoffEvent.QUEUE): HandoffState.QUEUED,
    (HandoffState.QUEUED, HandoffEvent.START): HandoffState.PROCESSING,
    (
        HandoffState.PROCESSING,
        HandoffEvent.COMPLETE_PROCESSING,
    ): HandoffState.AWAITING_REVIEW,
    (HandoffState.AWAITING_REVIEW, HandoffEvent.ACCEPT): HandoffState.ACCEPTED,
    (HandoffState.AWAITING_REVIEW, HandoffEvent.REJECT): HandoffState.REJECTED,
    (HandoffState.FAILED, HandoffEvent.RETRY): HandoffState.QUEUED,
    **{
        (state, HandoffEvent.FAIL): HandoffState.FAILED
        for state in (
            HandoffState.RECEIVED,
            HandoffState.QUEUED,
            HandoffState.PROCESSING,
            HandoffState.AWAITING_REVIEW,
        )
    },
}


def transition(
    snapshot: HandoffLifecycle,
    event: HandoffEvent,
    *,
    expected_state: HandoffState,
    expected_revision: int,
    failure_code: FailureCode | None = None,
    review: ReviewDecision | None = None,
) -> HandoffLifecycle:
    """Return a new snapshot or reject a stale/invalid event; perform no I/O."""

    if not isinstance(snapshot, HandoffLifecycle) or not isinstance(
        event, HandoffEvent
    ):
        raise TypeError("snapshot and event must be lifecycle types")
    if snapshot.state != expected_state or snapshot.revision != expected_revision:
        raise StaleTransitionError("Handoff state or revision is stale")
    next_state = _NEXT_STATE.get((snapshot.state, event))
    if next_state is None:
        raise TransitionError(f"Cannot {event.value} a {snapshot.state.value} handoff")

    if event is HandoffEvent.FAIL:
        if not isinstance(failure_code, FailureCode):
            raise TransitionError("Failure requires a defined error code")
    elif failure_code is not None:
        raise TransitionError("Only failure events may provide a failure code")

    if event in (HandoffEvent.ACCEPT, HandoffEvent.REJECT):
        if not isinstance(review, ReviewDecision):
            raise TransitionError("A human review decision is required")
    elif review is not None:
        raise TransitionError("Review evidence is only valid for a review decision")

    return replace(
        snapshot,
        state=next_state,
        revision=snapshot.revision + 1,
        attempt=snapshot.attempt + (event in (HandoffEvent.QUEUE, HandoffEvent.RETRY)),
        failure_code=failure_code,
        review=review,
    )
