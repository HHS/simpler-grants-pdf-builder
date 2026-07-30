from unittest.mock import patch

import docraptor
from django.test import Client, TestCase
from django.urls import reverse
from easyaudit.models import CRUDEvent
from users.models import BloomUser

from nofos.models import Nofo


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

    @patch("nofos.views.docraptor.DocApi")
    def test_get_returns_405_and_does_not_print(self, mock_doc_api):
        """A follow-up GET (what the Acrobat extension issues) must not 500."""
        response = self.client.get("{}?mode=inline".format(self.url))

        self.assertEqual(response.status_code, 405)
        self.assertIn("POST", response["Allow"])
        # no PDF was generated and no audit event was recorded
        mock_doc_api.assert_not_called()
        self.assertEqual(self._print_event_count(), 0)

    @patch("nofos.views.docraptor.DocApi")
    def test_head_returns_405_and_does_not_print(self, mock_doc_api):
        """DetailView also accepts HEAD, so it needs the same guard as GET."""
        response = self.client.head(self.url)

        self.assertEqual(response.status_code, 405)
        mock_doc_api.assert_not_called()
        self.assertEqual(self._print_event_count(), 0)

    @patch("nofos.views.docraptor.DocApi")
    def test_range_request_returns_405_and_does_not_print(self, mock_doc_api):
        """Byte-range re-requests against an inline PDF must not 500 either."""
        response = self.client.get(self.url, headers={"range": "bytes=0-1023"})

        self.assertEqual(response.status_code, 405)
        mock_doc_api.assert_not_called()
        self.assertEqual(self._print_event_count(), 0)

    ###################################################
    # POST behaviour is unchanged
    ###################################################

    @patch("nofos.views.docraptor.DocApi")
    def test_post_returns_pdf_inline(self, mock_doc_api):
        mock_doc_api.return_value.create_doc.return_value = b"%PDF-1.4 fake pdf"

        response = self.client.post("{}?mode=inline".format(self.url))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(
            response["Content-Disposition"], 'inline; filename="nofo-test-001.pdf"'
        )
        self.assertEqual(response.content, b"%PDF-1.4 fake pdf")

    @patch("nofos.views.docraptor.DocApi")
    def test_post_returns_pdf_as_attachment_by_default(self, mock_doc_api):
        mock_doc_api.return_value.create_doc.return_value = b"%PDF-1.4 fake pdf"

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Disposition"], 'attachment; filename="nofo-test-001.pdf"'
        )

    @patch("nofos.views.docraptor.DocApi")
    def test_post_creates_a_single_print_audit_event(self, mock_doc_api):
        mock_doc_api.return_value.create_doc.return_value = b"%PDF-1.4 fake pdf"

        self.client.post("{}?mode=inline".format(self.url))

        self.assertEqual(self._print_event_count(), 1)

    ###################################################
    # Exception handling degrades gracefully
    ###################################################

    @patch("nofos.views.docraptor.DocApi")
    def test_post_handles_docraptor_api_exception(self, mock_doc_api):
        mock_doc_api.return_value.create_doc.side_effect = docraptor.rest.ApiException(
            status=422, reason="Unprocessable Entity"
        )

        with self.assertLogs("django.request", level="ERROR"):
            response = self.client.post(self.url)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._print_event_count(), 0)

    @patch("nofos.views.docraptor.DocApi")
    def test_post_handles_unexpected_exception(self, mock_doc_api):
        """Non-ApiException failures used to escape as a raw 500."""
        mock_doc_api.return_value.create_doc.side_effect = ValueError("boom")

        with self.assertLogs("django.request", level="ERROR"):
            response = self.client.post(self.url)

        self.assertEqual(response.status_code, 400)
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

        with patch("nofos.views.docraptor.DocApi") as mock_doc_api:
            response = other_client.post(self.url)

        self.assertEqual(response.status_code, 403)
        mock_doc_api.assert_not_called()

    def test_login_required(self):
        anon_client = Client()
        response = anon_client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response["Location"])
