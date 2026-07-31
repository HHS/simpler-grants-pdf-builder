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

    GET is now supported, but only as a replay of a just-generated PDF: POST
    caches the bytes it generates (keyed by NOFO + user + mode + is_test_pdf,
    see PrintNofoAsPDFView.PRINT_PDF_CACHE_TTL_SECONDS), and a follow-up GET
    with matching params serves the cached bytes instead of calling DocRaptor
    or writing a second audit event. A GET with no matching cache entry --
    eg. visiting the print URL directly with no prior POST -- has nothing
    safe to replay and 404s rather than silently generating a fresh document.
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
    # GET with no cache entry: 404, never a 500, never a duplicate
    ###################################################

    @patch("nofos.views.docraptor.DocApi")
    def test_get_with_no_cache_entry_returns_404_and_does_not_print(self, mock_doc_api):
        """
        A follow-up GET with nothing cached (eg. visiting the print URL
        directly, or arriving after the cache window expired) must not 500,
        and must not silently generate a fresh document either.
        """
        response = self.client.get("{}?mode=inline".format(self.url))

        self.assertEqual(response.status_code, 404)
        mock_doc_api.assert_not_called()
        self.assertEqual(self._print_event_count(), 0)

    @patch("nofos.views.docraptor.DocApi")
    def test_head_returns_405_and_does_not_print(self, mock_doc_api):
        """
        HEAD is deliberately excluded from http_method_names -- it's the
        same generation trigger as GET would be if Django auto-routed it to
        get(), and we don't want a third path into PDF generation.
        """
        response = self.client.head(self.url)

        self.assertEqual(response.status_code, 405)
        mock_doc_api.assert_not_called()
        self.assertEqual(self._print_event_count(), 0)

    @patch("nofos.views.docraptor.DocApi")
    def test_range_request_with_no_cache_entry_returns_404_and_does_not_print(
        self, mock_doc_api
    ):
        """Byte-range re-requests against an inline PDF must not 500 either."""
        response = self.client.get(self.url, headers={"range": "bytes=0-1023"})

        self.assertEqual(response.status_code, 404)
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
    # GET after POST: replay from cache, no duplicate generation
    ###################################################

    @patch("nofos.views.docraptor.DocApi")
    def test_get_after_post_replays_cached_bytes_without_a_second_docraptor_call(
        self, mock_doc_api
    ):
        mock_doc_api.return_value.create_doc.return_value = b"%PDF-1.4 fake pdf"

        post_response = self.client.post("{}?mode=inline".format(self.url))
        get_response = self.client.get("{}?mode=inline".format(self.url))

        self.assertEqual(post_response.status_code, 200)
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.content, post_response.content)
        self.assertEqual(
            get_response["Content-Disposition"], post_response["Content-Disposition"]
        )

        # exactly one DocRaptor call total, for the POST -- the GET was
        # served from cache
        mock_doc_api.return_value.create_doc.assert_called_once()
        self.assertEqual(self._print_event_count(), 1)

    @patch("nofos.views.docraptor.DocApi")
    def test_range_request_after_post_is_also_served_from_cache(self, mock_doc_api):
        """
        The Acrobat extension's follow-up re-fetch is sometimes a byte-range
        GET -- this must hit the same cache entry as a plain GET would.
        """
        mock_doc_api.return_value.create_doc.return_value = b"%PDF-1.4 fake pdf"

        self.client.post("{}?mode=inline".format(self.url))
        range_response = self.client.get(
            "{}?mode=inline".format(self.url), headers={"range": "bytes=0-1023"}
        )

        self.assertEqual(range_response.status_code, 200)
        self.assertEqual(range_response.content, b"%PDF-1.4 fake pdf")
        mock_doc_api.return_value.create_doc.assert_called_once()
        self.assertEqual(self._print_event_count(), 1)

    @patch("nofos.views.docraptor.DocApi")
    def test_get_with_different_mode_than_the_post_is_a_cache_miss(self, mock_doc_api):
        """The cache key includes `mode`, so it doesn't cross mode/params."""
        mock_doc_api.return_value.create_doc.return_value = b"%PDF-1.4 fake pdf"

        self.client.post("{}?mode=inline".format(self.url))
        # no ?mode= at all -- defaults to "attachment", a different cache key
        mismatched_get_response = self.client.get(self.url)

        self.assertEqual(mismatched_get_response.status_code, 404)
        mock_doc_api.return_value.create_doc.assert_called_once()

    @patch("nofos.views.docraptor.DocApi")
    def test_get_does_not_see_a_different_users_cached_pdf(self, mock_doc_api):
        """
        The cache key includes the requesting user, so this is strictly a
        replay of *this user's own* just-generated PDF -- a different user's
        follow-up GET must still 404, and if they go on to POST, that's an
        independent print action with its own DocRaptor call and audit event.
        """
        mock_doc_api.return_value.create_doc.return_value = b"%PDF-1.4 fake pdf"

        BloomUser.objects.create_user(
            email="other-bloom-user@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        other_client = Client()
        other_client.login(email="other-bloom-user@example.com", password="testpass123")

        self.client.post("{}?mode=inline".format(self.url))
        other_get_response = other_client.get("{}?mode=inline".format(self.url))

        self.assertEqual(other_get_response.status_code, 404)
        mock_doc_api.return_value.create_doc.assert_called_once()
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

        with patch("nofos.views.docraptor.DocApi") as mock_doc_api:
            response = other_client.post(self.url)

        self.assertEqual(response.status_code, 403)
        mock_doc_api.assert_not_called()

    def test_login_required(self):
        anon_client = Client()
        response = anon_client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response["Location"])
