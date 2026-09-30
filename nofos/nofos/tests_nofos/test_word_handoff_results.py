from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, connections, transaction
from django.test import TestCase, TransactionTestCase

from nofos.models import (
    ExternalSourceHandoff,
    ExternalSourceHandoffCurrent,
    ExternalSourceHandoffResult,
    Nofo,
)
from nofos.word_handoff_identity import (
    TrustedHandoffPrincipal,
    link_handoff_to_nofo,
    record_handoff,
    replace_handoff_result,
)
from nofos.word_handoff_lifecycle import ReviewDecision

PRINCIPAL = TrustedHandoffPrincipal("synthetic-source", "hrsa")
REVIEW = ReviewDecision(
    "synthetic-reviewer", "synthetic-authorization", "synthetic-decision"
)


def new_nofo(title):
    return Nofo.objects.create(title=title, opdiv="HRSA", group="hrsa")


class HandoffResultTests(TestCase):
    def setUp(self):
        self.receipt, _ = record_handoff(
            principal=PRINCIPAL, source_record_id="comp-1", source_version="v1"
        )
        self.nofos = [new_nofo(f"Synthetic {n}") for n in range(3)]
        self.first = link_handoff_to_nofo(
            principal=PRINCIPAL, handoff_id=self.receipt.pk, nofo_id=self.nofos[0].pk
        )

    def replace(self, nofo, expected=None, review=REVIEW):
        return replace_handoff_result(
            principal=PRINCIPAL,
            handoff_id=self.receipt.pk,
            nofo_id=nofo.pk,
            expected_current_result_id=self.first.pk if expected is None else expected,
            review=review,
        )

    def test_authorized_replacement_is_current_and_prior_is_traceable(self):
        second = self.replace(self.nofos[1])
        self.assertEqual(second.supersedes_id, self.first.pk)
        self.assertEqual(second.reviewer_id, REVIEW.reviewer_id)
        self.assertEqual(ExternalSourceHandoffResult.objects.count(), 2)
        self.assertEqual(
            ExternalSourceHandoffCurrent.objects.get(handoff=self.receipt).result_id,
            second.pk,
        )
        first_uuid, second_uuid = self.nofos[0].pk, self.nofos[1].pk
        self.nofos[0].delete()
        self.nofos[1].delete()
        self.first.refresh_from_db()
        second.refresh_from_db()
        self.assertIsNone(self.first.nofo_id)
        self.assertIsNone(second.nofo_id)
        self.assertEqual(self.first.linked_nofo_uuid, first_uuid)
        self.assertEqual(second.linked_nofo_uuid, second_uuid)
        self.assertEqual(
            ExternalSourceHandoffCurrent.objects.get(handoff=self.receipt).result_id,
            second.pk,
        )

    def test_stale_or_unauthorized_replacement_rolls_back(self):
        with self.assertRaises(ValidationError):
            self.replace(self.nofos[1], expected=self.nofos[2].pk)
        with self.assertRaises(PermissionDenied):
            self.replace(self.nofos[1], review=None)
        self.assertEqual(ExternalSourceHandoffResult.objects.count(), 1)
        self.assertEqual(
            ExternalSourceHandoffCurrent.objects.get(handoff=self.receipt).result_id,
            self.first.pk,
        )
        with patch(
            "nofos.word_handoff_identity.models.QuerySet.update", return_value=0
        ):
            with self.assertRaises(ValidationError):
                self.replace(self.nofos[1])
        self.assertEqual(ExternalSourceHandoffResult.objects.count(), 1)
        self.assertEqual(
            ExternalSourceHandoffCurrent.objects.get(handoff=self.receipt).result_id,
            self.first.pk,
        )

    def test_relink_and_result_mutation_are_rejected(self):
        with self.assertRaises(ValidationError):
            link_handoff_to_nofo(
                principal=PRINCIPAL,
                handoff_id=self.receipt.pk,
                nofo_id=self.nofos[1].pk,
            )
        self.first.nofo = self.nofos[1]
        with self.assertRaises(ValidationError):
            self.first.save()
        self.first.pk = self.nofos[2].pk
        with self.assertRaises(ValidationError):
            self.first.save()
        with self.assertRaises(ValidationError):
            ExternalSourceHandoffResult.objects.filter(handoff=self.receipt).update(
                nofo=self.nofos[1]
            )
        with self.assertRaises(ValidationError):
            ExternalSourceHandoffResult.objects.filter(handoff=self.receipt).delete()
        with self.assertRaises(IntegrityError), transaction.atomic():
            ExternalSourceHandoffResult.objects.create(
                handoff=self.receipt,
                nofo=self.nofos[0],
                linked_nofo_uuid=self.nofos[0].pk,
            )
        with self.assertRaises(ValidationError):
            ExternalSourceHandoffResult.objects.create(
                handoff=self.receipt,
                nofo=self.nofos[1],
                linked_nofo_uuid=self.nofos[1].pk,
                supersedes=self.first,
            )
        with self.assertRaises(ValidationError):
            ExternalSourceHandoffCurrent.objects.get(handoff=self.receipt).save()
        with self.assertRaises(ValidationError):
            ExternalSourceHandoffCurrent.objects.filter(handoff=self.receipt).update(
                result=self.first
            )
        with self.assertRaises(ValidationError):
            ExternalSourceHandoffCurrent(handoff=self.receipt, result=self.first).save()
        cloned_result = ExternalSourceHandoffResult(
            id=ExternalSourceHandoffCurrent.objects.get(handoff=self.receipt).result_id,
            handoff=self.receipt,
            nofo=self.nofos[1],
            linked_nofo_uuid=self.nofos[1].pk,
        )
        with self.assertRaises(ValidationError):
            cloned_result.save()
        with self.assertRaises(ValidationError):
            ExternalSourceHandoffResult.objects.bulk_create(
                [cloned_result], update_conflicts=True
            )
        wrong_group = Nofo.objects.create(title="Wrong group", opdiv="ACL", group="acl")
        with self.assertRaises(ValidationError):
            ExternalSourceHandoffResult.objects.create(
                handoff=self.receipt, nofo=wrong_group, linked_nofo_uuid=wrong_group.pk
            )

    def test_receipt_identity_is_immutable(self):
        self.receipt.source_version = "different"
        with self.assertRaises(ValidationError):
            self.receipt.save()
        self.receipt.refresh_from_db()
        self.receipt.state = "processing"
        with self.assertRaises(ValidationError):
            self.receipt.save()
        self.receipt.refresh_from_db()
        self.receipt.state_changed_at = self.receipt.state_changed_at.replace(year=2001)
        with self.assertRaises(ValidationError):
            self.receipt.save()
        with self.assertRaises(ValidationError):
            ExternalSourceHandoff.objects.filter(pk=self.receipt.pk).update(group="acl")
        with self.assertRaises(ValidationError):
            ExternalSourceHandoff.objects.filter(pk=self.receipt.pk).update(
                pk=self.nofos[0].pk
            )
        with self.assertRaises(ValidationError):
            ExternalSourceHandoff.objects.bulk_create(
                [self.receipt], update_conflicts=True
            )
        clone = ExternalSourceHandoff(
            id=self.receipt.pk,
            source_system="other",
            source_record_id="other",
            source_version="other",
            group="hrsa",
        )
        with self.assertRaises(ValidationError):
            clone.save()

    def test_same_nofo_can_be_linked_from_a_separate_source_receipt(self):
        other, _ = record_handoff(
            principal=PRINCIPAL, source_record_id="comp-2", source_version="v1"
        )
        other_result = link_handoff_to_nofo(
            principal=PRINCIPAL, handoff_id=other.pk, nofo_id=self.nofos[0].pk
        )
        self.assertNotEqual(other_result.pk, self.first.pk)
        self.assertEqual(other_result.linked_nofo_uuid, self.first.linked_nofo_uuid)
        self.assertEqual(
            ExternalSourceHandoffCurrent.objects.get(handoff=other).result_id,
            other_result.pk,
        )


class HandoffResultPostgresRaceTests(TransactionTestCase):
    def test_two_replacements_with_same_expected_current_are_serialized(self):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL row-lock behavior only")
        receipt, _ = record_handoff(
            principal=PRINCIPAL, source_record_id="race", source_version="v1"
        )
        nofos = [new_nofo(f"Race {n}") for n in range(3)]
        first = link_handoff_to_nofo(
            principal=PRINCIPAL, handoff_id=receipt.pk, nofo_id=nofos[0].pk
        )
        barrier = Barrier(2)

        def attempt(nofo_id):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return replace_handoff_result(
                    principal=PRINCIPAL,
                    handoff_id=receipt.pk,
                    nofo_id=nofo_id,
                    expected_current_result_id=first.pk,
                    review=REVIEW,
                ).pk
            except ValidationError:
                return None
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(attempt, nofo.pk) for nofo in nofos[1:]]
            outcomes = [future.result(timeout=20) for future in futures]
        self.assertEqual(sum(value is not None for value in outcomes), 1)
        self.assertEqual(ExternalSourceHandoffResult.objects.count(), 2)
        self.assertIn(
            ExternalSourceHandoffCurrent.objects.get(handoff=receipt).result_id,
            outcomes,
        )
