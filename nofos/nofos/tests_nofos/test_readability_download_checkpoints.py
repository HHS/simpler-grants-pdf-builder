from unittest.mock import patch

import docraptor
from constance.test import override_config
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, NofoReadabilityCheckpoint
from nofos.readability import (
    ReadabilityMetricsAnalysisError,
    save_readability_checkpoint,
)
from nofos.tests_nofos.test_readability_metrics import build_payload

HINT = "Downloading also saves a readability snapshot."


@override_config(HHS_NOFO_METRICS_ENABLED=True)
class ReadabilityDownloadCheckpointTests(TestCase):
    def setUp(self):
        for target in (
            "nofos.readability.get_metrics_package_version",
            "nofos.readability_history.get_metrics_package_version",
        ):
            version_patch = patch(target, return_value="0.5.2")
            version_patch.start()
            self.addCleanup(version_patch.stop)
        analyze_patch = patch(
            "nofos.readability.analyze_nofo_readability", return_value=build_payload()
        )
        self.analyze = analyze_patch.start()
        self.addCleanup(analyze_patch.stop)
        docraptor_patch = patch("nofos.pdf_service.docraptor.DocApi")
        self.doc_api = docraptor_patch.start()
        self.addCleanup(docraptor_patch.stop)
        self.doc_api.return_value.create_doc.return_value = b"%PDF-1.4 fake pdf"

        self.user = BloomUser.objects.create_user(
            email="downloader@example.com",
            password="test",
            group="hrsa",
            force_password_reset=False,
        )
        self.client.force_login(self.user)
        self.nofo = Nofo.objects.create(
            title="Synthetic download", number="TEST-DL-1", group="hrsa", opdiv="HRSA"
        )
        self.print_url = reverse("nofos:print_pdf", kwargs={"pk": self.nofo.pk})

    def download(self):
        return self.client.post(self.print_url + "?mode=attachment&is_test_pdf=false")

    def preview(self):
        return self.client.post(self.print_url + "?mode=inline")

    def checkpoints(self):
        return NofoReadabilityCheckpoint.objects.filter(score__nofo=self.nofo)

    def edit_nofo(self):
        self.nofo.refresh_from_db()
        self.nofo.title = self.nofo.title + " (edited)"
        self.nofo.save()

    def test_download_saves_a_download_checkpoint(self):
        response = self.download()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"%PDF-1.4 fake pdf")
        checkpoint = self.checkpoints().get()
        self.assertEqual(checkpoint.trigger, NofoReadabilityCheckpoint.TRIGGER_DOWNLOAD)
        self.assertEqual(checkpoint.saved_by, self.user)

    def test_preview_and_test_downloads_do_not_save(self):
        self.assertEqual(self.preview().status_code, 200)
        self.client.post(self.print_url + "?mode=attachment&is_test_pdf=true")

        self.assertFalse(self.checkpoints().exists())
        self.analyze.assert_not_called()

    def test_unchanged_nofo_does_not_save_again(self):
        self.download()
        self.download()
        self.assertEqual(self.checkpoints().count(), 1)

        self.edit_nofo()
        self.download()

        self.assertEqual(self.checkpoints().count(), 2)
        self.assertTrue(
            all(c.trigger == "download" for c in self.checkpoints()),
        )

    def test_download_after_a_manual_save_keeps_the_manual_checkpoint(self):
        save_readability_checkpoint(self.nofo, self.user)

        self.download()

        checkpoint = self.checkpoints().get()
        self.assertEqual(checkpoint.trigger, NofoReadabilityCheckpoint.TRIGGER_MANUAL)

    def test_failed_pdf_generation_saves_nothing(self):
        self.doc_api.return_value.create_doc.side_effect = docraptor.rest.ApiException(
            status=422, reason="Unprocessable Entity"
        )

        with self.assertLogs("django.request", level="ERROR"):
            response = self.download()

        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.checkpoints().exists())

    def test_metrics_failure_still_downloads_the_pdf(self):
        self.analyze.side_effect = ReadabilityMetricsAnalysisError(
            {"message": "rejected"}
        )

        response = self.download()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"%PDF-1.4 fake pdf")
        self.assertFalse(self.checkpoints().exists())

    @override_config(HHS_NOFO_METRICS_ENABLED=False)
    def test_disabled_metrics_save_nothing_and_hide_the_hint(self):
        self.download()

        self.assertFalse(self.checkpoints().exists())
        for url_name in ("nofos:nofo_edit", "nofos:nofo_view"):
            response = self.client.get(reverse(url_name, kwargs={"pk": self.nofo.pk}))
            self.assertNotContains(response, HINT)
            self.assertNotContains(response, "download-pdf-readability-hint")

    def test_hint_is_shown_and_announced_with_the_download_button(self):
        for url_name in ("nofos:nofo_edit", "nofos:nofo_view"):
            response = self.client.get(reverse(url_name, kwargs={"pk": self.nofo.pk}))
            self.assertContains(response, HINT)
            self.assertContains(
                response, 'aria-describedby="download-pdf-readability-hint"'
            )

    def test_panel_history_and_overview_describe_download_saves(self):
        self.download()
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_builder_metrics")
        )

        edit = self.client.get(reverse("nofos:nofo_edit", kwargs={"pk": self.nofo.pk}))
        history = self.client.get(
            reverse("nofos:nofo_readability_history", kwargs={"pk": self.nofo.pk})
        )
        overview = self.client.get(reverse("nofos:builder_metrics_readability_scores"))

        self.assertContains(edit, "automatically on PDF download")
        self.assertContains(edit, "when the PDF was downloaded")
        self.assertContains(edit, "Automatic &middot; on PDF download")
        self.assertContains(edit, "downloader@example.com downloaded the PDF.")
        self.assertContains(history, "Automatic, on PDF download")
        self.assertContains(overview, "Automatic, on PDF download")

    def test_saving_after_a_download_reports_the_automatic_checkpoint(self):
        self.download()

        response = self.client.post(
            reverse("nofos:nofo_readability_metrics_save", kwargs={"pk": self.nofo.pk})
        )

        payload = response.json()
        self.assertTrue(payload["already_saved"])
        self.assertEqual(payload["checkpoint"]["trigger"], "download")
        self.assertEqual(
            payload["checkpoint"]["trigger_event"], "the PDF was downloaded"
        )
