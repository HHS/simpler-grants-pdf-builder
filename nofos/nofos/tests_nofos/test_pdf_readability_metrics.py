from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from constance.test import override_config
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from users.models import BloomUser

from nofos.models import PdfReadabilityAttempt
from nofos.pdf_readability import _ERRORS, PDF_READABILITY_OUTCOMES, PdfReadabilityError


@override_settings(PDF_READABILITY_ATTEMPT_RECORDING_ENABLED=True)
class AttemptTests(TestCase):
    def setUp(self):
        self.url = reverse("pdf_readability")

    def upload(self):
        return SimpleUploadedFile("SECRET-FILENAME.pdf", b"%PDF-1.7 SECRET-TEXT")

    def test_exact_content_free_schema(self):
        from easyaudit.signals.model_signals import should_audit

        self.assertFalse(should_audit(PdfReadabilityAttempt()))
        self.assertEqual(
            {f.name for f in PdfReadabilityAttempt._meta.fields},
            {"id", "created_at", "source", "outcome", "http_status", "duration_ms"},
        )
        self.assertEqual(
            set(PDF_READABILITY_OUTCOMES),
            {"success", "disabled", "internal_error", *_ERRORS},
        )

    def test_disabled_recorded_get_not_recorded(self):
        self.client.get(self.url)
        self.assertEqual(PdfReadabilityAttempt.objects.count(), 0)
        self.assertEqual(self.client.post(self.url).status_code, 503)
        self.assertEqual(PdfReadabilityAttempt.objects.get().outcome, "disabled")

    @override_settings(PDF_READABILITY_ATTEMPT_RECORDING_ENABLED=False)
    def test_recording_default_safety_gate(self):
        self.client.post(self.url)
        self.assertFalse(PdfReadabilityAttempt.objects.exists())

    @override_config(HHS_NOFO_PDF_METRICS_PILOT_ENABLED=True)
    def test_each_analysis_outcome_recorded_once_without_content(self):
        for code, (_, status) in _ERRORS.items():
            with self.subTest(code=code), patch(
                "bloom_nofos.views.analyze_uploaded_pdf",
                side_effect=PdfReadabilityError(code),
            ), patch("nofos.pdf_readability_metrics.logger.warning") as warning:
                response = self.client.post(self.url, {"pdf": self.upload()})
                self.assertEqual(response.status_code, status)
                attempt = PdfReadabilityAttempt.objects.get()
                self.assertEqual(attempt.outcome, code)
                self.assertEqual(attempt.http_status, status)
                self.assertGreaterEqual(attempt.duration_ms, 0)
                self.assertNotIn("SECRET", str(attempt.__dict__))
                warning.assert_not_called()
                PdfReadabilityAttempt.objects.all().delete()

    @override_config(HHS_NOFO_PDF_METRICS_PILOT_ENABLED=True)
    def test_success_written_after_analysis_slot_release(self):
        from nofos.pdf_readability import _analysis_slot
        from nofos.pdf_readability_metrics import record_attempt

        def analyze(upload):
            with _analysis_slot():
                return {
                    "metrics": {"word_count": {"value": 987654}},
                    "page_count": 42,
                    "text": "SECRET-TEXT",
                }

        def record(*args):
            # A second slot acquisition would raise busy if recording ran under
            # the analysis lock. Exercise the real slot, not just call ordering.
            with _analysis_slot():
                record_attempt(*args)

        with patch(
            "bloom_nofos.views.analyze_uploaded_pdf", side_effect=analyze
        ), patch("bloom_nofos.views.record_attempt", side_effect=record):
            response = self.client.post(self.url, {"pdf": self.upload()})
        self.assertEqual(response.status_code, 200)
        attempt = PdfReadabilityAttempt.objects.get()
        self.assertEqual(attempt.outcome, "success")
        self.assertNotIn("987654", str(attempt.__dict__))

    @override_config(HHS_NOFO_PDF_METRICS_PILOT_ENABLED=True)
    def test_invalid_form_and_upload_limit(self):
        self.assertEqual(self.client.post(self.url).status_code, 400)
        self.assertEqual(PdfReadabilityAttempt.objects.get().outcome, "invalid_pdf")
        PdfReadabilityAttempt.objects.all().delete()
        with patch("nofos.pdf_readability.MAX_UPLOAD_BYTES", 2):
            self.assertEqual(
                self.client.post(self.url, {"pdf": self.upload()}).status_code, 413
            )
        self.assertEqual(PdfReadabilityAttempt.objects.get().outcome, "too_large")

    @override_config(HHS_NOFO_PDF_METRICS_PILOT_ENABLED=True)
    def test_csrf_rejection_not_misclassified_as_pdf_failure(self):
        self.assertEqual(
            Client(enforce_csrf_checks=True).post(self.url).status_code, 403
        )
        self.assertFalse(PdfReadabilityAttempt.objects.exists())

    def test_db_failure_does_not_change_response_or_log_exception(self):
        with patch(
            "nofos.pdf_readability_metrics.PdfReadabilityAttempt.objects.create",
            side_effect=DatabaseError("SECRET-TEXT"),
        ), self.assertLogs(
            "django.request.pdf_readability_metrics", level="WARNING"
        ) as logs:
            response = self.client.post(self.url)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            [r.getMessage() for r in logs.records],
            ["PDF readability outcome could not be recorded."],
        )
        self.assertIsNone(logs.records[0].exc_info)
        self.assertFalse(PdfReadabilityAttempt.objects.exists())

    @override_config(HHS_NOFO_PDF_METRICS_PILOT_ENABLED=True)
    def test_db_failure_preserves_enabled_success_and_busy(self):
        for failure, expected in ((None, 200), (PdfReadabilityError("busy"), 429)):
            with self.subTest(expected=expected), patch(
                "bloom_nofos.views.analyze_uploaded_pdf",
                return_value={},
                side_effect=failure,
            ), patch(
                "nofos.pdf_readability_metrics.PdfReadabilityAttempt.objects.create",
                side_effect=DatabaseError("SECRET-FILENAME SECRET-TEXT"),
            ), self.assertLogs(
                "django.request.pdf_readability_metrics", level="WARNING"
            ) as logs:
                response = self.client.post(self.url, {"pdf": self.upload()})
                self.assertEqual(response.status_code, expected)
                if expected == 429:
                    self.assertEqual(response["Retry-After"], "15")
                self.assertEqual(
                    logs.records[0].getMessage(),
                    "PDF readability outcome could not be recorded.",
                )
                self.assertIsNone(logs.records[0].exc_info)


class MetricsTests(TestCase):
    def setUp(self):
        self.url = reverse("nofos:builder_metrics_readability_pilot")
        self.user = BloomUser.objects.create_user(
            email="synthetic@example.com",
            password=None,
            group="bloom",
            force_password_reset=False,
        )

    def login_viewer(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_builder_metrics")
        )
        self.client.force_login(self.user)

    def test_permission_required_on_both_pages(self):
        for authenticated in (False, True):
            if authenticated:
                self.client.force_login(self.user)
            for url in (self.url, reverse("nofos:builder_metrics")):
                self.assertIn(self.client.get(url).status_code, (302, 403))
                self.assertIn(
                    self.client.get(url, HTTP_ACCEPT="application/json").status_code,
                    (302, 403),
                )

    @override_settings(
        PDF_READABILITY_ATTEMPT_RETENTION_DAYS=None,
        AUTHENTICATED_PDF_READABILITY_ATTEMPT_RETENTION_DAYS=None,
    )
    def test_links_and_empty_state(self):
        self.login_viewer()
        page = self.client.get(self.url)
        self.assertContains(page, "Back to usage &amp; quality metrics")
        self.assertContains(page, 'href="/nofos/metrics"')
        self.assertContains(page, "Public retention: Not configured")
        self.assertContains(page, "Authenticated retention: Not configured")
        self.assertContains(page, "OpDiv filtering isn't available")
        self.assertContains(page, ".back-link, .pilot-pagination")
        self.assertEqual(page["Cache-Control"], "private, no-store")
        main = self.client.get(reverse("nofos:builder_metrics"), {"group": "cdc"})
        self.assertContains(main, 'aria-label="Other metrics pages"')
        self.assertContains(main, f'href="{self.url}"')
        self.assertContains(main, ".metrics-other-pages { display: none !important; }")
        self.assertLess(
            main.content.index(b"Other metrics pages"),
            main.content.index(b"How historical metrics are preserved"),
        )

    def test_chart_windows_preserve_unknown_coverage_and_source_filter(self):
        self.login_viewer()
        for source in ("public", "authenticated"):
            PdfReadabilityAttempt.objects.create(
                source=source, outcome="success", http_status=200, duration_ms=10
            )
        old = PdfReadabilityAttempt.objects.create(
            source="authenticated", outcome="busy", http_status=429, duration_ms=10
        )
        PdfReadabilityAttempt.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=100)
        )
        data = self.client.get(
            self.url, {"source": "authenticated"}, HTTP_ACCEPT="application/json"
        ).json()
        self.assertEqual(data["total_attempts"], 2)
        self.assertEqual(data["unsuccessful"], 1)
        self.assertEqual(len(data["chart_daily"]), 30)
        self.assertEqual(len(data["chart_weekly"]), 12)
        self.assertEqual(data["chart_daily"][-1]["attempts"], 1)
        self.assertEqual(data["chart_weekly"][-1]["attempts"], 1)
        self.assertTrue(
            all(row["attempts"] is None for row in data["chart_daily"][:-1])
        )
        self.assertEqual(data["chart_daily"][-1]["period"], str(timezone.localdate()))
        self.assertEqual(
            data["chart_weekly"][-1]["period"],
            str(timezone.localdate() - timedelta(days=timezone.localdate().weekday())),
        )
        page = self.client.get(self.url, {"source": "authenticated"})
        self.assertContains(
            page, 'class="metrics-data-details margin-top-2 font-sans-2xs"', count=2
        )
        self.assertContains(page, "About these metrics")
        self.assertContains(page, "No data")

    @override_config(HHS_NOFO_PDF_METRICS_PILOT_ENABLED=True)
    def test_json_aggregates_pagination_and_denominator(self):
        self.login_viewer()
        for n in range(51):
            PdfReadabilityAttempt.objects.create(
                outcome="success" if n < 25 else "busy",
                http_status=200 if n < 25 else 429,
                duration_ms=n,
            )
        response = self.client.get(self.url, HTTP_ACCEPT="application/json")
        data = response.json()
        self.assertTrue(data["enabled"])
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(data["total_attempts"], 51)
        self.assertEqual(data["success_rate_pct"], 49.0)
        self.assertEqual(data["p50_duration_ms"], 25)
        self.assertEqual(data["p95_duration_ms"], 48)
        self.assertEqual(sum(r["attempts"] for r in data["daily"]), 51)
        self.assertEqual(sum(r["attempts"] for r in data["weekly"]), 51)
        self.assertEqual(len(data["recent_attempts"]), 50)
        self.assertEqual(
            set(data["recent_attempts"][0]),
            {"created_at", "source", "outcome", "http_status", "duration_ms"},
        )
        self.assertEqual(
            len(
                self.client.get(
                    self.url + "?page=2", HTTP_ACCEPT="application/json"
                ).json()["recent_attempts"]
            ),
            1,
        )

    def test_cleanup_requires_approved_configuration_and_dry_run(self):
        with self.assertRaises(CommandError):
            call_command("cleanup_pdf_readability_attempts", stdout=StringIO())
        old = PdfReadabilityAttempt.objects.create(
            outcome="success", http_status=200, duration_ms=1
        )
        PdfReadabilityAttempt.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=31)
        )
        recent = PdfReadabilityAttempt.objects.create(
            outcome="disabled", http_status=503, duration_ms=1
        )
        with override_settings(PDF_READABILITY_ATTEMPT_RETENTION_DAYS=30):
            call_command(
                "cleanup_pdf_readability_attempts", dry_run=True, stdout=StringIO()
            )
            self.assertEqual(PdfReadabilityAttempt.objects.count(), 2)
            call_command("cleanup_pdf_readability_attempts", stdout=StringIO())
            self.assertEqual(
                list(PdfReadabilityAttempt.objects.values_list("pk", flat=True)),
                [recent.pk],
            )
