"""Restricted entry point and source-aware, content-free reporting."""

from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from bloom_nofos.tests_bloom_nofos.test_pdf_readability import REPORT
from constance.test import override_config
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import DatabaseError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from users.models import BloomUser

from nofos.models import PdfReadabilityAttempt
from nofos.pdf_readability import PdfReadabilityError


@override_config(
    HHS_NOFO_AUTHENTICATED_PDF_METRICS_PILOT_ENABLED=True,
    HHS_NOFO_PDF_METRICS_PILOT_ENABLED=False,
)
@override_settings(
    AUTHENTICATED_PDF_READABILITY_ATTEMPT_RECORDING_ENABLED=True,
    AUTHENTICATED_PDF_READABILITY_ATTEMPT_RETENTION_DAYS=7,
)
class AuthenticatedPilotTests(TestCase):
    def setUp(self):
        self.url = reverse("nofos:authenticated_pdf_readability")
        self.public_url = reverse("pdf_readability")
        self.user = BloomUser.objects.create_user(
            email="synthetic@example.com",
            password=None,
            group="bloom",
            force_password_reset=False,
        )
        self.permission = Permission.objects.get(codename="use_pdf_readability_pilot")

    def login(self):
        self.user.groups.add(
            Group.objects.get(name="PDF readability pilot participants")
        )
        self.client.force_login(self.user)

    def upload(self):
        return SimpleUploadedFile(
            "SECRET-FILENAME.pdf",
            b"%PDF-1.7 SECRET-TEXT",
            content_type="application/pdf",
        )

    def test_authentication_and_explicit_permission_before_analysis(self):
        with patch("bloom_nofos.views.analyze_uploaded_pdf") as analyze:
            for method in ("get", "post"):
                response = getattr(self.client, method)(self.url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response["Location"].startswith(reverse("users:login")))
            self.client.force_login(self.user)
            for method in ("get", "post"):
                self.assertEqual(
                    getattr(self.client, method)(self.url).status_code, 403
                )
            analyze.assert_not_called()
        self.assertFalse(PdfReadabilityAttempt.objects.exists())

    def test_internal_group_and_approved_group_access_and_revocation(self):
        self.login()
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.user.groups.remove(
            Group.objects.get(name="PDF readability pilot participants")
        )
        self.assertEqual(self.client.post(self.url).status_code, 403)

    def test_public_disabled_independently_no_navigation_link(self):
        self.login()
        self.assertEqual(self.client.get(self.public_url).status_code, 503)
        response = self.client.get(self.url)
        self.assertContains(response, "How we handle your PDF")
        self.assertContains(response, "do not include your identity")
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertIn("noindex", response["X-Robots-Tag"])
        self.assertNotContains(
            self.client.get(reverse("nofos:nofo_index")), f'href="{self.url}"'
        )

    @override_config(HHS_NOFO_AUTHENTICATED_PDF_METRICS_PILOT_ENABLED=False)
    def test_disabled_get_not_counted_post_counted_without_analysis(self):
        self.login()
        with patch("bloom_nofos.views.analyze_uploaded_pdf") as analyze:
            self.assertEqual(self.client.get(self.url).status_code, 503)
            self.assertFalse(PdfReadabilityAttempt.objects.exists())
            self.assertEqual(self.client.post(self.url).status_code, 503)
            analyze.assert_not_called()
        row = PdfReadabilityAttempt.objects.get()
        self.assertEqual((row.source, row.outcome), ("authenticated", "disabled"))

    def test_success_reuses_report_and_stays_in_authenticated_workflow(self):
        self.login()
        with patch("bloom_nofos.views.analyze_uploaded_pdf", return_value=REPORT):
            response = self.client.post(self.url, {"pdf": self.upload()})
        self.assertContains(response, "Readability report")
        self.assertContains(response, f'href="{self.url}"')
        self.assertContains(response, "Print / save as PDF")
        self.assertContains(response, "Copy metrics")
        row = PdfReadabilityAttempt.objects.get()
        self.assertEqual((row.source, row.outcome), ("authenticated", "success"))
        self.assertNotIn("SECRET", str(row.__dict__))
        self.assertFalse(self.user.has_perm("nofos.view_builder_metrics"))
        self.assertEqual(
            self.client.get(
                reverse("nofos:builder_metrics_readability_pilot")
            ).status_code,
            403,
        )

    def test_csrf_failure_has_no_analysis_or_outcome(self):
        self.login()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        with patch("bloom_nofos.views.analyze_uploaded_pdf") as analyze:
            response = client.post(self.url, {"pdf": self.upload()})
        self.assertEqual(response.status_code, 403)
        self.assertIn("noindex", response["X-Robots-Tag"])
        analyze.assert_not_called()
        self.assertFalse(PdfReadabilityAttempt.objects.exists())

    def test_valid_csrf_upload(self):
        self.login()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        client.get(self.url)
        with patch("bloom_nofos.views.analyze_uploaded_pdf", return_value=REPORT):
            response = client.post(
                self.url,
                {
                    "pdf": self.upload(),
                    "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PdfReadabilityAttempt.objects.count(), 1)

    @override_config(HHS_NOFO_AUTHENTICATED_PDF_METRICS_PILOT_ENABLED=False)
    def test_disabled_authenticated_post_still_requires_csrf(self):
        self.login()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.url).status_code, 403)
        self.assertFalse(PdfReadabilityAttempt.objects.exists())

    def test_handled_errors_and_capacity_record_once(self):
        self.login()
        for code in (
            "invalid_pdf",
            "format_unsupported",
            "encrypted",
            "no_text",
            "too_large",
            "busy",
            "timeout",
            "unavailable",
        ):
            with self.subTest(code=code), patch(
                "bloom_nofos.views.analyze_uploaded_pdf",
                side_effect=PdfReadabilityError(code),
            ):
                error = PdfReadabilityError(code)
                response = self.client.post(self.url, {"pdf": self.upload()})
                self.assertEqual(response.status_code, error.http_status)
                self.assertEqual(PdfReadabilityAttempt.objects.get().outcome, code)
                if code == "busy":
                    self.assertEqual(response["Retry-After"], "15")
                PdfReadabilityAttempt.objects.all().delete()

    def test_unexpected_analysis_failure_is_sanitized_and_counted_once(self):
        self.login()
        with patch(
            "bloom_nofos.views.analyze_uploaded_pdf",
            side_effect=RuntimeError("SECRET-TEXT"),
        ), self.assertLogs("django.request.pdf_readability", level="WARNING") as logs:
            response = self.client.post(self.url, {"pdf": self.upload()})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn(b"SECRET", response.content)
        self.assertEqual(PdfReadabilityAttempt.objects.get().outcome, "internal_error")
        self.assertNotIn("SECRET", repr(logs.records[0].__dict__))
        self.assertIsNone(logs.records[0].exc_info)

    def test_recording_failure_does_not_lose_report(self):
        self.login()
        with patch(
            "bloom_nofos.views.analyze_uploaded_pdf", return_value=REPORT
        ), patch(
            "nofos.pdf_readability_metrics.PdfReadabilityAttempt.objects.create",
            side_effect=DatabaseError("SECRET-TEXT"),
        ):
            response = self.client.post(self.url, {"pdf": self.upload()})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(PdfReadabilityAttempt.objects.exists())

    def test_unexpected_report_formatting_failure_is_counted_once(self):
        self.login()
        with patch(
            "bloom_nofos.views.analyze_uploaded_pdf", return_value=REPORT
        ), patch("bloom_nofos.views._metric_rows", side_effect=RuntimeError("SECRET")):
            response = self.client.post(self.url, {"pdf": self.upload()})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn(b"SECRET", response.content)
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(PdfReadabilityAttempt.objects.count(), 1)
        self.assertEqual(PdfReadabilityAttempt.objects.get().outcome, "internal_error")

    @override_settings(AUTHENTICATED_PDF_READABILITY_ATTEMPT_RECORDING_ENABLED=False)
    def test_recording_independent_of_public_setting(self):
        self.login()
        with patch("bloom_nofos.views.analyze_uploaded_pdf", return_value=REPORT):
            self.assertEqual(
                self.client.post(self.url, {"pdf": self.upload()}).status_code, 200
            )
        self.assertFalse(PdfReadabilityAttempt.objects.exists())

    @override_settings(AUTHENTICATED_PDF_READABILITY_ATTEMPT_RETENTION_DAYS=None)
    def test_auth_recording_requires_retention_but_report_does_not(self):
        self.login()
        with patch("bloom_nofos.views.analyze_uploaded_pdf", return_value=REPORT):
            self.assertEqual(
                self.client.post(self.url, {"pdf": self.upload()}).status_code, 200
            )
        self.assertFalse(PdfReadabilityAttempt.objects.exists())

    @override_config(HHS_NOFO_PDF_METRICS_PILOT_ENABLED=True)
    @override_settings(PDF_READABILITY_ATTEMPT_RECORDING_ENABLED=True)
    def test_signed_in_public_upload_is_public(self):
        self.login()
        with patch("bloom_nofos.views.analyze_uploaded_pdf", return_value=REPORT):
            self.client.post(self.public_url, {"pdf": self.upload()})
        self.assertEqual(PdfReadabilityAttempt.objects.get().source, "public")


class SourceDashboardTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="viewer@example.com",
            password=None,
            group="bloom",
            force_password_reset=False,
        )
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_builder_metrics")
        )
        self.client.force_login(self.user)
        self.url = reverse("nofos:builder_metrics_readability_pilot")
        for source, outcome in (
            ("authenticated", "success"),
            ("authenticated", "busy"),
            ("public", "success"),
            ("unknown", "timeout"),
        ):
            PdfReadabilityAttempt.objects.create(
                source=source,
                outcome=outcome,
                http_status=200 if outcome == "success" else 503,
                duration_ms=10,
            )

    def test_source_filter_html_json_and_rates(self):
        for source, count, rate in (
            ("all", 4, 50),
            ("authenticated", 2, 50),
            ("public", 1, 100),
            ("unknown", 1, 0),
        ):
            with self.subTest(source=source):
                data = self.client.get(
                    self.url, {"source": source}, HTTP_ACCEPT="application/json"
                ).json()
                self.assertEqual(
                    (data["source"], data["total_attempts"], data["success_rate_pct"]),
                    (source, count, rate),
                )
                self.assertEqual(sum(row["attempts"] for row in data["sources"]), 4)
                self.assertTrue(
                    source == "all"
                    or all(row["source"] == source for row in data["recent_attempts"])
                )
                page = self.client.get(self.url, {"source": source})
                self.assertEqual(
                    page.context["metrics"],
                    data
                    | {
                        "daily": page.context["metrics"]["daily"],
                        "weekly": page.context["metrics"]["weekly"],
                        "recent_attempts": page.context["metrics"]["recent_attempts"],
                    },
                )

    def test_pagination_preserves_selected_source(self):
        PdfReadabilityAttempt.objects.bulk_create(
            [
                PdfReadabilityAttempt(
                    source="authenticated",
                    outcome="success",
                    http_status=200,
                    duration_ms=1,
                )
                for _ in range(51)
            ]
        )
        page = self.client.get(self.url, {"source": "authenticated"})
        self.assertContains(page, "?source=authenticated&amp;page=2")
        data = self.client.get(
            self.url,
            {"source": "authenticated", "page": 2},
            HTTP_ACCEPT="application/json",
        ).json()
        self.assertEqual(len(data["recent_attempts"]), 3)

    def test_metrics_permission_does_not_grant_upload(self):
        self.assertEqual(
            self.client.get(reverse("nofos:authenticated_pdf_readability")).status_code,
            403,
        )

    @override_settings(
        PDF_READABILITY_ATTEMPT_RETENTION_DAYS=30,
        AUTHENTICATED_PDF_READABILITY_ATTEMPT_RETENTION_DAYS=7,
    )
    def test_cleanup_is_source_specific(self):
        PdfReadabilityAttempt.objects.update(
            created_at=timezone.now() - timedelta(days=10)
        )
        call_command(
            "cleanup_pdf_readability_attempts", source="public", stdout=StringIO()
        )
        self.assertEqual(PdfReadabilityAttempt.objects.count(), 4)
        call_command(
            "cleanup_pdf_readability_attempts",
            source="authenticated",
            dry_run=True,
            stdout=StringIO(),
        )
        self.assertEqual(PdfReadabilityAttempt.objects.count(), 4)
        call_command(
            "cleanup_pdf_readability_attempts",
            source="authenticated",
            stdout=StringIO(),
        )
        self.assertEqual(
            set(PdfReadabilityAttempt.objects.values_list("source", flat=True)),
            {"public", "unknown"},
        )

    def test_legacy_backfill_and_new_unknown_default(self):
        import importlib
        from types import SimpleNamespace

        from django.apps import apps
        from django.db import connection

        module = importlib.import_module(
            "nofos.migrations.0150_authenticated_pdf_readability_pilot"
        )
        # At migration time the pre-source implementation recorded only public
        # route outcomes. New direct inserts after migration remain unknown.
        module.prepare_pilot(apps, SimpleNamespace(connection=connection))
        self.assertFalse(
            PdfReadabilityAttempt.objects.filter(source="unknown").exists()
        )
        row = PdfReadabilityAttempt.objects.create(
            outcome="success", http_status=200, duration_ms=1
        )
        self.assertEqual(row.source, "unknown")
