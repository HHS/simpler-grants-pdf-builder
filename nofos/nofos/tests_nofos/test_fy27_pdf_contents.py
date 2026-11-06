from unittest.mock import patch

from bs4 import BeautifulSoup
from constance.test import override_config
from django.test import TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.forms import NofoThemeOptionsForm
from nofos.models import Nofo, Section, Subsection
from nofos.pdf_service import generate_nofo_pdf


class Fy27PdfContentsTests(TestCase):
    def setUp(self):
        self.nofo = Nofo.objects.create(
            title="Synthetic FY27 NOFO",
            number="TEST-27-001",
            group="bloom",
            opdiv="IHS",
            theme="portrait-ihs-white",
            icon_style="nofo--icons--solid",
            introductory_page_family="get_started",
        )
        step = Section.objects.create(
            nofo=self.nofo,
            name='Step 1: Review "this" opportunity',
            html_id="review",
            order=1,
        )
        for order, name in enumerate(("Eligibility", "Key dates"), 1):
            Subsection.objects.create(
                section=step,
                name=name,
                html_id=f"review--{order}",
                order=order,
                tag="h3",
                body="Synthetic fixture content.",
            )
        self.user = BloomUser.objects.create_user(
            email="editor@example.test",
            password=None,
            group="bloom",
            force_password_reset=False,
        )

    def pdf_document(self):
        with patch("nofos.pdf_service.docraptor.DocApi") as provider:
            provider.return_value.create_doc.return_value = b"%PDF"
            generate_nofo_pdf(
                self.nofo, base_url="https://example.test/nofo", is_test_pdf=True
            )
            html = provider.return_value.create_doc.call_args.args[0][
                "document_content"
            ]
        return BeautifulSoup(html, "html.parser")

    @override_config(HHS_NOFO_FY27_PDF_CONTENTS_ENABLED=True)
    def test_new_pdf_modes_keep_cover_order_and_same_individual_links(self):
        columns = self.pdf_document()
        self.nofo.pdf_contents_layout = Nofo.PdfContentsLayout.SINGLE
        single = self.pdf_document()

        def contents_links(soup):
            return [
                (link.get_text(strip=True), link["href"])
                for link in soup.select("#section--toc a")
            ]

        self.assertEqual(contents_links(columns), contents_links(single))
        self.assertEqual(
            contents_links(single),
            [
                ("Before you get started", "#section--before-you-begin"),
                ('Step 1: Review "this" opportunity', "#review"),
                ("Eligibility", "#review--1"),
                ("Key dates", "#review--2"),
            ],
        )
        for soup, layout in ((columns, "columns"), (single, "single")):
            with self.subTest(layout=layout):
                self.assertEqual(
                    soup.select_one("#section--cover-page").find_next_sibling(
                        "section"
                    )["id"],
                    "section--toc",
                )
                self.assertIn(f"toc--fy27-{layout}", soup.select_one(".toc")["class"])
                self.assertIsNotNone(
                    soup.select_one(
                        'link[href$="theme-fy27-pdf-contents.css"][media="print"]'
                    )
                )
        self.assertFalse(columns.select("[data-contents-step]"))
        self.assertEqual(
            [
                tag["data-contents-step"]
                for tag in single.select("[data-contents-step]")
            ],
            ['Step 1: Review "this" opportunity'] * 2,
        )

    @override_config(HHS_NOFO_FY27_PDF_CONTENTS_ENABLED=True)
    def test_html_and_legacy_and_landscape_pdf_keep_their_layouts(self):
        self.client.force_login(self.user)
        page = self.client.get(reverse("nofos:nofo_view", args=[self.nofo.pk]))
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, "toc--fy27-")
        self.assertNotContains(page, "theme-fy27-pdf-contents.css")
        for family, theme in (
            ("legacy", "portrait-ihs-white"),
            ("", "portrait-ihs-white"),
            ("get_started", "landscape-cdc-blue"),
        ):
            with self.subTest(family=family, theme=theme):
                self.nofo.introductory_page_family = family
                self.nofo.theme = theme
                document = self.pdf_document()
                self.assertIsNone(document.select_one('[class*="toc--fy27-"]'))
                self.assertIsNone(
                    document.select_one('link[href$="theme-fy27-pdf-contents.css"]')
                )

    @override_config(HHS_NOFO_FY27_PDF_CONTENTS_ENABLED=True)
    def test_save_choice_and_turn_off_at_runtime_without_losing_it(self):
        data = {
            "theme": self.nofo.theme,
            "cover": self.nofo.cover,
            "icon_style": self.nofo.icon_style,
            "pdf_contents_layout": Nofo.PdfContentsLayout.SINGLE,
        }
        form = NofoThemeOptionsForm(data, instance=self.nofo, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertIsNotNone(self.pdf_document().select_one(".toc--fy27-single"))
        with override_config(HHS_NOFO_FY27_PDF_CONTENTS_ENABLED=False):
            form = NofoThemeOptionsForm(data, instance=self.nofo, user=self.user)
            self.assertNotIn("pdf_contents_layout", form.fields)
            self.assertIsNone(self.pdf_document().select_one(".toc--fy27-single"))
        self.nofo.refresh_from_db()
        self.assertEqual(self.nofo.pdf_contents_layout, Nofo.PdfContentsLayout.SINGLE)

    def test_theme_screen_only_offers_layout_when_enabled_for_fy27(self):
        self.client.force_login(self.user)
        url = reverse("nofos:nofo_edit_theme_options", args=[self.nofo.pk])
        with override_config(HHS_NOFO_FY27_PDF_CONTENTS_ENABLED=False):
            self.assertNotContains(self.client.get(url), 'name="pdf_contents_layout"')
        with override_config(HHS_NOFO_FY27_PDF_CONTENTS_ENABLED=True):
            response = self.client.get(url)
            self.assertContains(response, 'name="pdf_contents_layout"')
            self.assertContains(response, "Single column")
            self.nofo.introductory_page_family = "legacy"
            self.nofo.save()
            self.assertNotContains(self.client.get(url), 'name="pdf_contents_layout"')

    @override_config(HHS_NOFO_FY27_PDF_CONTENTS_ENABLED=True)
    def test_missing_choice_preserves_existing_value_and_bad_choice_is_rejected(self):
        self.nofo.pdf_contents_layout = Nofo.PdfContentsLayout.SINGLE
        data = {
            "theme": self.nofo.theme,
            "cover": self.nofo.cover,
            "icon_style": self.nofo.icon_style,
        }
        form = NofoThemeOptionsForm(data, instance=self.nofo, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().pdf_contents_layout, Nofo.PdfContentsLayout.SINGLE)
        form = NofoThemeOptionsForm(
            {**data, "pdf_contents_layout": "bogus"}, instance=self.nofo, user=self.user
        )
        self.assertIn("pdf_contents_layout", form.errors)
