import time
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from bloom_nofos.tests_bloom_nofos.test_utils import VALID_DOCX
from constance.test import override_config
from django.core.management import CommandError, call_command
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from users.models import BloomUser

from nofos.models import Nofo, WordDownloadAttempt
from nofos.readability_word_export import (
    builder_salt,
    checker_report_token,
    report_token,
)
from nofos.word_download_metrics import outcome_for, record_word_download

CHECKER_REPORT = {
    "profile": "word",
    "scope": {
        "recovered_word_count": 42,
        "sentence_word_count": 0,
        "complete_sentence_count": 0,
        "excluded_word_count": 42,
    },
}


@override_config(
    HHS_NOFO_METRICS_ENABLED=True,
    HHS_NOFO_READABILITY_WORD_EXPORT_ENABLED=True,
    HHS_NOFO_PDF_METRICS_PILOT_ENABLED=True,
    HHS_NOFO_POLICY_EXPORT_ENABLED=True,
)
@override_settings(
    GRABZIT_APPLICATION_KEY="synthetic-key",
    GRABZIT_APPLICATION_SECRET="synthetic-secret",
    GRABZIT_WORD_EXPORT_ALLOWED_HOSTS=("testserver",),
    WORD_DOWNLOAD_ATTEMPT_RECORDING_ENABLED=True,
)
class WordDownloadRecordingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = BloomUser.objects.create_user(
            email="word-download-metrics@example.com",
            password="test-password",
            group="cdc",
            force_password_reset=False,
        )
        cls.nofo = Nofo.objects.create(
            title="Word download metrics NOFO",
            short_name="word-download-metrics",
            number="TEST-WD-001",
            opdiv="CDC",
            group="cdc",
            status="draft",
        )

    def setUp(self):
        provider = patch("bloom_nofos.utils.GrabzItClient.GrabzItClient")
        self.grabzit = self.enterContext(provider).return_value
        self.grabzit.SaveTo.return_value = VALID_DOCX
        self.client = Client()
        self.client.force_login(self.user)
        # GrabzIt copies the session and CSRF cookies onto its own request.
        self.client.cookies["csrftoken"] = "synthetic-csrf"
        self.export_url = reverse("nofos:nofo_export", args=[self.nofo.pk])
        self.panel_url = reverse(
            "nofos:nofo_readability_word_export", args=[self.nofo.pk]
        )
        self.checker_url = reverse("pdf_readability_word_export")

    def only_attempt(self):
        self.assertEqual(WordDownloadAttempt.objects.count(), 1)
        return WordDownloadAttempt.objects.get()

    def builder_token(self):
        request = RequestFactory().get("/")
        request.user = self.user
        return report_token(
            request,
            {"metrics": {"word_count": {"value": 10}}},
            scope="builder",
            salt=builder_salt(request, self.nofo),
        )

    # NOFO export page

    def test_nofo_word_export_success(self):
        response = self.client.post(
            self.export_url, {"export_action": "download"}, secure=True
        )

        self.assertEqual(response.status_code, 200)
        attempt = self.only_attempt()
        self.assertEqual(attempt.source, "nofo_export")
        self.assertEqual(attempt.outcome, "success")
        self.assertEqual(attempt.http_status, 200)
        self.assertGreaterEqual(attempt.duration_ms, 0)
        self.assertTrue(attempt.authenticated)
        self.assertEqual(attempt.metrics_group, "cdc")
        self.assertTrue(attempt.metrics_included)
        self.assertEqual(attempt.nofo, self.nofo)

    def test_nofo_clearance_export_success(self):
        self.client.post(
            self.export_url, {"export_action": "download_stripped"}, secure=True
        )

        attempt = self.only_attempt()
        self.assertEqual(attempt.source, "nofo_clearance")
        self.assertEqual(attempt.outcome, "success")

    @override_config(HHS_NOFO_POLICY_EXPORT_ENABLED=False)
    def test_clearance_export_while_disabled_is_recorded_as_disabled(self):
        response = self.client.post(
            self.export_url, {"export_action": "download_stripped"}, secure=True
        )

        self.assertEqual(response.status_code, 400)
        attempt = self.only_attempt()
        self.assertEqual(attempt.source, "nofo_clearance")
        self.assertEqual(attempt.outcome, "export_disabled")
        self.grabzit.URLToDOCX.assert_not_called()

    def test_unknown_export_action_is_not_recorded(self):
        response = self.client.post(
            self.export_url, {"export_action": "bogus"}, secure=True
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(WordDownloadAttempt.objects.exists())

    def test_provider_failure_is_recorded(self):
        self.grabzit.SaveTo.side_effect = RuntimeError("synthetic provider failure")

        response = self.client.post(
            self.export_url, {"export_action": "download"}, secure=True
        )

        self.assertEqual(response.status_code, 502)
        attempt = self.only_attempt()
        self.assertEqual(attempt.outcome, "conversion_failed")
        self.assertEqual(attempt.http_status, 502)

    def test_invalid_provider_document_is_recorded(self):
        self.grabzit.SaveTo.return_value = b"not a docx"

        self.client.post(self.export_url, {"export_action": "download"}, secure=True)

        self.assertEqual(self.only_attempt().outcome, "invalid_docx")

    def test_missing_cookies_are_recorded(self):
        del self.client.cookies["csrftoken"]

        self.client.post(self.export_url, {"export_action": "download"}, secure=True)

        self.assertEqual(self.only_attempt().outcome, "missing_cookies")

    @override_settings(GRABZIT_WORD_EXPORT_ALLOWED_HOSTS=("nofos.example",))
    def test_unconfigured_host_is_recorded_as_disabled(self):
        response = self.client.post(
            self.export_url, {"export_action": "download"}, secure=True
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.only_attempt().outcome, "export_disabled")

    def test_excluded_group_is_marked_not_included(self):
        self.user.group = "bloom"
        self.user.save()

        self.client.post(self.export_url, {"export_action": "download"}, secure=True)

        attempt = self.only_attempt()
        self.assertEqual(attempt.metrics_group, "bloom")
        self.assertFalse(attempt.metrics_included)

    def test_deleting_the_nofo_keeps_the_attempt(self):
        self.client.post(self.export_url, {"export_action": "download"}, secure=True)

        self.nofo.delete()

        attempt = self.only_attempt()
        self.assertIsNone(attempt.nofo)
        self.assertEqual(attempt.outcome, "success")

    # Readability metrics panel

    def test_readability_panel_success(self):
        response = self.client.post(self.panel_url, {"report": self.builder_token()})

        self.assertEqual(response.status_code, 200)
        attempt = self.only_attempt()
        self.assertEqual(attempt.source, "readability_panel")
        self.assertEqual(attempt.outcome, "success")
        self.assertEqual(attempt.nofo, self.nofo)

    def test_readability_panel_expired_results(self):
        token = self.builder_token()
        with patch("django.core.signing.time.time", return_value=time.time() + 3601):
            response = self.client.post(self.panel_url, {"report": token})

        self.assertEqual(response.status_code, 410)
        self.assertEqual(self.only_attempt().outcome, "results_expired")

    def test_readability_panel_invalid_results(self):
        response = self.client.post(self.panel_url, {"report": "tampered"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.only_attempt().outcome, "results_invalid")

    @override_config(HHS_NOFO_METRICS_ENABLED=False)
    def test_readability_panel_while_metrics_disabled(self):
        response = self.client.post(self.panel_url, {"report": self.builder_token()})

        self.assertEqual(response.status_code, 503)
        attempt = self.only_attempt()
        self.assertEqual(attempt.source, "readability_panel")
        self.assertEqual(attempt.outcome, "export_disabled")

    # Readability Checker

    def test_public_checker_download(self):
        token = checker_report_token(RequestFactory().get("/"), CHECKER_REPORT)

        response = Client().post(self.checker_url, {"report": token})

        self.assertEqual(response.status_code, 200)
        attempt = self.only_attempt()
        self.assertEqual(attempt.source, "readability_checker")
        self.assertEqual(attempt.outcome, "success")
        self.assertFalse(attempt.authenticated)
        self.assertEqual(attempt.metrics_group, "")
        self.assertIsNone(attempt.metrics_included)
        self.assertIsNone(attempt.nofo)

    def test_signed_in_checker_download(self):
        request = RequestFactory().get("/")
        request.user = self.user
        token = checker_report_token(request, CHECKER_REPORT)

        self.client.post(self.checker_url, {"report": token})

        attempt = self.only_attempt()
        self.assertTrue(attempt.authenticated)
        self.assertEqual(attempt.metrics_group, "cdc")

    @override_config(HHS_NOFO_READABILITY_WORD_EXPORT_ENABLED=False)
    def test_checker_download_while_word_export_disabled(self):
        token = checker_report_token(RequestFactory().get("/"), CHECKER_REPORT)

        response = Client().post(self.checker_url, {"report": token})

        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.only_attempt().outcome, "export_disabled")

    # Recording rules

    @override_settings(WORD_DOWNLOAD_ATTEMPT_RECORDING_ENABLED=False)
    def test_nothing_is_recorded_when_recording_is_off(self):
        response = self.client.post(
            self.export_url, {"export_action": "download"}, secure=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(WordDownloadAttempt.objects.exists())

    def test_recording_failure_does_not_break_the_download(self):
        with patch(
            "nofos.word_download_metrics.WordDownloadAttempt.objects.create",
            side_effect=RuntimeError("synthetic database failure"),
        ):
            with self.assertLogs(
                "django.request.word_download_metrics", "WARNING"
            ) as logs:
                response = self.client.post(
                    self.export_url, {"export_action": "download"}, secure=True
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, VALID_DOCX)
        self.assertNotIn("synthetic database failure", "\n".join(logs.output))

    def test_composer_downloads_are_not_recorded(self):
        # Composer uses the same GrabzIt helper but isn't one of the four sources.
        from bloom_nofos.utils import generate_docx_download_response

        request = RequestFactory().post("/", HTTP_HOST="testserver", secure=True)
        request.COOKIES = {"sessionid": "s", "csrftoken": "c"}
        generate_docx_download_response(
            request=request,
            export_url="https://testserver/composer/export",
            target_element="#download_target",
            filename_base="guide",
        )

        self.assertFalse(WordDownloadAttempt.objects.exists())

    def test_rows_hold_no_document_or_user_fields(self):
        self.assertEqual(
            {field.name for field in WordDownloadAttempt._meta.get_fields()},
            {
                "id",
                "created_at",
                "source",
                "outcome",
                "http_status",
                "duration_ms",
                "authenticated",
                "metrics_group",
                "metrics_included",
                "nofo",
            },
        )


@override_settings(WORD_DOWNLOAD_ATTEMPT_RECORDING_ENABLED=True)
class WordDownloadOutcomeTests(TestCase):
    def test_tagged_outcome_wins(self):
        response = HttpResponse(status=500)
        response.word_download_outcome = "host_mismatch"
        self.assertEqual(outcome_for(response), "host_mismatch")

    def test_untagged_responses_fall_back_to_status(self):
        cases = {
            200: "success",
            400: "results_invalid",
            410: "results_expired",
            502: "conversion_failed",
            503: "export_disabled",
            500: "unknown",
        }
        for status, outcome in cases.items():
            with self.subTest(status=status):
                self.assertEqual(outcome_for(HttpResponse(status=status)), outcome)

    def test_unknown_source_is_not_recorded(self):
        request = RequestFactory().post("/")
        with self.assertLogs("django.request.word_download_metrics", "WARNING"):
            record_word_download(
                request,
                source="composer",
                response=HttpResponse(),
                started=time.monotonic(),
            )
        self.assertFalse(WordDownloadAttempt.objects.exists())


class WordDownloadCleanupTests(TestCase):
    def make_attempt(self, days_old):
        attempt = WordDownloadAttempt.objects.create(
            source="nofo_export",
            outcome="success",
            http_status=200,
            duration_ms=1,
            authenticated=True,
        )
        WordDownloadAttempt.objects.filter(pk=attempt.pk).update(
            created_at=timezone.now() - timedelta(days=days_old)
        )
        return attempt

    def test_requires_a_retention_window(self):
        with self.assertRaises(CommandError):
            call_command("cleanup_word_download_attempts", stdout=StringIO())

    @override_settings(WORD_DOWNLOAD_ATTEMPT_RETENTION_DAYS=30)
    def test_dry_run_then_delete_only_old_rows(self):
        old = self.make_attempt(45)
        recent = self.make_attempt(5)

        out = StringIO()
        call_command("cleanup_word_download_attempts", dry_run=True, stdout=out)
        self.assertIn("Would delete 1", out.getvalue())
        self.assertEqual(WordDownloadAttempt.objects.count(), 2)

        out = StringIO()
        call_command("cleanup_word_download_attempts", stdout=out)
        self.assertIn("Deleted 1", out.getvalue())
        self.assertEqual(
            list(WordDownloadAttempt.objects.values_list("pk", flat=True)),
            [recent.pk],
        )
        self.assertFalse(WordDownloadAttempt.objects.filter(pk=old.pk).exists())
