from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from nofos.models import ExternalSourceHandoff, Nofo
from nofos.word_handoff_identity import (
    TrustedHandoffPrincipal,
    link_handoff_to_nofo,
    record_handoff,
)


class WordHandoffIdentityTests(TestCase):
    def setUp(self):
        self.hrsa = TrustedHandoffPrincipal("synthetic-source", "hrsa")

    def test_exact_retry_reuses_receipt_without_changing_metadata(self):
        first, created = record_handoff(
            principal=self.hrsa, source_record_id="comp-1", source_version="v02"
        )
        self.assertTrue(created)
        second, created = record_handoff(
            principal=self.hrsa, source_record_id="comp-1", source_version="v02"
        )
        self.assertFalse(created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.received_at, second.received_at)
        self.assertEqual(ExternalSourceHandoff.objects.count(), 1)

    def test_versions_are_opaque_and_distinct_not_ordered_or_superseded(self):
        receipts = [
            record_handoff(
                principal=self.hrsa,
                source_record_id="comp-1",
                source_version=version,
            )[0]
            for version in ("12", "2", "draft-A")
        ]
        self.assertEqual(len({receipt.pk for receipt in receipts}), 3)
        self.assertTrue(all(receipt.state == "received" for receipt in receipts))

    def test_database_enforces_exact_identity_tuple(self):
        record_handoff(
            principal=self.hrsa, source_record_id="comp-1", source_version="v1"
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            ExternalSourceHandoff.objects.create(
                source_system="synthetic-source",
                source_record_id="comp-1",
                source_version="v1",
                group="hrsa",
            )
        self.assertEqual(ExternalSourceHandoff.objects.count(), 1)

    def test_same_identity_cannot_be_replayed_into_another_scope(self):
        record_handoff(
            principal=self.hrsa, source_record_id="comp-1", source_version="v1"
        )
        with self.assertRaises(PermissionDenied):
            record_handoff(
                principal=TrustedHandoffPrincipal("synthetic-source", "acl"),
                source_record_id="comp-1",
                source_version="v1",
            )

    def test_principal_must_have_an_opdiv_scope(self):
        for group in ("bloom", "staging", "unknown"):
            with self.subTest(group=group), self.assertRaises(PermissionDenied):
                record_handoff(
                    principal=TrustedHandoffPrincipal("synthetic-source", group),
                    source_record_id="comp-1",
                    source_version="v1",
                )
        self.assertEqual(ExternalSourceHandoff.objects.count(), 0)

    def test_missing_or_oversize_opaque_identity_rejected(self):
        for value in ("", "  ", "x" * 256):
            with self.subTest(value=value[:8]), self.assertRaises(ValidationError):
                record_handoff(
                    principal=self.hrsa,
                    source_record_id=value,
                    source_version="v1",
                )

    def test_nofo_link_is_scope_matched_and_immutable(self):
        receipt, _ = record_handoff(
            principal=self.hrsa, source_record_id="comp-1", source_version="v1"
        )
        hrsa_nofo = Nofo.objects.create(title="Synthetic", opdiv="HRSA", group="hrsa")
        other_hrsa_nofo = Nofo.objects.create(
            title="Synthetic 2", opdiv="HRSA", group="hrsa"
        )
        acl_nofo = Nofo.objects.create(title="Synthetic ACL", opdiv="ACL", group="acl")

        with self.assertRaises(PermissionDenied):
            link_handoff_to_nofo(
                principal=self.hrsa, handoff_id=receipt.pk, nofo_id=acl_nofo.pk
            )
        linked = link_handoff_to_nofo(
            principal=self.hrsa, handoff_id=receipt.pk, nofo_id=hrsa_nofo.pk
        )
        self.assertEqual(linked.nofo_id, hrsa_nofo.pk)
        self.assertEqual(
            link_handoff_to_nofo(
                principal=self.hrsa, handoff_id=receipt.pk, nofo_id=hrsa_nofo.pk
            ).nofo_id,
            hrsa_nofo.pk,
        )
        with self.assertRaises(ValidationError):
            link_handoff_to_nofo(
                principal=self.hrsa,
                handoff_id=receipt.pk,
                nofo_id=other_hrsa_nofo.pk,
            )
        receipt.refresh_from_db()
        self.assertEqual(receipt.nofo_id, hrsa_nofo.pk)
        self.assertEqual(receipt.linked_nofo_uuid, hrsa_nofo.pk)

        hrsa_nofo_id = hrsa_nofo.pk
        hrsa_nofo.delete()
        receipt.refresh_from_db()
        self.assertIsNone(receipt.nofo_id)
        self.assertEqual(receipt.linked_nofo_uuid, hrsa_nofo_id)
        with self.assertRaises(ValidationError):
            link_handoff_to_nofo(
                principal=self.hrsa,
                handoff_id=receipt.pk,
                nofo_id=other_hrsa_nofo.pk,
            )

    def test_different_source_cannot_link_receipt(self):
        receipt, _ = record_handoff(
            principal=self.hrsa, source_record_id="comp-1", source_version="v1"
        )
        nofo = Nofo.objects.create(title="Synthetic", opdiv="HRSA", group="hrsa")
        with self.assertRaises(PermissionDenied):
            link_handoff_to_nofo(
                principal=TrustedHandoffPrincipal("other-source", "hrsa"),
                handoff_id=receipt.pk,
                nofo_id=nofo.pk,
            )
