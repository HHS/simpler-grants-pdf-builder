from unittest.mock import patch

from bs4 import BeautifulSoup
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.forms import NofoThemeOptionsForm
from nofos.models import Nofo
from nofos.nofo import suggest_all_nofo_fields, suggest_nofo_theme
from nofos.nofo_document_context import get_nofo_document_context
from nofos.tests_nofos.test_introductory_page import introductory_docx


class FDAOnboardingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for group in ("bloom", "fda", "cdc"):
            user = BloomUser.objects.create_user(
                email=f"{group}@example.test",
                password="Synthetic-test-password-27!",
                group=group,
                is_superuser=group == "bloom",
                is_staff=group == "bloom",
                force_password_reset=False,
            )
            setattr(cls, group, user)

    def test_superuser_can_create_fda_user_who_can_sign_in(self):
        self.client.force_login(self.bloom)
        password = "Another-synthetic-password-27!"
        email = "fda-new@example.test"
        response = self.client.post(
            reverse("users:user_team_create"),
            {
                "email": email,
                "full_name": "Synthetic FDA editor",
                "group": "fda",
                "password1": password,
                "password2": password,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BloomUser.objects.get(email=email).group, "fda")
        self.client.logout()
        self.assertTrue(self.client.login(username=email, password=password))

    def test_word_import_uses_editor_group_and_preserves_access_boundaries(self):
        self.client.force_login(self.fda)
        response = self.client.post(
            reverse("nofos:nofo_import"),
            {
                "nofo-import": SimpleUploadedFile(
                    "synthetic.docx",
                    introductory_docx(number="RFA-FD-26-001"),
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        self.assertEqual(response.status_code, 302)
        imported = Nofo.objects.get()
        self.assertEqual(imported.group, "fda")
        self.assertEqual(imported.theme, "portrait-fda-blue")
        self.assertEqual(imported.cover, "nofo--cover-page--text")
        separate = Nofo.objects.create(group="cdc", title="CDC notice", opdiv="CDC")
        index = reverse("nofos:nofo_index")
        imported_view = reverse("nofos:nofo_view", args=[imported.pk])
        separate_view = reverse("nofos:nofo_view", args=[separate.pk])
        peer = BloomUser.objects.create_user(
            email="fda-peer@example.test",
            password=None,
            group="fda",
            force_password_reset=False,
        )

        self.client.force_login(peer)
        self.assertQuerySetEqual(
            self.client.get(index).context["nofo_list"], [imported]
        )
        self.assertEqual(self.client.get(imported_view).status_code, 200)
        self.assertEqual(self.client.get(separate_view).status_code, 403)

        self.client.force_login(self.cdc)
        self.assertNotIn(imported, self.client.get(index).context["nofo_list"])
        self.assertEqual(self.client.get(imported_view).status_code, 403)

        self.client.force_login(self.bloom)
        self.assertEqual(self.client.get(imported_view).status_code, 200)

    def test_conflicting_word_opdiv_keeps_group_theme_and_warns_editor(self):
        cases = (
            (self.cdc, "FDA", "RFA-FD-26-001", "portrait-cdc-blue"),
            (self.fda, "CDC", "CDC-RFA-DP-26-0012", "portrait-fda-blue"),
        )
        for user, opdiv, number, theme in cases:
            with self.subTest(group=user.group):
                self.client.force_login(user)
                response = self.client.post(
                    reverse("nofos:nofo_import"),
                    {
                        "nofo-import": SimpleUploadedFile(
                            "synthetic.docx",
                            introductory_docx(number=number, opdiv=opdiv),
                            content_type=(
                                "application/vnd.openxmlformats-officedocument."
                                "wordprocessingml.document"
                            ),
                        )
                    },
                    follow=True,
                )
                self.assertContains(
                    response, f"The document’s OpDiv identifies {opdiv}."
                )
                nofo = Nofo.objects.get(group=user.group)
                self.assertEqual(nofo.opdiv, opdiv)
                self.assertEqual(nofo.theme, theme)
                self.assertEqual(nofo.cover, "nofo--cover-page--text")

    def test_theme_match_does_not_change_cdc_fallback(self):
        for opdiv, number, expected in (
            ("Food and Drug Administration", "", "fda-blue"),
            ("Food & Drug Administration", "TEMPLATE", "fda-blue"),
            ("FDA", "RFA-FD-26-001", "fda-blue"),
            ("", "RFA-FD-26-001", "fda-blue"),
            ("", "PAR-FD-26-002", "fda-blue"),
            ("", "CDC-RFA-FD-26-0012", "cdc-blue"),
            ("Centers for Disease Control and Prevention", "RFA-FD-26-001", "cdc-blue"),
            ("CDC", "", "cdc-blue"),
            ("AFDA", "RFA-XX-26-001", "cdc-blue"),
            ("ACF", "RFA-FD-26-001", "acf-white"),
        ):
            with self.subTest(opdiv=opdiv, number=number):
                self.assertEqual(
                    suggest_nofo_theme(number, opdiv), f"portrait-{expected}"
                )

    def test_group_default_only_applies_on_first_import(self):
        soup = BeautifulSoup(
            "<p>OpDiv: CDC</p><p>Opportunity number: CDC-RFA-DP-26-0012</p>",
            "html.parser",
        )
        nofo = Nofo(group="fda")
        suggest_all_nofo_fields(nofo, soup, first_time_import=True)
        self.assertEqual(nofo.theme, "portrait-fda-blue")
        self.assertEqual(nofo.cover, "nofo--cover-page--text")
        nofo.theme = "portrait-cdc-blue"
        nofo.cover = "nofo--cover-page--medium"
        nofo.icon_style = "nofo--icons--border"
        suggest_all_nofo_fields(nofo, soup, first_time_import=False)
        self.assertEqual(nofo.theme, "portrait-cdc-blue")
        self.assertEqual(nofo.cover, "nofo--cover-page--medium")
        self.assertEqual(nofo.icon_style, "nofo--icons--border")

    def test_theme_form_restricts_fda_choices_without_restricting_bloom(self):
        data = {
            "theme": "portrait-fda-blue",
            "cover": "nofo--cover-page--medium",
            "icon_style": "nofo--icons--border",
        }
        for user, group, valid in (
            (self.fda, "fda", True),
            (self.bloom, "cdc", True),
            (self.cdc, "cdc", False),
        ):
            with self.subTest(user=user.group, group=group):
                form = NofoThemeOptionsForm(
                    data,
                    user=user,
                    instance=Nofo(group=group, title="Synthetic notice"),
                )
                self.assertEqual(form.is_valid(), valid, form.errors)
        form = NofoThemeOptionsForm(
            {
                "theme": "portrait-cdc-blue",
                "cover": "nofo--cover-page--hero",
                "icon_style": "nofo--icons--thin",
            },
            user=self.fda,
            instance=Nofo(group="fda", title="Synthetic notice"),
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(set(form.errors), {"theme", "cover", "icon_style"})

    def test_standard_cover_uses_the_uploaded_image(self):
        nofo = Nofo.objects.create(
            group="fda",
            theme="portrait-fda-blue",
            cover="nofo--cover-page--medium",
            title="Synthetic FDA notice",
            opdiv="FDA",
        )
        self.client.force_login(self.fda)
        key = "img/cover-img/synthetic.png"
        image_url = "https://example.test/synthetic.png"
        with patch("nofos.nofo.upload_file_to_s3", return_value=key):
            response = self.client.post(
                reverse("nofos:nofo_upload_cover_image", args=[nofo.pk]),
                {
                    "cover_image": SimpleUploadedFile(
                        "synthetic.png", b"fixture", content_type="image/png"
                    ),
                    "cover_image_alt_text": "Synthetic cover artwork",
                },
            )
        self.assertRedirects(
            response,
            reverse("nofos:nofo_edit", args=[nofo.pk]),
            fetch_redirect_response=False,
        )
        nofo.refresh_from_db()
        self.assertEqual(nofo.cover_image, key)
        with patch("nofos.nofo.get_image_url_from_s3", return_value=image_url):
            response = self.client.get(reverse("nofos:nofo_view", args=[nofo.pk]))
        self.assertContains(response, image_url)
        self.assertContains(response, 'alt="Synthetic cover artwork"')

    def test_both_pdf_cover_sources_use_fda_logo(self):
        for cover in ("text", "medium"):
            with self.subTest(cover=cover):
                nofo = Nofo.objects.create(
                    group="fda",
                    theme="portrait-fda-blue",
                    cover=f"nofo--cover-page--{cover}",
                    title="Synthetic FDA notice",
                    opdiv="FDA",
                    agency="U.S. Food and Drug Administration",
                )
                html = render_to_string(
                    "nofos/nofo_pdf.html",
                    {"nofo": nofo, **get_nofo_document_context(nofo)},
                )
                soup = BeautifulSoup(html, "html.parser")
                cover_html = soup.select_one("#section--cover-page")
                self.assertEqual(
                    cover_html.select_one("img.fda-cover-logo")["alt"],
                    "U.S. Food and Drug Administration logo",
                )
                self.assertIsNone(
                    cover_html.select_one(".nofo--cover-page--hero-image")
                )
                self.assertIsNone(
                    cover_html.select_one(".nofo--cover-page--footer--image img")
                )
                self.assertIn(nofo.agency, cover_html.get_text())
                self.assertIn("theme-opdiv-fda-blue.css", html)
