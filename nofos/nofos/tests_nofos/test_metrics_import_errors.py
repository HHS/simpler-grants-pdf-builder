"""
The import-errors drill-down behind the "Blocking import errors" chart (#912).

The thing worth protecting here is that the drill-down and the chart never
disagree: same attempts, same window, same exclusions. A page that quietly
counts different rows than the chart it hangs off is worse than no page.
"""

from datetime import datetime

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time
from users.models import BloomUser

from nofos import metrics
from nofos.models import ImportAttempt, Nofo


@freeze_time("2026-09-20 12:00:00")
class ImportErrorDrilldownTestCase(TestCase):
    def setUp(self):
        self.months = metrics.month_boundaries(
            timezone.make_aware(datetime(2026, 9, 1)), 2
        )
        self.url = reverse("nofos:builder_metrics_import_errors")

        with freeze_time("2026-09-10 12:00:00"):
            self.cdc_user = self.make_user("cdc")
            self.nih_user = self.make_user("nih")
            self.bloom_user = self.make_user("bloom")

            self.cdc_nofo = Nofo.objects.create(
                title="CDC NOFO", number="CDC-1", opdiv="CDC", group="cdc"
            )

            # Two of one code, one of another, so ordering by frequency is
            # actually exercised rather than coincidental.
            self.record_failure(self.cdc_user, "IMPORT-OPDIV-BLANK", "a.docx")
            self.record_failure(self.cdc_user, "IMPORT-OPDIV-BLANK", "b.docx")
            self.record_failure(
                self.nih_user, "IMPORT-NO-SECTIONS", "c.docx", nofo=None
            )
            # A success, to prove the tables count failures only.
            ImportAttempt.objects.create(user=self.cdc_user, filename="ok.docx")
            # Internal accounts stay out, exactly as in metrics.py.
            self.record_failure(self.bloom_user, "IMPORT-UNEXPECTED", "internal.docx")

    def make_user(self, group):
        return BloomUser.objects.create_user(
            email=f"{group}@example.com",
            password=None,
            group=group,
            force_password_reset=False,
        )

    def record_failure(self, user, error_code, filename, nofo=None):
        """Not named `fail` - that is unittest's own, and shadowing it breaks asserts."""
        return ImportAttempt.objects.create(
            user=user, error_code=error_code, filename=filename, nofo=nofo
        )

    def authorize(self, user=None):
        viewer = user or self.cdc_user
        viewer.user_permissions.add(
            Permission.objects.get(codename="view_builder_metrics")
        )
        self.client.force_login(viewer)
        return viewer


class ImportErrorQueryTests(ImportErrorDrilldownTestCase):
    def test_groups_by_code_most_frequent_first(self):
        rows = metrics.import_errors_by_code(self.months)

        self.assertEqual(
            [(row["code"], row["attempts"], row["share_pct"]) for row in rows],
            [("IMPORT-OPDIV-BLANK", 2, 66.7), ("IMPORT-NO-SECTIONS", 1, 33.3)],
        )

    def test_excludes_internal_accounts_like_the_chart(self):
        codes = {row["code"] for row in metrics.import_errors_by_code(self.months)}

        self.assertNotIn("IMPORT-UNEXPECTED", codes)

    def test_totals_reconcile_with_the_error_rate_chart(self):
        rows = metrics.import_errors_by_code(self.months)
        failures = sum(row["attempts"] for row in rows)
        attempts = metrics.eligible_import_attempts(self.months).count()

        # The chart's first month carries every attempt in this fixture.
        self.assertEqual(
            metrics.import_error_rate_by_month(self.months)[0],
            round(100 * failures / attempts, 1),
        )

    def test_filters_by_opdiv(self):
        self.assertEqual(
            [row["code"] for row in metrics.import_errors_by_code(self.months, "nih")],
            ["IMPORT-NO-SECTIONS"],
        )
        self.assertEqual(
            [row["code"] for row in metrics.import_errors_by_code(self.months, "cdc")],
            ["IMPORT-OPDIV-BLANK"],
        )

    def test_share_is_of_failures_within_the_selected_opdiv(self):
        rows = metrics.import_errors_by_code(self.months, "cdc")

        self.assertEqual(rows[0]["share_pct"], 100.0)

    def test_no_failures_returns_no_rows(self):
        self.assertEqual(metrics.import_errors_by_code(self.months, "acf"), [])

    def test_recent_errors_are_newest_first_and_failures_only(self):
        with freeze_time("2026-09-15 12:00:00"):
            self.record_failure(self.cdc_user, "IMPORT-FILE-TYPE", "newest.pdf")

        attempts = metrics.recent_import_errors(self.months)

        self.assertEqual(attempts[0].filename, "newest.pdf")
        self.assertNotIn("ok.docx", [attempt.filename for attempt in attempts])
        self.assertNotIn("internal.docx", [attempt.filename for attempt in attempts])


class ImportErrorPageTests(ImportErrorDrilldownTestCase):
    def test_requires_the_metrics_permission(self):
        self.client.force_login(self.cdc_user)

        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_authorized_viewer_sees_the_summary_table(self):
        self.authorize()

        content = self.client.get(self.url).content.decode("utf-8")

        self.assertIn("IMPORT-OPDIV-BLANK", content)
        self.assertIn("IMPORT-NO-SECTIONS", content)
        self.assertIn("66.7%", content)

    def test_codes_carry_their_plain_language_meaning(self):
        self.authorize()

        content = self.client.get(self.url).content.decode("utf-8")

        # Read from the error catalog rather than a second copy of the copy.
        self.assertIn("We couldn’t read the Opdiv from this document", content)

    def test_uncatalogued_code_says_so_rather_than_showing_a_blank_cell(self):
        self.authorize()
        with freeze_time("2026-09-12 12:00:00"):
            self.record_failure(self.cdc_user, "IMPORT-RETIRED-CODE", "old.docx")

        content = self.client.get(self.url).content.decode("utf-8")

        self.assertIn("Not in the error catalog", content)

    def test_back_link_returns_to_the_metrics_page(self):
        self.authorize()

        content = self.client.get(self.url).content.decode("utf-8")

        self.assertIn(f'href="{reverse("nofos:builder_metrics")}"', content)
        self.assertIn("Back to usage &amp; quality metrics", content)

    def test_recent_attempts_show_the_detail_needed_to_chase_one_down(self):
        self.authorize()

        content = self.client.get(self.url).content.decode("utf-8")

        self.assertIn("a.docx", content)
        self.assertIn("New import", content)
        self.assertIn("CDC", content)

    def test_nofo_is_linked_only_when_the_viewer_could_open_it(self):
        self.authorize()
        with freeze_time("2026-09-12 12:00:00"):
            self.record_failure(
                self.cdc_user, "REIMPORT-DOCUMENT-INVALID", "d.docx", nofo=self.cdc_nofo
            )

        content = self.client.get(self.url).content.decode("utf-8")
        self.assertIn(self.cdc_nofo.get_absolute_url(), content)

        # An NIH viewer sees the row, but not a link they'd only get a 403 from.
        nih_viewer = self.authorize(self.nih_user)
        content = self.client.get(self.url).content.decode("utf-8")

        self.assertIn("d.docx", content)
        self.assertNotIn(self.cdc_nofo.get_absolute_url(), content)
        self.assertEqual(nih_viewer.group, "nih")

    def test_opdiv_filter_narrows_the_page(self):
        self.authorize()

        content = self.client.get(self.url, {"group": "nih"}).content.decode("utf-8")

        self.assertIn("IMPORT-NO-SECTIONS", content)
        self.assertNotIn("IMPORT-OPDIV-BLANK", content)

    def test_unknown_opdiv_is_rejected(self):
        self.authorize()

        self.assertEqual(self.client.get(self.url, {"group": "nope"}).status_code, 400)

    def test_empty_state_reads_as_a_clean_result_not_missing_data(self):
        self.authorize()

        content = self.client.get(self.url, {"group": "acf"}).content.decode("utf-8")

        self.assertIn("No import errors recorded", content)

    def test_long_lists_paginate(self):
        self.authorize()
        with freeze_time("2026-09-11 12:00:00"):
            for index in range(60):
                self.record_failure(
                    self.cdc_user, "IMPORT-UNEXPECTED", f"bulk-{index}.docx"
                )

        first_page = self.client.get(self.url).content.decode("utf-8")
        second_page = self.client.get(self.url, {"page": 2}).content.decode("utf-8")

        self.assertIn("Page 1 of", first_page)
        self.assertIn("Next", first_page)
        self.assertIn("Page 2 of", second_page)

    def test_results_are_not_cached_by_intermediaries(self):
        self.authorize()

        response = self.client.get(self.url)

        self.assertEqual(response["Cache-Control"], "private, no-store")


@freeze_time("2026-09-20 12:00:00")
class MetricsPageLinkTests(TestCase):
    def setUp(self):
        self.viewer = BloomUser.objects.create_user(
            email="viewer@example.com",
            password=None,
            group="cdc",
            force_password_reset=False,
        )
        self.viewer.user_permissions.add(
            Permission.objects.get(codename="view_builder_metrics")
        )
        self.client.force_login(self.viewer)

    def test_dashboard_payload_carries_the_drill_down_url_for_the_chosen_opdiv(self):
        """
        The server's job is to put the right URL in the payload; the anchor
        itself is rendered client-side and covered by
        tests/js/builder_metrics.test.cjs.
        """
        response = self.client.get(
            reverse("nofos:builder_metrics"),
            {"group": "cdc"},
            headers={"accept": "application/json"},
        )

        self.assertEqual(
            response.json()["importErrorsUrl"],
            "{}?group=cdc".format(reverse("nofos:builder_metrics_import_errors")),
        )

    def test_drill_down_url_follows_the_all_opdivs_default(self):
        response = self.client.get(
            reverse("nofos:builder_metrics"), headers={"accept": "application/json"}
        )

        self.assertTrue(response.json()["importErrorsUrl"].endswith("?group=all"))
