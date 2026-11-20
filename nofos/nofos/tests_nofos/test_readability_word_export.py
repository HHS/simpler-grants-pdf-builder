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
