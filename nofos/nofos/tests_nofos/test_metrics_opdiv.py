import importlib
import json
from datetime import datetime
from types import SimpleNamespace

from django.apps import apps
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from easyaudit.models import CRUDEvent
from freezegun import freeze_time
from users.models import BloomUser

from nofos import metrics
from nofos.models import ImportAttempt, MetricsActivity, MetricsActor, MetricsNofo, Nofo


@freeze_time("2026-09-20 12:00:00")
class MetricsOpdivTests(TestCase):
    def setUp(self):
        self.months = metrics.month_boundaries(
            timezone.make_aware(datetime(2026, 9, 1)), 2
        )
        self.users = {}
        self.nofos = {}
        for group, hours, warnings in [
            ("cdc", 24, 2),
            ("nih", 72, 8),
            ("bloom", 1, 99),
            ("staging", 1, 99),
        ]:
            with freeze_time("2026-09-10 12:00:00"):
                user = BloomUser.objects.create_user(
                    email=f"{group}@example.com",
                    password=None,
                    group=group,
                    force_password_reset=False,
                )
                nofo = Nofo.objects.create(
                    title=group, number=group, opdiv=group.upper(), group=group
                )
                ImportAttempt.objects.create(
                    user=user, nofo=nofo, warning_count=warnings
                )
                self.activity(user, nofo)
                self.activity(user, nofo)
                if group == "cdc":
                    ImportAttempt.objects.create(
                        user=user, error_code="IMPORT-UNEXPECTED", is_reimport=True
                    )
            with freeze_time(
                timezone.make_aware(datetime(2026, 9, 10, 12))
                + timezone.timedelta(hours=hours)
            ):
                self.activity(user, nofo, live=True)
            self.users[group], self.nofos[group] = user, nofo
        self.viewer = self.users["cdc"]
        self.url = reverse("nofos:builder_metrics")

    def activity(self, user, nofo, live=False):
        CRUDEvent.objects.create(
            content_type=ContentType.objects.get_for_model(Nofo),
            object_id=str(nofo.pk),
            user=user,
            event_type=CRUDEvent.UPDATE,
            changed_fields=(
                json.dumps({"action": "nofo_print", "print_mode": ["live"]})
                if live
                else "{}"
            ),
        )

    def values(self, group):
        return [
            query(self.months, group)
            for query in [
                metrics.total_users_by_month,
                metrics.active_users_by_month,
                metrics.nofos_created_by_month,
                metrics.time_to_first_live_pdf_by_month,
                metrics.import_error_rate_by_month,
                metrics.avg_warnings_by_month,
            ]
        ]

    def authorize(self):
        self.viewer.user_permissions.add(
            Permission.objects.get(codename="view_builder_metrics")
        )
        self.client.force_login(self.viewer)

    def test_all_six_metrics_filter_and_recompute_denominators(self):
        self.assertEqual(
            self.values("cdc"),
            [[1, 1], [1, 0], [1, 0], [24.0, None], [50.0, None], [2.0, None]],
        )
        self.assertEqual(
            self.values("nih"),
            [[1, 1], [1, 0], [1, 0], [72.0, None], [0.0, None], [8.0, None]],
        )
        self.assertEqual(
            self.values("all"),
            [[2, 2], [2, 0], [2, 0], [48.0, None], [33.3, None], [5.0, None]],
        )
        self.assertEqual(
            self.values("acf"),
            [[0, 0], [0, 0], [0, 0], [None, None], [None, None], [None, None]],
        )

    def test_deleting_users_and_nofos_preserves_filtered_values(self):
        before = self.values("cdc")
        self.nofos["cdc"].delete()
        self.users["cdc"].delete()
        CRUDEvent.objects.all().delete()
        self.assertEqual(self.values("cdc"), before)

    def test_all_active_users_are_distinct_even_with_multiple_group_facts(self):
        actor = MetricsActor.objects.get(user=self.viewer)
        MetricsActivity.objects.create(
            actor=actor, month=self.months[0][0].date(), group="nih"
        )
        self.assertEqual(metrics.active_users_by_month(self.months), [2, 0])
        self.assertEqual(metrics.active_users_by_month(self.months, "nih"), [2, 0])

    def test_missing_group_stays_in_all_and_is_not_assigned_to_an_agency(self):
        MetricsActor.objects.filter(user=self.viewer).update(group="")
        self.assertEqual(metrics.total_users_by_month(self.months), [2, 2])
        self.assertEqual(metrics.total_users_by_month(self.months, "cdc"), [0, 0])

    def test_html_and_json_require_metrics_permission(self):
        self.client.force_login(self.viewer)
        for accept in ["text/html", "application/json"]:
            self.assertEqual(
                self.client.get(self.url, HTTP_ACCEPT=accept).status_code, 403
            )
        self.authorize()
        response = self.client.get(
            self.url, {"group": "cdc"}, HTTP_ACCEPT="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["groupLabel"], "CDC")
        self.assertEqual(response.json()["errorRatePct"], [50.0])
        self.assertEqual(response["Cache-Control"], "private, no-store")
        html = self.client.get(self.url, {"group": "cdc"})
        self.assertContains(html, "OpDiv group")
        self.assertContains(html, 'value="cdc" selected')
        self.assertNotContains(html, 'value="bloom"')
        self.assertNotContains(html, 'value="staging"')
        self.assertEqual(
            self.client.get(self.url, HTTP_ACCEPT="application/json").json()["group"],
            "all",
        )

    def test_invalid_or_internal_group_rejected_for_both_formats(self):
        self.authorize()
        for group in ["bloom", "staging", "bad", "", "<script>"]:
            for accept in ["text/html", "application/json"]:
                self.assertEqual(
                    self.client.get(
                        self.url, {"group": group}, HTTP_ACCEPT=accept
                    ).status_code,
                    400,
                )

    def test_baseline_recovers_surviving_groups_only_and_is_repeatable(self):
        self.users["nih"].delete()
        self.nofos["nih"].delete()
        MetricsActor.objects.update(group="")
        MetricsActivity.objects.update(group="")
        MetricsNofo.objects.update(group="")
        ImportAttempt.objects.update(metrics_group="")
        baseline = importlib.import_module(
            "nofos.migrations.0139_metrics_opdiv_baseline"
        ).baseline
        editor = SimpleNamespace(connection=SimpleNamespace(alias="default"))
        baseline(apps, editor)
        before = self.values("cdc")
        baseline(apps, editor)
        self.assertEqual(self.values("cdc"), before)
        self.assertEqual(
            before, [[1, 1], [1, 0], [1, 0], [24.0, None], [50.0, None], [2.0, None]]
        )
        self.assertEqual(metrics.total_users_by_month(self.months, "nih"), [0, 0])
        self.assertEqual(metrics.total_users_by_month(self.months), [2, 2])
