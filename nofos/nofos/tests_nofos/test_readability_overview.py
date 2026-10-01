from datetime import timedelta
from unittest.mock import patch

from constance.test import override_config
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from users.models import BloomUser

from nofos.models import Nofo, NofoReadabilityCheckpoint, NofoReadabilityScore
from nofos.readability import INPUT_CONTRACT_VERSION, PROFILE_REFERENCE
from nofos.readability_overview import readability_overview_page


@override_config(HHS_NOFO_METRICS_ENABLED=True)
class ReadabilityOverviewTests(TestCase):
    def setUp(self):
        self.viewer = BloomUser.objects.create_user(
            email="metrics-viewer@example.com",
            password="testpass123",
            group="hrsa",
            force_password_reset=False,
        )
        self.viewer.user_permissions.add(
            Permission.objects.get(codename="view_builder_metrics")
        )
        self.client.force_login(self.viewer)
        self.nofo = Nofo.objects.create(
            title="Synthetic CDC NOFO",
            short_name="cdc-test",
            number="TEST-CDC-001",
            opdiv="CDC",
            group="cdc",
        )

    def checkpoint(self, nofo=None, value=100, complete=True, saved=True, offset=0):
        nofo = nofo or self.nofo
        score = NofoReadabilityScore.objects.create(
            nofo=nofo,
            nofo_revision=nofo.updated + timedelta(seconds=offset),
            profile_reference=PROFILE_REFERENCE,
            package_version="test-package",
            input_contract_version=INPUT_CONTRACT_VERSION,
            is_complete=complete,
            result={
                "metrics": {
                    "word_count": {
                        "status": "calculated" if complete else "unavailable",
                        "value": value if complete else None,
                    }
                }
            },
        )
        if not saved:
            return score
        return NofoReadabilityCheckpoint.objects.create(
            score=score, saved_by=self.viewer, nofo_status_at_save="review"
        )

    def url(self):
        return reverse("nofos:builder_metrics_readability_scores")

    def test_latest_two_not_latest_complete_and_unsaved_not_included(self):
        self.checkpoint(value=120, offset=0)
        self.checkpoint(value=100, offset=1)
        self.checkpoint(value=1, saved=False, offset=2)
        page, rows = readability_overview_page(None)
        self.assertEqual(page.paginator.count, 1)
        self.assertEqual(rows[0]["count"], 2)
        self.assertEqual(rows[0]["latest"]["metrics"][0]["value"], 100)
        self.assertEqual(rows[0]["latest"]["change_summary"]["improved"], 1)
        self.checkpoint(complete=False, offset=3)
        _page, rows = readability_overview_page(None)
        self.assertEqual(rows[0]["count"], 3)
        self.assertFalse(rows[0]["latest"]["is_complete"])
        self.assertEqual(rows[0]["latest"]["metrics"][0]["display"], "Unavailable")

    def test_permissions_and_private_response(self):
        self.checkpoint()
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertContains(response, "Synthetic CDC NOFO")
        self.assertContains(
            response, reverse("nofos:nofo_readability_history", args=[self.nofo.pk])
        )
        self.viewer.user_permissions.clear()
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        admin = BloomUser.objects.create_superuser(
            email="overview-admin@example.com",
            password="testpass123",
            force_password_reset=False,
        )
        self.client.force_login(admin)
        self.assertEqual(self.client.get(self.url()).status_code, 200)
        self.client.logout()
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login", response["Location"])

    @override_config(HHS_NOFO_METRICS_ENABLED=False)
    def test_disabled_returns_404_and_retains_records(self):
        self.checkpoint()
        self.assertEqual(self.client.get(self.url()).status_code, 404)
        self.assertEqual(NofoReadabilityCheckpoint.objects.count(), 1)

    def test_archived_and_empty_states(self):
        self.assertContains(
            self.client.get(self.url()), "No saved readability results yet."
        )
        self.checkpoint()
        Nofo.objects.filter(pk=self.nofo.pk).update(archived=timezone.now().date())
        response = self.client.get(self.url())
        self.assertContains(response, "Archived")
        self.assertContains(response, "Synthetic CDC NOFO")

    @patch(
        "nofos.readability_history.get_metrics_package_version",
        return_value="test-package",
    )
    def test_pagination_and_bounded_projected_queries(self, _version):
        for index in range(51):
            nofo = Nofo.objects.create(
                title=f"Synthetic {index}",
                number=f"TEST-{index}",
                opdiv="CDC",
                group="cdc",
            )
            for offset in range(3):
                self.checkpoint(nofo, value=100 - offset, offset=offset)
        with CaptureQueriesContext(connection) as queries:
            page, rows = readability_overview_page(1)
        self.assertEqual(len(rows), 50)
        self.assertEqual(page.paginator.count, 51)
        self.assertEqual(len(queries), 3)
        projection_sql = queries[-1]["sql"]
        self.assertIn("ROW_NUMBER()", projection_sql)
        self.assertNotIn('"result" FROM', projection_sql)
        second, rows = readability_overview_page(2)
        self.assertEqual(len(rows), 1)
        self.assertEqual(second.number, 2)
        self.assertEqual(rows[0]["count"], 3)
