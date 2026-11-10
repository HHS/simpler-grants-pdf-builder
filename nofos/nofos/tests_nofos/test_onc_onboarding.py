from bs4 import BeautifulSoup
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.forms import NofoThemeOptionsForm
from nofos.models import Nofo
from nofos.nofo_document_context import get_nofo_document_context
from nofos.tests_nofos.test_introductory_page import introductory_docx


class ONCOnboardingTests(TestCase):
    logo_alt = (
        "Office of the National Coordinator for Health Information Technology logo"
    )

    @classmethod
    def setUpTestData(cls):
        for group in ("bloom", "onc", "cdc"):
            user = BloomUser.objects.create_user(
                email=f"{group}@example.test",
                password="Synthetic-test-password-27!",
                group=group,
                is_superuser=(group == "bloom"),
                is_staff=(group == "bloom"),
                force_password_reset=False,
            )
            setattr(cls, group, user)

    def test_superuser_can_create_an_onc_account(self):
        self.client.force_login(self.bloom)
        password = "Another-synthetic-password-27!"
        response = self.client.post(
            reverse("users:user_team_create"),
            {
                "email": "onc-new@example.test",
                "full_name": "Synthetic ONC user",
                "group": "onc",
                "password1": password,
                "password2": password,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            BloomUser.objects.get(email="onc-new@example.test").group, "onc"
        )
        self.client.logout()
        self.assertTrue(
            self.client.login(username="onc-new@example.test", password=password)
        )

    def test_word_import_and_group_visibility(self):
        self.client.force_login(self.onc)
        response = self.client.post(
            reverse("nofos:nofo_import"),
            {
                "nofo-import": SimpleUploadedFile(
                    "synthetic.docx",
                    introductory_docx(number="CDC-TEST-001"),
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        self.assertEqual(response.status_code, 302)
        nofo = Nofo.objects.get()
        self.assertEqual(nofo.group, "onc")
        self.assertEqual(nofo.theme, "portrait-onc-navy")
        self.assertEqual(nofo.cover, "nofo--cover-page--text")
        cdc_nofo = Nofo.objects.create(group="cdc", title="Separate group", opdiv="CDC")
        peer = BloomUser.objects.create_user(
            email="onc-peer@example.test",
            password="Synthetic-27!",
            group="onc",
            force_password_reset=False,
        )
        self.client.force_login(peer)
        self.assertQuerySetEqual(
            self.client.get(reverse("nofos:nofo_index")).context["nofo_list"], [nofo]
        )
        view_url = reverse("nofos:nofo_view", args=[nofo.pk])
        self.assertContains(self.client.get(view_url), self.logo_alt)
        self.assertEqual(
            self.client.get(reverse("nofos:nofo_view", args=[cdc_nofo.pk])).status_code,
            403,
        )
        self.client.force_login(self.cdc)
        self.assertNotIn(
            nofo, self.client.get(reverse("nofos:nofo_index")).context["nofo_list"]
        )
        self.assertEqual(self.client.get(view_url).status_code, 403)
        self.client.force_login(self.bloom)
        self.assertContains(self.client.get(view_url), self.logo_alt)
        theme_url = reverse("nofos:nofo_edit_theme_options", args=[nofo.pk])
        self.client.force_login(self.onc)
        theme_soup = BeautifulSoup(self.client.get(theme_url).content, "html.parser")
        self.assertEqual(
            [option["value"] for option in theme_soup.select("select#theme option")],
            ["portrait-onc-navy"],
        )

        for cover in ("nofo--cover-page--text", "nofo--cover-page--medium"):
            with self.subTest(cover=cover):
                nofo.cover = cover
                context = {
                    "nofo": nofo,
                    "object": nofo,
                    **get_nofo_document_context(nofo),
                }
                pdf_source = render_to_string("nofos/nofo_pdf.html", context)
                logo = BeautifulSoup(pdf_source, "html.parser").select_one(
                    "#section--cover-page .onc-cover-logo"
                )
                self.assertIsNotNone(logo)
                self.assertEqual(logo["alt"], self.logo_alt)
                self.assertTrue(logo["src"].endswith("/img/onc-logo-inverse.png"))
                self.assertIn(cover, pdf_source)
                self.assertIn("theme-opdiv-onc-navy.css", pdf_source)

    def test_theme_form_restricts_choices_and_allows_standard_image(self):
        nofo = Nofo(
            title="Synthetic ONC NOFO",
            opdiv="ONC",
            group="onc",
            theme="portrait-onc-navy",
        )
        for user in (self.onc, self.bloom):
            data = {
                "theme": "portrait-onc-navy",
                "cover": "nofo--cover-page--medium",
                "icon_style": "nofo--icons--solid",
            }
            form = NofoThemeOptionsForm(data, user=user, instance=nofo)
            self.assertTrue(form.is_valid(), form.errors)
            invalid = {
                **data,
                "theme": "portrait-cdc-blue",
                "cover": "nofo--cover-page--hero",
                "icon_style": "nofo--icons--thin",
            }
            form = NofoThemeOptionsForm(invalid, user=user, instance=nofo)
            self.assertFalse(form.is_valid())
            expected_errors = {"cover", "icon_style"}
            if user == self.onc:
                expected_errors.add("theme")
            self.assertEqual(set(form.errors), expected_errors)

    def test_onc_theme_is_not_selectable_on_another_groups_record(self):
        nofo = Nofo(title="Another record", opdiv="CDC", group="cdc")
        data = {
            "theme": "portrait-onc-navy",
            "cover": "nofo--cover-page--text",
            "icon_style": "nofo--icons--solid",
        }
        for user in (self.onc, self.cdc):
            with self.subTest(group=user.group):
                form = NofoThemeOptionsForm(data, user=user, instance=nofo)
                self.assertFalse(form.is_valid())
                self.assertIn("theme", form.errors)

    def test_bloom_can_select_onc_theme_across_groups(self):
        for group in ("onc", "cdc"):
            with self.subTest(group=group):
                nofo = Nofo(
                    title="Synthetic notice", group=group, theme="portrait-cdc-blue"
                )
                form = NofoThemeOptionsForm(
                    {
                        "theme": "portrait-onc-navy",
                        "cover": "nofo--cover-page--text",
                        "icon_style": "nofo--icons--solid",
                    },
                    user=self.bloom,
                    instance=nofo,
                )
                self.assertTrue(form.is_valid(), form.errors)
                themes = {
                    value
                    for _, options in form.fields["theme"].choices
                    for value, _ in options
                }
                self.assertIn("portrait-cdc-blue", themes)
