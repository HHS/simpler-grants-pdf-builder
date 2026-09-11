import importlib
import json
from datetime import datetime
from types import SimpleNamespace

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.test import TestCase
from django.utils import timezone
from easyaudit.models import CRUDEvent
from freezegun import freeze_time
from users.models import BloomUser

from nofos.metrics import (
    active_users_by_month,
    avg_warnings_by_month,
    import_error_rate_by_month,
    month_boundaries,
    nofos_created_by_month,
    time_to_first_live_pdf_by_month,
    total_users_by_month,
)
from nofos.models import ImportAttempt, MetricsActivity, MetricsActor, MetricsNofo, Nofo


class MetricsHistoryTests(TestCase):
    def setUp(self):
        self.months = month_boundaries(timezone.make_aware(datetime(2026, 9, 1)), 3)
        with freeze_time("2026-09-10 12:00:00"):
            self.user = BloomUser.objects.create_user(
                email="metrics@example.com", password=None, group="cdc"
            )
            self.nofo = Nofo.objects.create(
                title="History", number="CDC-001", opdiv="CDC", group="cdc"
            )
            self.attempt = ImportAttempt.objects.create(
                user=self.user, nofo=self.nofo, warning_count=2
            )
            self.event(self.user)

    def event(self, user=None, mode=None, **overrides):
        values = dict(
            content_type=ContentType.objects.get_for_model(Nofo),
            object_id=str(self.nofo.pk),
            event_type=CRUDEvent.UPDATE,
            user=user,
            changed_fields=(
                json.dumps({"action": "nofo_print", "print_mode": [mode]})
                if mode
                else "{}"
            ),
        )
        values.update(overrides)
        return CRUDEvent.objects.create(**values)

    def snapshot(self):
        return [
            query(self.months)
            for query in (
                total_users_by_month,
                active_users_by_month,
                nofos_created_by_month,
                time_to_first_live_pdf_by_month,
                import_error_rate_by_month,
                avg_warnings_by_month,
            )
        ]

    def test_deletion_preserves_all_six_metrics_and_unlinks_user(self):
        with freeze_time("2026-09-11 12:00:00"):
            self.event(self.user, "live")
        before = self.snapshot()
        actor_id = MetricsActor.objects.get(user=self.user).pk
        self.nofo.delete()
        self.user.delete()
        CRUDEvent.objects.all().delete()
        self.assertEqual(self.snapshot(), before)
        self.assertIsNone(MetricsActor.objects.get(pk=actor_id).user_id)
        self.attempt.refresh_from_db()
        self.assertIsNone(self.attempt.user_id)
        self.assertIsNone(self.attempt.nofo_id)
        self.assertTrue(self.attempt.metrics_included)

    def test_group_changes_only_affect_future_activity_and_imports(self):
        before = self.snapshot()
        self.user.group = "bloom"
        self.user.save()
        self.nofo.group = "staging"
        self.nofo.save()
        with freeze_time("2026-10-10"):
            self.event(self.user)
            ImportAttempt.objects.create(user=self.user, warning_count=100)
        self.assertEqual(self.snapshot(), before)
        self.user.group = "cdc"
        self.user.save()
        with freeze_time("2026-11-10"):
            self.event(self.user)
            ImportAttempt.objects.create(user=self.user, warning_count=4)
        self.assertEqual(active_users_by_month(self.months), [1, 0, 1])
        self.assertEqual(avg_warnings_by_month(self.months), [2.0, None, 4.0])

    def test_excluded_signup_and_attempt_remain_excluded_after_move_and_deletion(self):
        with freeze_time("2026-09-12"):
            user = BloomUser.objects.create_user(
                email="internal@example.com", password=None, group="bloom"
            )
            attempt = ImportAttempt.objects.create(
                user=user, error_code="IMPORT-UNEXPECTED"
            )
            self.event(user)
            user.group = "cdc"
            user.save()
            self.event(user)
            user.delete()
        self.assertEqual(total_users_by_month(self.months), [1, 1, 1])
        self.assertEqual(active_users_by_month(self.months), [2, 0, 0])
        self.assertEqual(import_error_rate_by_month(self.months), [0.0, None, None])
        attempt.refresh_from_db()
        self.assertFalse(attempt.metrics_included)

    def test_later_first_pdf_updates_creation_cohort_once(self):
        with freeze_time("2026-09-11 12:00:00"):
            self.event(self.user, "test")
        self.assertEqual(
            time_to_first_live_pdf_by_month(self.months), [None, None, None]
        )
        with freeze_time("2026-10-10 12:00:00"):
            self.event(self.user, "live")
        self.assertEqual(
            time_to_first_live_pdf_by_month(self.months), [720.0, None, None]
        )
        with freeze_time("2026-11-10"):
            self.event(self.user, "live")
        self.nofo.delete()
        self.assertEqual(
            time_to_first_live_pdf_by_month(self.months), [720.0, None, None]
        )

    def test_out_of_order_and_malformed_print_events(self):
        with freeze_time(self.months[1][0]):
            self.event(mode="live")
        earlier = self.months[0][0].replace(day=12)
        with freeze_time(earlier):
            self.event(mode="live")
        for payload in (
            "null",
            "[]",
            "bad-json",
            '{"action":"nofo_print","print_mode":null}',
        ):
            self.event(changed_fields=payload)
        self.event(mode="live", object_id="legacy-integer")
        self.assertEqual(
            MetricsNofo.objects.get(pk=self.nofo.pk).first_live_at, earlier
        )

    def test_unknown_import_eligibility_is_not_assumed_external(self):
        with freeze_time("2026-10-01"):
            ImportAttempt.objects.create(error_code="IMPORT-UNEXPECTED")
        self.assertEqual(import_error_rate_by_month(self.months), [0.0, None, None])

    def test_facts_roll_back_with_transaction(self):
        before = self.snapshot()
        with self.assertRaises(RuntimeError), transaction.atomic():
            with freeze_time("2026-10-10"):
                self.event(self.user, "live")
                ImportAttempt.objects.create(user=self.user)
                raise RuntimeError("rollback")
        self.assertEqual(self.snapshot(), before)

    def test_metric_models_are_not_duplicated_in_audit(self):
        self.assertFalse(
            CRUDEvent.objects.filter(
                content_type__model__in=[
                    "metricsactor",
                    "metricsnofo",
                    "metricsactivity",
                ]
            ).exists()
        )

    def test_baseline_freezes_surviving_records_and_is_idempotent(self):
        with freeze_time("2026-10-10 12:00:00"):
            self.event(self.user, "live")
        MetricsActivity.objects.all().delete()
        MetricsActor.objects.all().delete()
        MetricsNofo.objects.all().delete()
        ImportAttempt.objects.update(metrics_included=None)
        baseline = importlib.import_module(
            "nofos.migrations.0137_metrics_history_baseline"
        ).baseline
        editor = SimpleNamespace(connection=SimpleNamespace(alias="default"))
        baseline(apps, editor)
        before = self.snapshot()
        baseline(apps, editor)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(total_users_by_month(self.months), [1, 1, 1])
        self.assertEqual(
            time_to_first_live_pdf_by_month(self.months), [720.0, None, None]
        )
        self.user.delete()
        self.nofo.delete()
        self.assertEqual(self.snapshot(), before)


class MetricsExplanationTests(TestCase):
    def test_authorized_page_explains_preservation_and_limits(self):
        from django.contrib.auth.models import Permission
        from django.urls import reverse

        user = BloomUser.objects.create_user(
            email="viewer@example.com",
            password=None,
            group="cdc",
            force_password_reset=False,
        )
        user.user_permissions.add(
            Permission.objects.get(codename="view_builder_metrics")
        )
        self.client.force_login(user)
        response = self.client.get(reverse("nofos:builder_metrics"))
        self.assertContains(
            response,
            '<summary class="text-bold">How historical metrics are preserved</summary>',
            html=True,
        )
        self.assertContains(response, "Previously deleted records")
        self.assertContains(response, "unknown user eligibility")


class MetricsImportCreationTests(TestCase):
    def test_import_records_final_group_at_creation(self):
        from unittest.mock import patch

        from nofos.nofo import create_nofo

        with patch("nofos.nofo._build_document", side_effect=lambda nofo, *args: nofo):
            nofo = create_nofo("Imported", [], "CDC", group="cdc")
        self.assertTrue(MetricsNofo.objects.get(pk=nofo.pk).included)

    def test_failed_creation_does_not_leave_a_metric_fact(self):
        from unittest.mock import patch

        from django.core.exceptions import ValidationError

        from nofos.nofo import create_nofo

        with patch(
            "nofos.nofo._build_document", side_effect=ValidationError("invalid")
        ):
            with self.assertRaises(ValidationError):
                create_nofo("Failed", [], "CDC", group="cdc")
        self.assertFalse(MetricsNofo.objects.exists())
        self.assertFalse(Nofo.objects.exists())
