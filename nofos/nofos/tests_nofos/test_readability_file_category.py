"""Attempted file category is bounded metadata, never a filename or content proof."""

import time
from unittest.mock import patch

from bloom_nofos.tests_bloom_nofos.test_pdf_readability import REPORT
from constance.test import override_config
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from users.models import BloomUser

from nofos.models import PdfReadabilityAttempt
from nofos.pdf_readability import PdfReadabilityError
from nofos.pdf_readability_metrics import record_attempt


@override_config(
    HHS_NOFO_AUTHENTICATED_PDF_METRICS_PILOT_ENABLED=True,
    HHS_NOFO_PDF_METRICS_PILOT_ENABLED=True,
)
@override_settings(
    PDF_READABILITY_ATTEMPT_RECORDING_ENABLED=True,
    AUTHENTICATED_PDF_READABILITY_ATTEMPT_RECORDING_ENABLED=True,
)
class FileCategoryTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="synthetic-category@example.com",
            password=None,
            group="bloom",
            force_password_reset=False,
        )
        self.user.user_permissions.add(
            Permission.objects.get(codename="use_pdf_readability_pilot"),
            Permission.objects.get(codename="view_builder_metrics"),
        )
        self.client.force_login(self.user)
        self.public = reverse("pdf_readability")
        self.authenticated = reverse("nofos:authenticated_pdf_readability")
        self.metrics = reverse("nofos:builder_metrics_readability_pilot")

    def upload(self, name):
        return SimpleUploadedFile(
            name, b"SYNTHETIC-PRIVATE-CONTENT", content_type="private/mime-value"
        )

    def test_success_and_parser_failure_keep_attempted_extension_only(self):
        for url, name, category in (
            (self.public, "PRIVATE-NAME.PDF", "pdf"),
            (self.authenticated, "PRIVATE-NAME.DoCx", "docx"),
        ):
            for error in (
                None,
                PdfReadabilityError(
                    "invalid_word" if category == "docx" else "invalid_pdf"
                ),
            ):
                with self.subTest(category=category, error=error), patch(
                    "bloom_nofos.views.analyze_uploaded_pdf",
                    return_value=REPORT,
                    side_effect=error,
                ):
                    response = self.client.post(url, {"pdf": self.upload(name)})
                    self.assertEqual(response.status_code, 400 if error else 200)
                    record = PdfReadabilityAttempt.objects.get()
                    self.assertEqual(record.file_category, category)
                    self.assertEqual(record.outcome, error.code if error else "success")
                    self.assertNotIn("PRIVATE", str(record.__dict__))
                    PdfReadabilityAttempt.objects.all().delete()

    def test_public_docx_rejection_records_attempted_category(self):
        with patch("bloom_nofos.views.analyze_uploaded_pdf") as analyze:
            self.assertEqual(
                self.client.post(
                    self.public, {"pdf": self.upload("private.docx")}
                ).status_code,
                400,
            )
            analyze.assert_not_called()
        row = PdfReadabilityAttempt.objects.get()
        self.assertEqual((row.file_category, row.outcome), ("docx", "unsupported_file"))

    @patch("nofos.pdf_readability.MAX_UPLOAD_BYTES", 1)
    def test_aborted_oversized_upload_is_unknown(self):
        with patch("bloom_nofos.views.analyze_uploaded_pdf") as analyze:
            response = self.client.post(
                self.public, {"pdf": self.upload("private.pdf")}
            )
            self.assertEqual(response.status_code, 413)
            analyze.assert_not_called()
        row = PdfReadabilityAttempt.objects.get()
        self.assertEqual((row.file_category, row.outcome), ("unknown", "too_large"))

    def test_missing_multiple_and_unsupported_uploads_are_unknown(self):
        for files in (
            {},
            {"pdf": [self.upload("a.pdf"), self.upload("b.docx")]},
            {"pdf": self.upload("a.exe")},
        ):
            with self.subTest(files=list(files)):
                response = self.client.post(self.authenticated, files)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    PdfReadabilityAttempt.objects.get().file_category, "unknown"
                )
                PdfReadabilityAttempt.objects.all().delete()

    @override_config(HHS_NOFO_PDF_METRICS_PILOT_ENABLED=False)
    def test_disabled_does_not_parse_upload_for_category(self):
        with patch("bloom_nofos.views._pdf_readability_form") as form:
            self.assertEqual(
                self.client.post(
                    self.public, {"pdf": self.upload("private.pdf")}
                ).status_code,
                403,
            )
            form.assert_not_called()
        self.assertEqual(PdfReadabilityAttempt.objects.get().file_category, "unknown")

    @override_settings(
        PDF_READABILITY_ATTEMPT_RECORDING_ENABLED=False,
        AUTHENTICATED_PDF_READABILITY_ATTEMPT_RECORDING_ENABLED=False,
    )
    def test_category_does_not_bypass_recording_switches(self):
        for source in ("public", "authenticated"):
            record_attempt(
                "success", 200, time.monotonic(), source=source, file_category="pdf"
            )
        self.assertFalse(PdfReadabilityAttempt.objects.exists())
        self.assertNotContains(self.client.get(self.authenticated), "its file category")

    def test_recording_normalizes_unrecognized_categories_without_storing_them(self):
        for value in ("private-name.pdf", "application/pdf", None, "PDF", []):
            record_attempt("success", 200, time.monotonic(), file_category=value)
        self.assertEqual(
            set(PdfReadabilityAttempt.objects.values_list("file_category", flat=True)),
            {"unknown"},
        )

    def test_notice_discloses_category_on_both_routes(self):
        for url in (self.public, self.authenticated):
            self.assertContains(
                self.client.get(url), "its file category (PDF, DOCX or unknown)"
            )

    def test_combined_filters_apply_to_counts_rates_charts_durations_and_rows(self):
        for source, category, outcome, duration in (
            ("authenticated", "pdf", "success", 10),
            ("authenticated", "docx", "success", 20),
            ("authenticated", "docx", "invalid_word", 40),
            ("public", "pdf", "success", 100),
            ("unknown", "unknown", "success", 200),
        ):
            PdfReadabilityAttempt.objects.create(
                source=source,
                file_category=category,
                outcome=outcome,
                http_status=200 if outcome == "success" else 400,
                duration_ms=duration,
            )
        response = self.client.get(
            self.metrics,
            {"source": "authenticated", "file_category": "docx"},
            HTTP_ACCEPT="application/json",
        )
        data = response.json()
        self.assertEqual(
            (data["total_attempts"], data["successes"], data["success_rate_pct"]),
            (2, 1, 50.0),
        )
        self.assertEqual((data["p50_duration_ms"], data["p95_duration_ms"]), (20, 40))
        self.assertEqual(sum(row["attempts"] for row in data["daily"]), 2)
        self.assertEqual(sum(row["attempts"] for row in data["weekly"]), 2)
        self.assertEqual(data["chart_daily"][-1]["attempts"], 2)
        self.assertEqual(data["chart_weekly"][-1]["attempts"], 2)
        self.assertTrue(
            all(
                row["file_category"] == "docx" and row["source"] == "authenticated"
                for row in data["recent_attempts"]
            )
        )
        self.assertEqual(
            {row["code"]: row["attempts"] for row in data["file_categories"]},
            {"pdf": 1, "docx": 2, "unknown": 0},
        )
        self.assertEqual(response["Cache-Control"], "private, no-store")
        unknown = self.client.get(
            self.metrics, {"file_category": "unknown"}, HTTP_ACCEPT="application/json"
        ).json()
        self.assertEqual(unknown["total_attempts"], 1)
        invalid = self.client.get(
            self.metrics,
            {"file_category": "private-name.pdf"},
            HTTP_ACCEPT="application/json",
        ).json()
        self.assertEqual(
            (invalid["file_category"], invalid["total_attempts"]), ("all", 5)
        )

    def test_pagination_and_print_text_preserve_both_filters(self):
        PdfReadabilityAttempt.objects.bulk_create(
            [
                PdfReadabilityAttempt(
                    source="authenticated",
                    file_category="docx",
                    outcome="success",
                    http_status=200,
                    duration_ms=1,
                )
                for _ in range(51)
            ]
        )
        page = self.client.get(
            self.metrics, {"source": "authenticated", "file_category": "docx"}
        )
        self.assertContains(
            page, 'href="?source=authenticated&amp;file_category=docx&amp;page=2"'
        )
        self.assertContains(
            page, "Selected file category: <strong>DOCX</strong>", html=False
        )
        self.assertContains(page, "Historical and unclassified attempts are Unknown.")


class FileCategoryMigrationTests(TransactionTestCase):
    def test_existing_successes_and_format_errors_remain_unknown(self):
        before = [("nofos", "0157_merge_candidate_access_and_history")]
        after = [("nofos", "0158_readability_attempt_file_category")]
        executor = MigrationExecutor(connection)
        try:
            executor.migrate(before)
            old = executor.loader.project_state(before).apps.get_model(
                "nofos", "PdfReadabilityAttempt"
            )
            for outcome in ("success", "invalid_pdf", "invalid_word"):
                old.objects.create(
                    source="public", outcome=outcome, http_status=200, duration_ms=1
                )
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            new = executor.loader.project_state(after).apps.get_model(
                "nofos", "PdfReadabilityAttempt"
            )
            self.assertEqual(
                list(new.objects.values_list("file_category", flat=True)),
                ["unknown"] * 3,
            )
        finally:
            MigrationExecutor(connection).migrate(after)
