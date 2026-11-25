from datetime import timedelta

from bs4 import BeautifulSoup
from constance.test import override_config
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from users.models import BloomUser

from nofos.metrics import months_from, word_downloads_by_month
from nofos.models import WordDownloadAttempt


def attempt(source="nofo_export", outcome="success", **fields):
    defaults = {
        "http_status": 200 if outcome == "success" else 502,
        "duration_ms": 1000,
        "authenticated": True,
        "metrics_group": "cdc",
        "metrics_included": True,
    }
    defaults.update(fields)
    return WordDownloadAttempt.objects.create(
        source=source, outcome=outcome, **defaults
    )


@override_config(WORD_DOWNLOAD_ATTEMPT_RECORDING_ENABLED=True)
class WordDownloadMetricsPageTests(TestCase):
    def setUp(self):
        self.url = reverse("nofos:builder_metrics_word_downloads")
        self.user = BloomUser.objects.create_user(
            email="word-downloads-viewer@example.com",
            password=None,
            group="bloom",
            force_password_reset=False,
        )

    def login_viewer(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_builder_metrics")
        )
        self.client.force_login(self.user)

    def soup(self, response):
        return BeautifulSoup(response.content, "html.parser")

    def test_permission_required(self):
        self.assertIn(self.client.get(self.url).status_code, (302, 403))
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(
            self.client.get(self.url, HTTP_ACCEPT="application/json").status_code,
            403,
        )

    def test_empty_state_back_link_and_headers(self):
        self.login_viewer()

        page = self.client.get(self.url, {"group": "hrsa"})

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "<title>Word downloads", html=False)
        back = self.soup(page).select_one(".back-link a")
        self.assertEqual(back.get_text(strip=True), "Back to usage & quality metrics")
        self.assertEqual(back["href"], reverse("nofos:builder_metrics") + "?group=hrsa")
        self.assertContains(page, "No recorded attempts for these filters.")
        self.assertContains(page, "Retention: No automatic expiration")
        self.assertEqual(page["Cache-Control"], "private, no-store")

    @override_config(WORD_DOWNLOAD_ATTEMPT_RECORDING_ENABLED=False)
    def test_recording_off_notice(self):
        self.login_viewer()
        self.assertContains(
            self.client.get(self.url), "Word download recording is off."
        )

    def test_invalid_group_is_rejected(self):
        self.login_viewer()
        self.assertEqual(self.client.get(self.url, {"group": "bloom"}).status_code, 400)

    def test_totals_sources_failures_and_internal_exclusion(self):
        attempt()
        attempt(outcome="conversion_failed", duration_ms=3000)
        attempt(source="nofo_clearance")
        attempt(
            source="readability_checker",
            authenticated=False,
            metrics_group="",
            metrics_included=None,
        )
        attempt(source="readability_panel", outcome="results_expired")
        # Bloomworks/staging downloads are excluded everywhere.
        attempt(metrics_group="bloom", metrics_included=False)
        self.login_viewer()

        data = self.client.get(self.url, HTTP_ACCEPT="application/json").json()

        self.assertEqual(data["total_attempts"], 5)
        self.assertEqual(data["successes"], 3)
        self.assertEqual(data["failed"], 2)
        self.assertEqual(data["success_rate_pct"], 60.0)
        by_source = {row["code"]: row for row in data["by_source"]}
        self.assertEqual(by_source["nofo_export"]["attempts"], 2)
        self.assertEqual(by_source["nofo_export"]["success_rate_pct"], 50.0)
        self.assertEqual(by_source["nofo_export"]["p50_duration_ms"], 1000)
        self.assertEqual(by_source["nofo_export"]["p50_seconds"], 1.0)
        self.assertEqual(data["p95_seconds"], 3.0)
        self.assertEqual(data["checker_split"], {"authenticated": 0, "public": 1})
        outcomes = {row["code"]: row for row in data["outcomes"]}
        self.assertEqual(outcomes["conversion_failed"]["attempts"], 1)
        self.assertEqual(outcomes["results_expired"]["rate_pct"], 20.0)
        self.assertEqual(data["provider_failure_rate_pct"], 20.0)

        page = self.client.get(self.url)
        reasons = [
            th.get_text(strip=True)
            for th in self.soup(page).select(
                "h2:-soup-contains('What prevented') + div tbody th"
            )
        ]
        self.assertEqual(
            sorted(reasons),
            ["Readability results expired", "Word conversion failed (GrabzIt)"],
        )

    def test_source_filter(self):
        attempt()
        attempt(source="nofo_clearance", outcome="invalid_docx")
        self.login_viewer()

        data = self.client.get(
            self.url, {"source": "nofo_clearance"}, HTTP_ACCEPT="application/json"
        ).json()

        self.assertEqual(data["total_attempts"], 1)
        self.assertEqual(data["failed"], 1)
        self.assertEqual(data["source_label"], "NOFO clearance export")
        # The by-source table keeps every source, marking the selected one.
        selected = {row["code"]: row["selected"] for row in data["by_source"]}
        self.assertEqual(
            selected,
            {
                "nofo_export": False,
                "nofo_clearance": True,
                "readability_panel": False,
                "readability_checker": False,
            },
        )

    def test_opdiv_filter_keeps_only_that_groups_signed_in_downloads(self):
        attempt(metrics_group="cdc")
        attempt(metrics_group="hrsa")
        attempt(
            source="readability_checker",
            authenticated=False,
            metrics_group="",
            metrics_included=None,
        )
        self.login_viewer()

        data = self.client.get(
            self.url, {"group": "hrsa"}, HTTP_ACCEPT="application/json"
        ).json()

        self.assertEqual(data["total_attempts"], 1)
        self.assertEqual(data["group_label"], "HRSA")

    def test_signed_in_filter_only_applies_to_the_checker(self):
        attempt(
            source="readability_checker",
            authenticated=False,
            metrics_group="",
            metrics_included=None,
        )
        attempt(source="readability_checker")
        attempt()
        self.login_viewer()

        checker = self.client.get(
            self.url,
            {"source": "readability_checker", "signed_in": "public", "group": "cdc"},
        )
        self.assertEqual(checker.context["metrics"]["total_attempts"], 1)
        # Checker downloads ignore the OpDiv filter and show the signed-in one.
        self.assertEqual(checker.context["metrics"]["group"], "all")
        soup = self.soup(checker)
        self.assertIsNotNone(soup.select_one("#word-downloads-signed-in"))
        self.assertIsNone(soup.select_one("#word-downloads-group"))

        builder = self.client.get(self.url, {"signed_in": "public"})
        self.assertEqual(builder.context["metrics"]["signed_in"], "all")
        self.assertEqual(builder.context["metrics"]["total_attempts"], 3)
        soup = self.soup(builder)
        self.assertIsNone(soup.select_one("#word-downloads-signed-in"))
        self.assertIsNotNone(soup.select_one("#word-downloads-group"))

    def test_charts_show_no_data_for_unobserved_days(self):
        attempt()
        attempt(outcome="conversion_failed")
        self.login_viewer()

        data = self.client.get(self.url, HTTP_ACCEPT="application/json").json()

        today = data["chart_daily"][-1]
        self.assertEqual((today["attempts"], today["failed"]), (2, 1))
        self.assertIsNone(data["chart_daily"][0]["attempts"])
        self.assertEqual(len(data["chart_daily"]), 30)
        self.assertEqual(len(data["chart_weekly"]), 12)

    def test_recent_attempts_paginate_with_filters(self):
        for _ in range(51):
            attempt(source="readability_panel")
        self.login_viewer()

        page = self.client.get(self.url, {"source": "readability_panel"})

        self.assertEqual(len(page.context["metrics"]["recent_attempts"]), 50)
        self.assertContains(
            page,
            "?source=readability_panel&amp;signed_in=all&amp;group=all&amp;page=2",
        )
        second = self.client.get(self.url, {"source": "readability_panel", "page": 2})
        self.assertEqual(len(second.context["metrics"]["recent_attempts"]), 1)


@override_config(HHS_NOFO_METRICS_ENABLED=True)
class WordDownloadMetricsNavigationTests(TestCase):
    def setUp(self):
        user = BloomUser.objects.create_user(
            email="word-downloads-nav@example.com",
            password=None,
            group="bloom",
            force_password_reset=False,
        )
        user.user_permissions.add(
            Permission.objects.get(codename="view_builder_metrics")
        )
        self.client.force_login(user)
        self.url = reverse("nofos:builder_metrics_word_downloads")

    def test_related_links_row_names_and_order(self):
        main = self.client.get(reverse("nofos:builder_metrics"), {"group": "cdc"})

        nav = BeautifulSoup(main.content, "html.parser").select_one(
            "nav.metrics-other-pages"
        )
        self.assertEqual(
            [a.get_text(strip=True) for a in nav.find_all("a")],
            ["Readability metrics", "Readability Checker usage", "Word downloads"],
        )
        self.assertNotIn("NOFO readability metrics", nav.get_text())
        link = nav.select_one("#metrics-word-downloads-link")
        self.assertEqual(link["href"], self.url + "?group=cdc")

    def test_card_payload_links_and_counts_successes(self):
        attempt()
        attempt(outcome="conversion_failed")
        attempt(metrics_group="hrsa")

        main = self.client.get(reverse("nofos:builder_metrics"), {"group": "cdc"})

        data = main.context["metrics_data"]
        self.assertEqual(data["wordDownloadsUrl"], self.url + "?group=cdc")
        self.assertEqual(data["wordDownloads"][-1], 1)
        self.assertContains(main, "Review Word downloads")


class WordDownloadsByMonthTests(TestCase):
    def test_no_data_months_success_counts_and_exclusions(self):
        months = months_from(timezone.now() - timedelta(days=40))
        attempt()
        attempt(outcome="results_invalid")
        attempt(
            source="readability_checker",
            authenticated=False,
            metrics_group="",
            metrics_included=None,
        )
        attempt(metrics_group="bloom", metrics_included=False)

        self.assertEqual(
            word_downloads_by_month(months)[:-1], [None] * (len(months) - 1)
        )
        self.assertEqual(word_downloads_by_month(months)[-1], 2)
        self.assertEqual(word_downloads_by_month(months, "cdc")[-1], 1)
        self.assertIsNone(word_downloads_by_month(months, "hrsa")[-1])
