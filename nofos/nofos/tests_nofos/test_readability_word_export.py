from unittest.mock import call, patch

from bloom_nofos.tests_bloom_nofos.test_utils import VALID_DOCX
from bs4 import BeautifulSoup
from constance import config
from constance.test import override_config
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo
from nofos.tests_nofos.test_word_readability import synthetic_docx


@override_config(
    HHS_NOFO_METRICS_ENABLED=True,
    HHS_NOFO_READABILITY_WORD_EXPORT_ENABLED=True,
    HHS_NOFO_PDF_METRICS_PILOT_ENABLED=True,
)
@override_settings(
    GRABZIT_APPLICATION_KEY="synthetic-key",
    GRABZIT_APPLICATION_SECRET="synthetic-secret",
    GRABZIT_WORD_EXPORT_ALLOWED_HOSTS=("testserver",),
)
class ReadabilityWordExportTests(TestCase):
    def setUp(self):
        provider = patch("bloom_nofos.utils.GrabzItClient.GrabzItClient")
        self.grabzit = self.enterContext(provider).return_value
        self.grabzit.SaveTo.return_value = VALID_DOCX

    def test_signed_out_checker_converts_only_metrics_and_generic_scope(self):
        client = Client(enforce_csrf_checks=True)
        url = reverse("pdf_readability")
        client.get(url)
        csrf = client.cookies["csrftoken"].value
        results = client.post(
            url,
            {
                "pdf": SimpleUploadedFile(
                    "unpublished-opportunity.docx", synthetic_docx()
                ),
                "csrfmiddlewaretoken": csrf,
            },
        )
        self.assertContains(results, "Download Word")
        self.assertNotContains(results, "Print / Save as PDF")
        form = BeautifulSoup(results.content, "html.parser").select_one(
            "form[action$='/export-word/']"
        )
        token = form.select_one("input[name=report]")["value"]
        export_url = reverse("pdf_readability_word_export")
        self.assertEqual(client.post(export_url, {"report": token}).status_code, 403)
        response = client.post(
            export_url, {"report": token, "csrfmiddlewaretoken": csrf}
        )
        self.assertEqual(response.content, VALID_DOCX)
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="readability-metrics.docx"',
        )
        self.assertIn("no-store", response["Cache-Control"])
        html = self.grabzit.HTMLToDOCX.call_args.args[0]
        for metric in results.context["metric_rows"]:
            self.assertIn(metric["value"], html)
        self.assertIn("Tier 2 clearance metrics", html)
        self.assertIn("Tier 1 drafting measure", html)
        self.assertIn("recovered Word text", html)
        self.assertNotIn("unpublished-opportunity", html)
        self.assertNotIn("Opportunity number", html)
        self.assertNotIn("HRSA-26-106", html)
        self.assertIn("Your document was not saved.", html)
        self.assertNotIn("Applicants should submit a clear plan", html)
        self.assertEqual(
            self.grabzit.method_calls,
            [call.UseSSL(True), call.HTMLToDOCX(html), call.SaveTo()],
        )
        self.assertFalse(Nofo.objects.exists())

        config.HHS_NOFO_READABILITY_WORD_EXPORT_ENABLED = False
        self.grabzit.reset_mock()
        response = client.post(
            export_url, {"report": token, "csrfmiddlewaretoken": csrf}
        )
        self.assertEqual(response.status_code, 503)
        self.grabzit.HTMLToDOCX.assert_not_called()
        config.HHS_NOFO_READABILITY_WORD_EXPORT_ENABLED = True

        self.grabzit.SaveTo.return_value = b"invalid"
        response = client.post(
            export_url, {"report": token, "csrfmiddlewaretoken": csrf}
        )
        self.assertContains(
            response, "Word export could not be completed", status_code=502
        )
        self.assertNotIn("Content-Disposition", response)

    def test_signed_in_checker_download_is_rejected_after_logout(self):
        user = BloomUser.objects.create_user(
            email="logout@example.com", password="test-password", group="bloom"
        )
        self.client.force_login(user)
        page = self.client.post(
            reverse("pdf_readability"),
            {"pdf": SimpleUploadedFile("draft.docx", synthetic_docx())},
        )
        token = page.context["word_export_report"]
        self.assertTrue(token)
        self.client.logout()
        response = self.client.post(
            reverse("pdf_readability_word_export"), {"report": token}
        )
        self.assertEqual(response.status_code, 400)
        self.grabzit.HTMLToDOCX.assert_not_called()

    def test_signed_in_checker_report_adds_document_details(self):
        user = BloomUser.objects.create_user(
            email="checker@example.com", password="test-password", group="bloom"
        )
        signed_in = Client()
        signed_in.force_login(user)
        exports = []
        for client in (Client(), signed_in):
            page = client.post(
                reverse("pdf_readability"),
                {"pdf": SimpleUploadedFile("draft.docx", synthetic_docx())},
            )
            self.assertContains(page, "Download Word")
            # The identifier stays out of the rendered page for everyone.
            self.assertNotIn("opportunity_number", page.context["report"])
            response = client.post(
                reverse("pdf_readability_word_export"),
                {"report": page.context["word_export_report"]},
            )
            self.assertEqual(response.content, VALID_DOCX)
            exports.append(self.grabzit.HTMLToDOCX.call_args.args[0])
        signed_out_html, signed_in_html = exports

        self.assertIn("Your document was not saved.", signed_out_html)
        self.assertNotIn("draft.docx", signed_out_html)
        self.assertNotIn("HRSA-26-106", signed_out_html)
        self.assertNotIn("Opportunity number", signed_out_html)

        self.assertNotIn("Your document was not saved.", signed_in_html)
        self.assertNotIn("draft.docx", signed_in_html)
        self.assertIn("Assistance Listing number 93.123", signed_in_html)
        self.assertNotIn("93.123", signed_out_html)
        self.assertIn("Opportunity number HRSA-26-106", signed_in_html)
        self.assertNotIn("Not found", signed_in_html)
        self.assertNotIn("Not found", signed_out_html)

        # A recognized upload can have an Assistance Listing without an opportunity number.
        unnumbered = synthetic_docx(
            "Assistance listing: 93.123. Apply at Grants.gov. "
            "Applicants should submit a clear plan. The plan should describe needs."
        )
        for client in (signed_in, Client()):
            page = client.post(
                reverse("pdf_readability"),
                {"pdf": SimpleUploadedFile("draft.docx", unnumbered)},
            )
            client.post(
                reverse("pdf_readability_word_export"),
                {"report": page.context["word_export_report"]},
            )
            exports.append(self.grabzit.HTMLToDOCX.call_args.args[0])
        unnumbered_signed_in, unnumbered_signed_out = exports[2:]
        self.assertNotIn("draft.docx", unnumbered_signed_in)
        self.assertNotIn("Opportunity number", unnumbered_signed_in)
        self.assertIn("Assistance Listing number 93.123", unnumbered_signed_in)
        self.assertNotIn("Opportunity number", unnumbered_signed_out)
        self.assertIn("Your document was not saved.", unnumbered_signed_out)

        for html in exports[:2]:
            self.assertIn("Tier 2 clearance metrics", html)
            self.assertIn("Document check", html)
            # A thin rule separates the scores from the notes below them.
            self.assertLess(html.index("Tier 1 drafting measure"), html.index("<hr"))
            self.assertLess(html.index("<hr"), html.index("Document check"))
            self.assertIn("Recognized as a likely HHS NOFO: <strong>Yes</strong>", html)
            self.assertIn(
                "found an opportunity number and an Assistance Listing number", html
            )
            self.assertIn(
                "NOFO template structure: <strong>Couldn’t verify</strong>", html
            )
            self.assertNotIn("Applicants should submit a clear plan", html)

    def test_document_check_reports_recognized_template_parts(self):
        from nofos.readability_word_export import nofo_check

        word = {
            "nofo_signals": ["grants_gov", "hhs_nofo_template_context", "bogus"],
            "word_exclusions": {"cover_total": 12, "table_of_contents": 40},
        }
        check = nofo_check(word, "word")
        self.assertEqual(check["structure"], "Yes")
        self.assertIn("a cover page and a table of contents", check["structure_note"])
        self.assertIn(
            "a Grants.gov reference and HHS NOFO template wording",
            check["recognized_note"],
        )
        self.assertNotIn("bogus", check["recognized_note"])

        check = nofo_check({"word_exclusions": {"instruction": 0}}, "word")
        self.assertEqual(check["structure"], "Couldn’t verify")
        self.assertIn("basic HHS NOFO details", check["recognized_note"])

        self.assertEqual(nofo_check({}, "pdf")["structure"], "Couldn’t verify")
        self.assertEqual(nofo_check({}, "builder")["structure"], "Yes")

    def test_checker_report_uses_only_allowed_measurement_counts(self):
        from django.test import RequestFactory

        from nofos.readability_word_export import checker_report_token

        request = RequestFactory().get("/")
        report = {
            "profile": "word",
            "scope": {
                "recovered_word_count": 42,
                "sentence_word_count": 0,
                "complete_sentence_count": 0,
                "excluded_word_count": 42,
            },
            "word_exclusions": {"cover_total": 5, "instruction": "private text"},
            "coverage": "private text",
        }
        url = reverse("pdf_readability_word_export")
        self.client.post(url, {"report": checker_report_token(request, report)})
        html = self.grabzit.HTMLToDOCX.call_args.args[0]
        self.assertIn("42 recovered words", html)
        self.assertIn("0 words in 0 complete sentences", html)
        self.assertNotIn("Words skipped in recognized sections", html)
        self.assertNotIn("Cover pages: 5 words", html)
        self.assertNotIn("private text", html)

        report.update(
            profile="generic", pages_with_text=2, pages_analyzed=5, pages_total=5
        )
        self.client.post(url, {"report": checker_report_token(request, report)})
        html = self.grabzit.HTMLToDOCX.call_args.args[0]
        self.assertIn("2 of 5 pages contained extractable text", html)
        self.assertNotIn("Cover pages: 5 words", html)

    def test_builder_report_uses_panel_values_and_enforces_record_access(self):
        user = BloomUser.objects.create_user(
            email="editor@example.com",
            password="test-password",
            group="bloom",
            force_password_reset=False,
        )
        nofo = Nofo.objects.create(
            title="Synthetic Opportunity & Training",
            number="TEST-2026-01",
            opdiv="TEST",
            group="bloom",
            status="draft",
        )
        self.client.force_login(user)
        edit_url = reverse("nofos:nofo_edit", args=[nofo.pk])
        self.assertContains(self.client.get(edit_url), "data-readability-word-export")
        with override_config(HHS_NOFO_READABILITY_WORD_EXPORT_ENABLED=False):
            self.assertNotContains(
                self.client.get(edit_url), "data-readability-word-export"
            )
        payload = {
            "metrics": {
                "word_count": {"value": 1234},
                "words_per_sentence": {
                    "value": 13.495,
                    "components": {"sentences_per_paragraph": 2.45},
                },
            },
            "warnings": ["Private source excerpt"],
        }
        with patch(
            "nofos.views.record_readability_snapshot", return_value=(payload, None)
        ):
            metrics = self.client.post(
                reverse("nofos:nofo_readability_metrics", args=[nofo.pk])
            )
        self.assertEqual(metrics.json(), payload)
        token = metrics["X-Readability-Word-Report"]
        export_url = reverse("nofos:nofo_readability_word_export", args=[nofo.pk])
        response = self.client.post(export_url, {"report": token})
        self.assertEqual(response.content, VALID_DOCX)
        html = self.grabzit.HTMLToDOCX.call_args.args[0]
        self.assertIn("Synthetic Opportunity &amp; Training", html)
        self.assertIn("TEST-2026-01", html)
        self.assertIn("1,234", html)
        self.assertIn("13.5", html)
        self.assertIn("2.45", html)
        self.assertNotIn("Not found", html)
        self.assertIn("This NOFO was created in NOFO Builder.", html)
        self.assertNotIn("Your document was not saved.", html)
        self.assertNotIn("Private source excerpt", html)

        self.grabzit.reset_mock()
        noop = self.client.post(
            reverse("pdf_readability_word_export"), {"report": token}
        )
        self.assertEqual(noop.status_code, 400)
        another_user = BloomUser.objects.create_user(
            email="other@example.com",
            password="test-password",
            group="bloom",
            force_password_reset=False,
        )
        self.client.force_login(another_user)
        self.assertEqual(
            self.client.post(export_url, {"report": token}).status_code, 400
        )
        another_user.group = "hrsa"
        another_user.save()
        self.assertEqual(
            self.client.post(export_url, {"report": token}).status_code, 403
        )
        self.grabzit.HTMLToDOCX.assert_not_called()
