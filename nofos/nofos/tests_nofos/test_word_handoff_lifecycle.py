"""Synthetic lifecycle contract tests; no document, service, or database I/O."""

import unittest

from nofos.word_handoff_lifecycle import (
    FailureCode,
    HandoffEvent,
    HandoffLifecycle,
    HandoffState,
    ReviewDecision,
    StaleTransitionError,
    TransitionError,
    transition,
)


class WordHandoffLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.initial = HandoffLifecycle(
            handoff_id="synthetic-handoff-1",
            source_system="announcement-services",
            source_record_id="SYNTHETIC-COMP-1",
            source_version="v1",
        )
        self.review = ReviewDecision(
            reviewer_id="synthetic-reviewer",
            authorization_reference="synthetic-authorization-check",
            decision_id="synthetic-decision-1",
        )

    def advance(self, snapshot, event, **kwargs):
        return transition(
            snapshot,
            event,
            expected_state=snapshot.state,
            expected_revision=snapshot.revision,
            **kwargs,
        )

    def test_complete_path_preserves_source_identity_and_requires_review(self):
        snapshot = self.initial
        for event, expected_state in (
            (HandoffEvent.QUEUE, HandoffState.QUEUED),
            (HandoffEvent.START, HandoffState.PROCESSING),
            (HandoffEvent.COMPLETE_PROCESSING, HandoffState.AWAITING_REVIEW),
        ):
            snapshot = self.advance(snapshot, event)
            self.assertEqual(snapshot.state, expected_state)
            self.assertEqual(snapshot.source_key, self.initial.source_key)
            self.assertEqual(snapshot.handoff_id, self.initial.handoff_id)

        with self.assertRaisesRegex(TransitionError, "human review"):
            self.advance(snapshot, HandoffEvent.ACCEPT)
        accepted = self.advance(snapshot, HandoffEvent.ACCEPT, review=self.review)
        self.assertEqual(accepted.state, HandoffState.ACCEPTED)
        self.assertEqual(accepted.review, self.review)
        self.assertEqual(accepted.attempt, 1)
        self.assertEqual(accepted.revision, 4)
        self.assertEqual(snapshot.state, HandoffState.AWAITING_REVIEW)
        for event in HandoffEvent:
            with self.subTest(event=event), self.assertRaises(TransitionError):
                self.advance(
                    accepted,
                    event,
                    review=(
                        self.review
                        if event in (HandoffEvent.ACCEPT, HandoffEvent.REJECT)
                        else None
                    ),
                )

    def test_rejection_is_terminal_and_requires_review(self):
        snapshot = self.advance(self.initial, HandoffEvent.QUEUE)
        snapshot = self.advance(snapshot, HandoffEvent.START)
        snapshot = self.advance(snapshot, HandoffEvent.COMPLETE_PROCESSING)
        with self.assertRaisesRegex(TransitionError, "human review"):
            self.advance(snapshot, HandoffEvent.REJECT)
        rejected = self.advance(snapshot, HandoffEvent.REJECT, review=self.review)
        self.assertEqual(rejected.state, HandoffState.REJECTED)
        with self.assertRaises(TransitionError):
            self.advance(rejected, HandoffEvent.RETRY)

    def test_failure_retry_reuses_identity_and_counts_attempts(self):
        queued = self.advance(self.initial, HandoffEvent.QUEUE)
        processing = self.advance(queued, HandoffEvent.START)
        failed = self.advance(
            processing, HandoffEvent.FAIL, failure_code=FailureCode.PROCESSING_TIMEOUT
        )
        self.assertEqual(failed.state, HandoffState.FAILED)
        self.assertEqual(failed.failure_code, FailureCode.PROCESSING_TIMEOUT)
        retried = self.advance(failed, HandoffEvent.RETRY)
        self.assertEqual(retried.state, HandoffState.QUEUED)
        self.assertEqual(retried.attempt, 2)
        self.assertIsNone(retried.failure_code)
        self.assertEqual(retried.source_key, self.initial.source_key)
        self.assertEqual(retried.handoff_id, self.initial.handoff_id)
        self.assertEqual(queued.attempt, 1)

    def test_stale_transition_and_duplicate_event_are_rejected(self):
        queued = self.advance(self.initial, HandoffEvent.QUEUE)
        with self.assertRaises(StaleTransitionError):
            transition(
                queued,
                HandoffEvent.START,
                expected_state=HandoffState.RECEIVED,
                expected_revision=0,
            )
        with self.assertRaises(StaleTransitionError):
            transition(
                queued,
                HandoffEvent.START,
                expected_state=HandoffState.QUEUED,
                expected_revision=0,
            )
        with self.assertRaises(TransitionError):
            self.advance(queued, HandoffEvent.QUEUE)

    def test_failure_codes_cannot_contain_free_text_and_review_evidence_is_scoped(self):
        with self.assertRaises(TransitionError):
            self.advance(self.initial, HandoffEvent.FAIL, failure_code="document text")
        with self.assertRaises(TransitionError):
            self.advance(self.initial, HandoffEvent.FAIL)
        with self.assertRaises(TransitionError):
            self.advance(self.initial, HandoffEvent.QUEUE, review=self.review)
        with self.assertRaises(TransitionError):
            self.advance(
                self.initial,
                HandoffEvent.QUEUE,
                failure_code=FailureCode.PROCESSING_FAILED,
            )

    def test_invalid_review_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            ReviewDecision("", "synthetic-authorization-check", "decision-1")
        with self.assertRaises(ValueError):
            ReviewDecision("reviewer", "", "decision-1")


if __name__ == "__main__":
    unittest.main()
