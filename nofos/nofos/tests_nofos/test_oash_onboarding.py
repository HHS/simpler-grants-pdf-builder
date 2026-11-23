from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.forms import NofoThemeOptionsForm
from nofos.models import Nofo
from nofos.nofo import suggest_nofo_theme
from nofos.tests_nofos.test_introductory_page import introductory_docx


class OashOnboardingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = BloomUser.objects.create_user(
            email="oash@example.test",
            password=None,
            group="oash",
            force_password_reset=False,
        )
        cls.outsider = BloomUser.objects.create_user(
            email="cdc@example.test",
            password=None,
            group="cdc",
            force_password_reset=False,
        )
        cls.bloom = BloomUser.objects.create_user(
            email="bloom@example.test",
            password=None,
            group="bloom",
            force_password_reset=False,
        )

    def test_group_import_uses_oash_defaults_and_warns_about_source_opdiv(self):
        self.client.force_login(self.editor)
        with patch("nofos.nofo.suggest_nofo_cover_image") as suggest_image:
            response = self.client.post(
                reverse("nofos:nofo_import"),
                {
                    "nofo-import": SimpleUploadedFile(
                        "notice.docx",
                        introductory_docx(number="CDC-RFA-27-001", opdiv="CDC"),
                        content_type=(
                            "application/vnd.openxmlformats-officedocument."
                            "wordprocessingml.document"
                        ),
                    )
                },
                follow=True,
            )
        suggest_image.assert_not_called()
        self.assertContains(response, "NOFO Builder applied the OASH theme")
        nofo = Nofo.objects.get()
        self.assertEqual(nofo.group, "oash")
        self.assertEqual(nofo.theme, "portrait-oash-navy")
        self.assertEqual(nofo.cover, "nofo--cover-page--text")
        url = reverse("nofos:nofo_view", args=[nofo.pk])
        self.assertContains(
            self.client.get(url), "Office of the Assistant Secretary for Health"
        )
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.bloom)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_opdiv_recognition_beats_opportunity_number_heuristics(self):
        for opdiv in ("OASH", "Office of the Assistant Secretary for Health"):
            with self.subTest(opdiv=opdiv):
                self.assertEqual(
                    suggest_nofo_theme("RFA-FD-27-001", opdiv), "portrait-oash-navy"
                )
        self.assertEqual(
            suggest_nofo_theme("RFA-FD-27-001", "AOASH"), "portrait-fda-blue"
        )

    def test_oash_theme_picker_accepts_supported_options(self):
        nofo = Nofo(group="oash", theme="portrait-oash-navy", title="Synthetic notice")
        data = {
            "theme": "portrait-oash-navy",
            "cover": "nofo--cover-page--medium",
            "icon_style": "nofo--icons--border",
        }
        self.assertTrue(
            NofoThemeOptionsForm(data, user=self.editor, instance=nofo).is_valid()
        )
        data["theme"] = "portrait-fda-blue"
        form = NofoThemeOptionsForm(data, user=self.editor, instance=nofo)
        self.assertIn("theme", form.errors)
