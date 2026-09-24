from unittest.mock import patch

import docraptor
from constance.test import override_config
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from easyaudit.models import CRUDEvent
from users.models import BloomUser

from nofos.models import Nofo, Section, Subsection
from nofos.pdf_service import GeneratedPDF, PDFGenerationError, generate_nofo_pdf


class PrintNofoAsPDFViewTest(TestCase):
    """
    Regression tests for the print endpoint.

    See https://github.com/HHS/simpler-grants-pdf-builder/issues/781: a follow-up
    GET to the print URL (eg. from the Adobe Acrobat Chrome extension re-requesting
    an inline PDF) used to fall through to DetailView.get() and raise
    TemplateDoesNotExist for the non-existent "nofos/nofo_detail.html", which
    surfaced as a 500.
    """

    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client = Client()
        self.client.login(email="test@example.com", password="testpass123")

        self.nofo = Nofo.objects.create(
            title="Test NOFO",
            short_name="test-nofo",
            number="NOFO-TEST-001",
            opdiv="TEST",
            group="bloom",
            status="draft",
        )
        self.url = reverse("nofos:print_pdf", kwargs={"pk": self.nofo.id})

    def _print_event_count(self):
        return CRUDEvent.objects.filter(
            object_id=self.nofo.pk, changed_fields__contains="nofo_print"
        ).count()

    ###################################################
    # Unsupported methods return 405, never a 500
    ###################################################

    @patch("nofos.pdf_service.docraptor.DocApi")
    def test_get_returns_405_and_does_not_print(self, mock_doc_api):
        """A follow-up GET (what the Acrobat extension issues) must not 500."""
        response = self.client.get("{}?mode=inline".format(self.url))

        self.assertEqual(response.status_code, 405)
        self.assertIn("POST", response["Allow"])
        # no PDF was generated and no audit event was recorded
        mock_doc_api.assert_not_called()
        self.assertEqual(self._print_event_count(), 0)

    @patch("nofos.pdf_service.docraptor.DocApi")
    def test_head_returns_405_and_does_not_print(self, mock_doc_api):
        """DetailView also accepts HEAD, so it needs the same guard as GET."""
        response = self.client.head(self.url)

        self.assertEqual(response.status_code, 405)
        mock_doc_api.assert_not_called()
        self.assertEqual(self._print_event_count(), 0)

    @patch("nofos.pdf_service.docraptor.DocApi")
    def test_range_request_returns_405_and_does_not_print(self, mock_doc_api):
        """Byte-range re-requests against an inline PDF must not 500 either."""
        response = self.client.get(self.url, headers={"range": "bytes=0-1023"})

        self.assertEqual(response.status_code, 405)
        mock_doc_api.assert_not_called()
        self.assertEqual(self._print_event_count(), 0)

    ###################################################
    # POST behaviour is unchanged
    ###################################################

    @override_config(
        HHS_NOFO_ASSISTANCE_LISTING_ENABLED=True,
        HHS_NOFO_ASSISTANCE_LISTING_ON_COVER_ENABLED=True,
    )
    @override_settings(GITHUB_SHA="safe-build-sha")
    @patch(
        "nofos.nofo_document_context.get_cover_image",
        return_value="https://images.example.org/cover.jpg",
    )
    @patch("nofos.pdf_service.docraptor.DocApi")
    def test_post_submits_rendered_document_without_request_secrets(
        self, mock_doc_api, mock_cover
    ):
        mock_doc_api.return_value.create_doc.return_value = b"%PDF-1.4 fake pdf"
        self.nofo.theme = "portrait-cdc-blue"
        self.nofo.author = "Document author"
        self.nofo.subject = "Document subject"
        self.nofo.keywords = "funding, health"
        self.nofo.assistance_listing_number = "93.123"
        self.nofo.inline_css = ".document-custom-style { color: blue; }"
        self.nofo.save()
        section = Section.objects.create(nofo=self.nofo, name="Eligibility", order=2)
        Subsection.objects.create(
            section=section,
            name="Eligible applicants",
            tag="h3",
            order=1,
            body="Unique authorized document body.",
        )
        self.client.cookies["csrftoken"] = "a" * 32
        session_cookie = self.client.cookies["sessionid"].value

        response = self.client.post(
            self.url, HTTP_AUTHORIZATION="Bearer private-secret"
        )

        self.assertEqual(response.status_code, 200)
        payload = mock_doc_api.return_value.create_doc.call_args.args[0]
        self.assertNotIn("document_url", payload)
        self.assertEqual(
            payload["prince_options"]["baseurl"],
            "http://testserver" + reverse("nofos:nofo_view", args=[self.nofo.pk]),
        )
        html = payload["document_content"]
        for expected in (
            self.nofo.title,
            "Unique authorized document body.",
            "theme-orientation-portrait",
            "theme-opdiv-cdc-blue",
            'name="author" content="Document author"',
            'name="subject" content="Document subject"',
            'name="keywords" content="funding, health"',
            'name="github_sha" content="safe-build-sha"',
            "section--cover-page",
            "https://images.example.org/cover.jpg",
            "93.123",
            ".document-custom-style",
        ):
            self.assertIn(expected, html)
        for secret in (
            "csrfmiddlewaretoken",
            "<form",
            "Edit this NOFO",
            self.user.email,
            self.user.password,
            session_cookie,
            "a" * 32,
            "private-secret",
        ):
            self.assertNotIn(secret, html)
        self.assertEqual(payload["document_type"], "pdf")
        self.assertIs(payload["javascript"], False)
        self.assertEqual(payload["pipeline"], 11)
        self.assertEqual(payload["prince_options"]["media"], "print")
        self.assertEqual(payload["prince_options"]["profile"], "PDF/UA-1")
        self.assertIs(mock_doc_api.return_value.api_client.configuration.debug, False)
        mock_cover.assert_called_once_with(self.nofo)

    @patch("nofos.pdf_service.docraptor.DocApi")
    def test_service_returns_bytes_without_a_browser_request_or_print_audit(
        self, mock_doc_api
    ):
        mock_doc_api.return_value.create_doc.return_value = b"%PDF-1.4 fake pdf"

        generated = generate_nofo_pdf(
            self.nofo,
            base_url="https://builder.example.org/nofos/authorized-record",
            is_test_pdf=True,
        )

        self.assertEqual(
            generated,
            GeneratedPDF(content=b"%PDF-1.4 fake pdf", is_test_pdf=True),
        )
        payload = mock_doc_api.return_value.create_doc.call_args.args[0]
        self.assertTrue(payload["test"])
        self.assertEqual(
            payload["prince_options"]["baseurl"],
            "https://builder.example.org/nofos/authorized-record",
        )
        self.assertIn(self.nofo.title, payload["document_content"])
        self.assertNotIn("<form", payload["document_content"])
        self.assertEqual(self._print_event_count(), 0)

    @override_config(DOCRAPTOR_LIVE_MODE=True)
    @patch("nofos.pdf_service.docraptor.DocApi")
    def test_test_mode_query_override_and_invalid_disposition(self, mock_doc_api):
        mock_doc_api.return_value.create_doc.return_value = b"%PDF-1.4 fake pdf"
        self.client.post(self.url)
        self.assertIs(
            mock_doc_api.return_value.create_doc.call_args.args[0]["test"], False
        )
        response = self.client.post(self.url + "?is_test_pdf=true&mode=invalid")
        self.assertIs(
            mock_doc_api.return_value.create_doc.call_args.args[0]["test"], True
        )
        self.assertTrue(response["Content-Disposition"].startswith("attachment;"))

    @patch("nofos.pdf_service.docraptor.DocApi")
    def test_localhost_is_still_rejected(self, mock_doc_api):
        response = self.client.post(self.url, HTTP_HOST="localhost")
        self.assertEqual(response.status_code, 400)
        mock_doc_api.return_value.create_doc.assert_not_called()

    @patch("nofos.pdf_service.docraptor.DocApi")
    def test_post_returns_pdf_inline(self, mock_doc_api):
        mock_doc_api.return_value.create_doc.return_value = b"%PDF-1.4 fake pdf"

        response = self.client.post("{}?mode=inline".format(self.url))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(
            response["Content-Disposition"], 'inline; filename="nofo-test-001.pdf"'
        )
        self.assertEqual(response.content, b"%PDF-1.4 fake pdf")

    @patch("nofos.pdf_service.docraptor.DocApi")
    def test_post_returns_pdf_as_attachment_by_default(self, mock_doc_api):
        mock_doc_api.return_value.create_doc.return_value = b"%PDF-1.4 fake pdf"

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Disposition"], 'attachment; filename="nofo-test-001.pdf"'
        )

    @patch("nofos.pdf_service.docraptor.DocApi")
    def test_post_creates_a_single_print_audit_event(self, mock_doc_api):
        mock_doc_api.return_value.create_doc.return_value = b"%PDF-1.4 fake pdf"

        self.client.post("{}?mode=inline".format(self.url))

        self.assertEqual(self._print_event_count(), 1)

    ###################################################
    # Exception handling degrades gracefully
    ###################################################

    @patch("nofos.pdf_service.docraptor.DocApi")
    def test_post_handles_docraptor_api_exception(self, mock_doc_api):
        mock_doc_api.return_value.create_doc.side_effect = docraptor.rest.ApiException(
            status=422, reason="Unprocessable Entity"
        )

        with self.assertLogs("django.request", level="ERROR"):
            response = self.client.post(self.url)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._print_event_count(), 0)

    @patch("nofos.pdf_service.docraptor.DocApi")
    def test_vendor_failure_diagnostic_omits_exception_payload_and_query(
        self, mock_doc_api
    ):
        sentinel = "synthetic-private-nofo-and-api-key"
        mock_doc_api.return_value.create_doc.side_effect = docraptor.rest.ApiException(
            status=422, reason=sentinel
        )

        # Check the explicit ERROR diagnostic. Django's separate WARNING for a
        # 400 response may include the request query and is outside this seam.
        with self.assertLogs("django.request", level="ERROR") as logs:
            response = self.client.post(self.url + "?secret=" + sentinel)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._print_event_count(), 0)
        self.assertEqual(len(logs.records), 1)
        self.assertNotIn(sentinel, repr(logs.records[0].__dict__))
        self.assertEqual(logs.records[0].status, 400)
        self.assertEqual(logs.records[0].exception_type, "PDFGenerationError")

    @patch("nofos.pdf_service.docraptor.DocApi")
    def test_vendor_exception_content_is_absent_from_all_request_logs(
        self, mock_doc_api
    ):
        sentinel = "synthetic-private-vendor-payload"
        vendor_error = docraptor.rest.ApiException(status=422, reason=sentinel)
        vendor_error.body = sentinel
        vendor_error.headers = {"X-Sensitive": sentinel}
        mock_doc_api.return_value.create_doc.side_effect = vendor_error

        with self.assertLogs("django.request", level="DEBUG") as logs:
            response = self.client.post(self.url)

        self.assertEqual(response.status_code, 400)
        self.assertGreaterEqual(len(logs.records), 1)
        for record in logs.records:
            self.assertNotIn(sentinel, repr(record.__dict__))

    @patch("nofos.pdf_service.docraptor.DocApi")
    def test_service_normalizes_vendor_failure_without_message(self, mock_doc_api):
        sentinel = "synthetic-sensitive-vendor-response"
        mock_doc_api.return_value.create_doc.side_effect = docraptor.rest.ApiException(
            status=422, reason=sentinel
        )

        with self.assertRaises(PDFGenerationError) as caught:
            generate_nofo_pdf(
                self.nofo,
                base_url="https://builder.example.org/nofos/authorized-record",
                is_test_pdf=False,
            )

        self.assertNotIn(sentinel, str(caught.exception))
        self.assertEqual(self._print_event_count(), 0)

    @patch("nofos.pdf_service.docraptor.DocApi")
    def test_post_lets_unexpected_exceptions_return_500(self, mock_doc_api):
        """
        Only DocRaptor API errors are treated as 400s. Anything else (a bug, a
        database failure, a broken audit event) is a server fault and must keep
        the normal 500 path, which JSONRequestLoggingMiddleware.process_exception
        logs at ERROR level before handler500 renders the sanitized 500 page.
        Reporting these as 400s would hide server faults from status-based alerting.
        """
        mock_doc_api.return_value.create_doc.side_effect = ValueError("boom")

        # raise_request_exception is a Client constructor argument: without it the
        # test client re-raises instead of returning the 500 we want to assert on.
        client = Client(raise_request_exception=False)
        client.login(email="test@example.com", password="testpass123")

        with self.assertLogs("django.request", level="ERROR") as logs:
            response = client.post(self.url)

        self.assertEqual(response.status_code, 500)
        self.assertIn("Unhandled Exception", "".join(logs.output))
        self.assertEqual(self._print_event_count(), 0)

    ###################################################
    # Access control still applies
    ###################################################

    def test_post_denied_for_user_in_another_group(self):
        BloomUser.objects.create_user(
            email="other@example.com",
            password="testpass123",
            group="acf",
            force_password_reset=False,
        )
        other_client = Client()
        other_client.login(email="other@example.com", password="testpass123")

        with patch("nofos.pdf_service.docraptor.DocApi") as mock_doc_api:
            response = other_client.post(self.url)

        self.assertEqual(response.status_code, 403)
        mock_doc_api.assert_not_called()

    def test_login_required(self):
        anon_client = Client()
        with patch("nofos.pdf_service.docraptor.DocApi") as mock_doc_api:
            for method in (anon_client.get, anon_client.post):
                response = method(self.url)
                self.assertEqual(response.status_code, 302)
                self.assertIn("/login", response["Location"])
        mock_doc_api.assert_not_called()
