from unittest.mock import patch

from constance.test import override_config
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, NofoReadabilityCheckpoint
from nofos.readability import (
    ReadabilityMetricsAnalysisError,
    ReadabilityMetricsUnavailable,
)
from nofos.tests_nofos.test_readability_metrics import build_payload

AUTOMATIC_SAVE_MESSAGE = "Readability metrics were saved automatically"


def upload(name="Program", body="Applicants must submit a plan."):
    html = f"<p>Opdiv: HRSA</p><h1>{name}</h1><p>{body}</p>"
    return SimpleUploadedFile("nofo.html", html.encode(), content_type="text/html")


@override_config(HHS_NOFO_METRICS_ENABLED=True)
class ReadabilityImportCheckpointTests(TestCase):
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
        self.user = BloomUser.objects.create_user(
            email="importer@example.com",
            password="test",
            group="hrsa",
            force_password_reset=False,
        )
        self.client.force_login(self.user)

    def import_nofo(self):
        response = self.client.post(
            reverse("nofos:nofo_import"), {"nofo-import": upload()}
        )
        self.assertEqual(response.status_code, 302)
        return Nofo.objects.latest("created")

    def reimport(self, nofo):
        return self.client.post(
            reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk}),
            {"nofo-import": upload(body="Applicants submit a plan.")},
        )

    def messages_for(self, response):
        return [str(message) for message in get_messages(response.wsgi_request)]

    def test_new_import_saves_an_automatic_import_checkpoint(self):
        nofo = self.import_nofo()

        checkpoint = NofoReadabilityCheckpoint.objects.get(score__nofo=nofo)
        self.assertEqual(checkpoint.trigger, NofoReadabilityCheckpoint.TRIGGER_IMPORT)
        self.assertEqual(checkpoint.saved_by, self.user)
        self.assertEqual(checkpoint.score.nofo_revision, nofo.updated)

    def test_reimport_saves_a_reimport_checkpoint_and_says_so(self):
        nofo = self.import_nofo()

        response = self.reimport(nofo)

        self.assertRedirects(
            response,
            reverse("nofos:nofo_edit", kwargs={"pk": nofo.pk}),
            fetch_redirect_response=False,
        )
        triggers = list(
            NofoReadabilityCheckpoint.objects.filter(score__nofo=nofo).values_list(
                "trigger", flat=True
            )
        )
        self.assertEqual(triggers, ["reimport", "import"])
        self.assertIn(AUTOMATIC_SAVE_MESSAGE, " ".join(self.messages_for(response)))

    def test_import_succeeds_without_a_checkpoint_when_metrics_fail(self):
        for error in (
            ReadabilityMetricsUnavailable("not installed"),
            ReadabilityMetricsAnalysisError({"message": "rejected"}),
        ):
            with self.subTest(error=type(error).__name__):
                self.analyze.side_effect = error
                nofo = self.import_nofo()
                response = self.reimport(nofo)

                self.assertEqual(response.status_code, 302)
                self.assertFalse(
                    NofoReadabilityCheckpoint.objects.filter(score__nofo=nofo).exists()
                )
                messages = " ".join(self.messages_for(response))
                self.assertIn("Re-imported NOFO from file", messages)
                self.assertNotIn(AUTOMATIC_SAVE_MESSAGE, messages)

    @override_config(HHS_NOFO_METRICS_ENABLED=False)
    def test_disabled_metrics_save_nothing_on_import_or_reimport(self):
        nofo = self.import_nofo()
        response = self.reimport(nofo)

        self.analyze.assert_not_called()
        self.assertFalse(NofoReadabilityCheckpoint.objects.exists())
        self.assertNotIn(AUTOMATIC_SAVE_MESSAGE, " ".join(self.messages_for(response)))

    def test_manual_saves_are_recorded_as_manual(self):
        nofo = self.import_nofo()
        nofo.title = "Edited"
        nofo.save()

        response = self.client.post(
            reverse("nofos:nofo_readability_metrics_save", kwargs={"pk": nofo.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checkpoint"]["trigger"], "manual")
        self.assertFalse(response.json()["checkpoint"]["is_automatic"])
        latest = NofoReadabilityCheckpoint.objects.filter(score__nofo=nofo).first()
        self.assertEqual(latest.trigger, NofoReadabilityCheckpoint.TRIGGER_MANUAL)

    def test_saving_unchanged_nofo_reports_the_automatic_checkpoint(self):
        nofo = self.import_nofo()

        response = self.client.post(
            reverse("nofos:nofo_readability_metrics_save", kwargs={"pk": nofo.pk})
        )

        payload = response.json()
        self.assertTrue(payload["already_saved"])
        self.assertEqual(payload["checkpoint"]["trigger"], "import")
        self.assertEqual(NofoReadabilityCheckpoint.objects.count(), 1)

    def test_edit_panel_describes_the_latest_save_and_explains_automatic_saves(self):
        nofo = self.import_nofo()
        edit_url = reverse("nofos:nofo_edit", kwargs={"pk": nofo.pk})

        response = self.client.get(edit_url)

        self.assertContains(response, "automatically on import")
        self.assertContains(response, "data-auto-save-notice")
        self.assertContains(response, "Automatic &middot; on import")
        self.assertNotContains(response, "Not calculated</span>")

        nofo.title = "Edited"
        nofo.save()
        self.client.post(
            reverse("nofos:nofo_readability_metrics_save", kwargs={"pk": nofo.pk})
        )
        response = self.client.get(edit_url)

        self.assertNotContains(response, "data-auto-save-notice")
        self.assertNotContains(response, "automatically on import</span>")
        self.assertContains(response, "Last saved")

    def test_edit_panel_without_saves_says_not_calculated(self):
        nofo = Nofo.objects.create(title="No saves", group="hrsa", opdiv="HRSA")

        response = self.client.get(reverse("nofos:nofo_edit", kwargs={"pk": nofo.pk}))

        self.assertContains(response, "Not calculated</span>")
        self.assertNotContains(response, "data-auto-save-notice")

    def test_history_and_overview_label_automatic_checkpoints(self):
        nofo = self.import_nofo()
        self.reimport(nofo)
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_builder_metrics")
        )

        history = self.client.get(
            reverse("nofos:nofo_readability_history", kwargs={"pk": nofo.pk})
        )
        overview = self.client.get(reverse("nofos:builder_metrics_readability_scores"))

        self.assertContains(history, "Automatic, on import")
        self.assertContains(history, "Automatic, on re-import")
        self.assertContains(overview, "Automatic, on re-import")
