"""Public PDF readability page; processing itself is tested in nofos tests."""

from unittest.mock import patch

from bloom_nofos.views import _metric_rows, _safe_upload_name
from constance.test import override_config
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from nofos.pdf_readability import PdfReadabilityError


def sample_pdf(name="example.pdf"):
    return SimpleUploadedFile(
        name, b"%PDF-1.4\nexample", content_type="application/pdf"
    )


REPORT = {
    "profile": "generic",
    "reliability": "low",
    "pages_analyzed": 2,
    "pages_total": 3,
    "coverage": "Some text was not measured.",
    "warnings": ["A table may have been read out of order."],
    "version": "hhs-nofo-metrics 0.5.3",
    "metrics": {
        "word_count": {"value": 1234, "status": "estimated", "reliability": "low"},
        "words_per_sentence": {
            "value": 18.16,
            "status": "estimated",
            "reliability": "low",
        },
        "sentences_per_paragraph": {
            "value": None,
            "status": "unavailable",
            "reliability": "low",
        },
        "flesch_reading_ease": {
            "value": 44.25,
            "status": "estimated",
            "reliability": "low",
        },
        "flesch_kincaid_grade_level": {
            "value": 10.5,
            "status": "estimated",
            "reliability": "low",
        },
        "passive_sentence_percentage": {
            "value": 19.74,
            "status": "estimated",
            "reliability": "low",
        },
    },
}


class PdfReadabilityPageTests(TestCase):
    def setUp(self):
        self.url = reverse("pdf_readability")

    def test_flag_is_off_by_default_for_get_and_post(self):
        self.assertEqual(self.client.get(self.url).status_code, 503)
        response = self.client.post(self.url, {"pdf": sample_pdf()})
        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "Service status", status_code=503)
        self.assertContains(response, "HHS | NOFO Builder", status_code=503)
        self.assertContains(response, "Back to top", status_code=503)
        self.assertContains(response, "Latest updates", status_code=503)
        self.assertNotContains(response, 'type="file"', status_code=503)
        self.assertNotIn("Retry-After", response)
        self.assertIn("no-store", response["Cache-Control"])

    @override_config(HHS_NOFO_PDF_METRICS_PILOT_ENABLED=True)
    def test_signed_out_form_has_csrf_file_label_and_no_login_link(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "pdf_readability.css")
        self.assertContains(response, "styles.css")
        self.assertNotContains(response, "theme-base.css")
        self.assertNotContains(response, "fonts.googleapis.com")
        self.assertContains(response, "<span>HHS | NOFO Builder</span>", html=True)
        self.assertNotContains(response, ">HHS | NOFO Builder</a>")
        self.assertContains(response, "Back to top")
        self.assertContains(response, "Latest updates")
        self.assertContains(response, 'for="pdf"')
        self.assertContains(response, "usa-file-input__input")
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, "One PDF, up to 15 MB")
        self.assertContains(response, "Upload a draft NOFO PDF")
        self.assertNotContains(response, "Upload one draft NOFO PDF")
        self.assertContains(
            response,
            "created from an HHS-approved FY27 template or NOFO development tool",
        )
        self.assertContains(
            response,
            "Contact your agency's grants policy office to confirm template compliance",
        )
        self.assertContains(
            response,
            "<strong>This report does not validate format compliance or make a clearance decision.</strong>",
            html=True,
        )
        self.assertNotContains(response, "Login")
        self.assertNotContains(response, "All NOFOs")
        self.assertIn("no-store", response["Cache-Control"])

    def test_noindex_headers_cover_disabled_errors_and_unsupported_methods(self):
        for enabled in (False, True):
            with override_config(HHS_NOFO_PDF_METRICS_PILOT_ENABLED=enabled):
                client = self.client_class(enforce_csrf_checks=True)
                for response in (
                    client.get(self.url),
                    client.post(self.url),
                    client.put(self.url),
                ):
                    self.assertEqual(
                        response["X-Robots-Tag"],
                        "noindex, nofollow, noarchive, nosnippet",
                    )
                    self.assertIn("no-store", response["Cache-Control"])

    def test_public_metric_policy_omits_reading_ease(self):
        rows = _metric_rows(REPORT)
        self.assertEqual(len(rows), 5)
        self.assertNotIn("Flesch Reading Ease", [row["label"] for row in rows])

    @override_config(HHS_NOFO_PDF_METRICS_PILOT_ENABLED=True)
    def test_post_rejects_missing_or_multiple_files(self):
        self.assertEqual(self.client.post(self.url).status_code, 400)
        with patch("bloom_nofos.views.analyze_uploaded_pdf") as analyze:
            response = self.client.post(
                self.url, {"pdf": [sample_pdf("one.pdf"), sample_pdf("two.pdf")]}
            )
        self.assertEqual(response.status_code, 400)
        analyze.assert_not_called()
        self.assertContains(response, "Choose one PDF", status_code=400)

    @override_config(HHS_NOFO_PDF_METRICS_PILOT_ENABLED=True)
    @patch("bloom_nofos.views.analyze_uploaded_pdf", return_value=REPORT)
    def test_report_is_immediate_printable_and_escaped(self, analyze):
        response = self.client.post(
            self.url, {"pdf": sample_pdf("<img src=x onerror=alert(1)>.pdf")}
        )
        self.assertEqual(response.status_code, 200)
        analyze.assert_called_once()
        self.assertContains(response, "Readability report")
        self.assertContains(response, "How to read these results")
        self.assertContains(
            response, "not a compliance, accessibility, or clearance determination"
        )
        self.assertNotContains(response, "theme-base.css")
        self.assertContains(response, "Print / save as PDF")
        self.assertContains(response, "1,234")
        self.assertContains(response, "Not available")
        self.assertNotContains(response, "Unavailable · Low reliability")
        self.assertContains(response, "Unavailable")
        self.assertContains(response, "low-reliability estimate")
        self.assertContains(response, "Copy metrics")
        self.assertContains(response, "HHS | NOFO Builder")
        self.assertContains(response, "Calculation notes (1)")
        self.assertNotContains(response, 'id="readability-calculation-notes" open')
        self.assertNotContains(response, "Flesch Reading Ease")
        self.assertContains(response, "2 of 3 pages processed")
        self.assertNotContains(response, "2 of 3 pages analyzed")
        self.assertContains(response, "Some text was not measured.")
        self.assertContains(response, "A table may have been read out of order.")
        self.assertContains(response, "hhs-nofo-metrics 0.5.3")
        self.assertContains(response, "&lt;img src=x onerror=alert(1)&gt;.pdf")
        self.assertNotContains(response, "<img src=x onerror=alert(1)>.pdf")
        self.assertNotContains(response, "Login")
        self.assertIn("no-store", response["Cache-Control"])

    @override_config(HHS_NOFO_PDF_METRICS_PILOT_ENABLED=True)
    @patch("bloom_nofos.views.analyze_uploaded_pdf")
    def test_busy_error_is_safe_and_retryable(self, analyze):
        analyze.side_effect = PdfReadabilityError("busy")
        response = self.client.post(self.url, {"pdf": sample_pdf()})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "15")
        self.assertContains(response, "The analyzer is busy", status_code=429)
        self.assertContains(response, 'aria-invalid="true"', status_code=429)
        self.assertContains(
            response, 'aria-describedby="pdf--hint pdf--error"', status_code=429
        )
        self.assertIn("no-store", response["Cache-Control"])

    @override_config(HHS_NOFO_PDF_METRICS_PILOT_ENABLED=True)
    def test_csrf_is_enforced_for_public_post(self):
        client = self.client_class(enforce_csrf_checks=True)
        response = client.post(self.url, {"pdf": sample_pdf()})
        self.assertEqual(response.status_code, 403)
        self.assertIn("no-store", response["Cache-Control"])

    @override_config(HHS_NOFO_PDF_METRICS_PILOT_ENABLED=True)
    def test_streaming_upload_limit_returns_413(self):
        oversized = SimpleUploadedFile(
            "oversized.pdf",
            b"%PDF-1.4\n" + b"x" * (15 * 1024 * 1024),
            content_type="application/pdf",
        )
        with patch("bloom_nofos.views.analyze_uploaded_pdf") as analyze:
            response = self.client.post(self.url, {"pdf": oversized})
        self.assertEqual(response.status_code, 413)
        self.assertContains(response, "too large", status_code=413)
        analyze.assert_not_called()

    def test_filename_is_bounded_and_metric_values_must_be_finite(self):
        self.assertEqual(_safe_upload_name("C:\\private\\sample.pdf"), "sample.pdf")
        self.assertEqual(len(_safe_upload_name("x" * 300 + ".pdf")), 180)
        report = {**REPORT, "metrics": {"word_count": {"value": float("nan")}}}
        self.assertEqual(_metric_rows(report)[0]["value"], "Not available")

    @override_config(HHS_NOFO_PDF_METRICS_PILOT_ENABLED=True)
    @patch("bloom_nofos.views.analyze_uploaded_pdf", return_value=REPORT)
    def test_long_hostile_filename_is_bounded_and_escaped_in_report(self, analyze):
        name = "<script>" + "x" * 200 + ".pdf"
        response = self.client.post(self.url, {"pdf": sample_pdf(name)})

        self.assertEqual(response.status_code, 200)
        analyze.assert_called_once()
        self.assertEqual(len(response.context["filename"]), 180)
        self.assertContains(response, "&lt;script&gt;" + "x" * 172)
        self.assertNotContains(response, "<script>")

    @override_config(HHS_NOFO_PDF_METRICS_PILOT_ENABLED=True)
    @patch("bloom_nofos.views.analyze_uploaded_pdf")
    def test_report_keeps_unavailable_measure_and_many_long_warnings(self, analyze):
        warnings = [
            f"Extraction note {index:02d}. " + "More detail. " * 40
            for index in range(20)
        ]
        warnings.append("A <fragment> was excluded.")
        analyze.return_value = {**REPORT, "warnings": warnings}

        response = self.client.post(self.url, {"pdf": sample_pdf()})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Not available")
        self.assertNotContains(response, "Unavailable · Low reliability")
        for warning in warnings[:-1]:
            self.assertContains(response, warning)
        self.assertContains(response, "A &lt;fragment&gt; was excluded.")
        self.assertNotContains(response, "<fragment>")
