from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from xml.sax.saxutils import escape
from zipfile import ZipFile

from bs4 import BeautifulSoup
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, Subsection
from nofos.nofo import consume_tagline_paragraph, extract_basic_information_tagline
from nofos.nofo_document_context import get_nofo_document_context


def tagline_docx(
    value="Stronger communities",
    *,
    new=True,
    empty=False,
    internal_link=False,
    number="CDC-SYNTHETIC-1093",
):
    def p(text, style=None):
        props = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
        return f'<w:p>{props}<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'

    body = p("Step 1: Review the Opportunity", "Heading2") + p(
        "Basic information", "Heading3"
    )
    body += p("Opdiv: CDC") + p("Opportunity Number: " + number)
    if new:
        body += p("Tagline", "Heading4") + ("<w:p/>" if empty else p(value))
    else:
        body += p("Tagline: " + value)
    body += p("Neighboring paragraph stays.")
    body += (
        "<w:tbl><w:tr><w:tc>"
        + p("Key facts", "Heading4")
        + p("Funding: $100,000")
        + "</w:tc></w:tr></w:tbl>"
    )
    body += p("Eligibility", "Heading3") + p("Eligible applicants may apply.")
    if internal_link:
        body = body.replace(
            p(value),
            '<w:p><w:r><w:t>See </w:t></w:r><w:hyperlink w:anchor="eligibility-original"><w:r><w:t>eligibility</w:t></w:r></w:hyperlink><w:r><w:t>.</w:t></w:r></w:p>',
            1,
        )
        body = body.replace(
            p("Eligibility", "Heading3"),
            '<w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr><w:bookmarkStart w:id="42" w:name="eligibility-original"/><w:r><w:t>Eligibility</w:t></w:r><w:bookmarkEnd w:id="42"/></w:p>',
        )
    body += (
        p("Step 2: Get Ready to Apply", "Heading2")
        + p("Prepare", "Heading3")
        + p("Gather the documents.")
    )
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
        + body
        + "<w:sectPr/></w:body></w:document>"
    ).encode()
    result = BytesIO()
    with ZipFile(
        Path(settings.BASE_DIR) / "nofos/fixtures/docx/lists.docx"
    ) as source, ZipFile(result, "w") as target:
        for entry in source.infolist():
            target.writestr(
                entry,
                xml if entry.filename == "word/document.xml" else source.read(entry),
            )
    return SimpleUploadedFile(
        "tagline.docx",
        result.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


class ScopedTaglineExtractionTests(TestCase):
    def extract(
        self,
        content,
        prefix="<h2>Step 1: Review the Opportunity</h2><h3>Basic information</h3>",
        level="h2",
    ):
        soup = BeautifulSoup("<body>" + prefix + content + "</body>", "html.parser")
        return (
            consume_tagline_paragraph(
                soup, extract_basic_information_tagline(soup, level)
            ),
            soup,
        )

    def test_exact_scope_case_spacing_one_paragraph_and_links(self):
        value, soup = self.extract(
            '<h4>  TAGLINE </h4><p>Help <strong>communities</strong> <a href="https://example.org">thrive</a></p><p>Keep second paragraph.</p><h3>Eligibility</h3><p><a href="#kept">Keep link</a></p>'
        )
        self.assertEqual(value, "Help **communities** [thrive](https://example.org)")
        self.assertIsNotNone(soup.find(attrs={"data-nofo-tagline-source": "true"}))
        self.assertIn("Keep second paragraph.", str(soup))
        self.assertIn('href="#kept"', str(soup))

    def test_blank_does_not_search_past_immediate_element(self):
        for next_html in (
            "<h3>Eligibility</h3><p>Do not borrow.</p>",
            "<p></p><p>Do not borrow.</p>",
            "<table><tr><td>Keep table</td></tr></table><p>Do not borrow.</p>",
            "<ul><li>Keep list</li></ul><p>Do not borrow.</p>",
            "",
        ):
            with self.subTest(next_html=next_html):
                value, soup = self.extract("<h4>Tagline</h4>" + next_html)
                self.assertEqual(value, "")
                self.assertIsNotNone(
                    soup.find(attrs={"data-nofo-tagline-source": "true"})
                )
                if "Do not borrow" in next_html:
                    self.assertIn("Do not borrow", str(soup))

    def test_other_locations_are_not_consumed(self):
        cases = [
            (
                "<h4>Funding details</h4><h5>Tagline</h5><p>Nested elsewhere.</p>",
                "<h2>Step 1: Review the Opportunity</h2><h3>Basic information</h3>",
            ),
            (
                "<h4>Tagline</h4><p>Other step.</p>",
                "<h2>Step 2: Get Ready to Apply</h2><h3>Basic information</h3>",
            ),
            (
                "<h4>Tagline</h4><p>Wrong parent.</p>",
                "<h2>Step 1: Review the Opportunity</h2><h3>Eligibility</h3>",
            ),
            (
                "<h3>Eligibility</h3><h4>Tagline</h4><p>Outside Basic information.</p>",
                "<h2>Step 1: Review the Opportunity</h2><h3>Basic information</h3>",
            ),
            (
                "<table><tr><td><h4>Tagline</h4><p>Table text.</p></td></tr></table>",
                "<h2>Step 1: Review the Opportunity</h2><h3>Basic information</h3>",
            ),
            (
                "<p>Tagline</p><p>Incidental prose.</p>",
                "<h2>Step 1: Review the Opportunity</h2><h3>Basic information</h3>",
            ),
        ]
        for content, prefix in cases:
            with self.subTest(content=content):
                value, soup = self.extract(content, prefix)
                self.assertIsNone(value)
                self.assertIn(content, str(soup))

    def test_h1_sections_and_placeholder_are_preserved(self):
        value, _ = self.extract(
            "<h3>Tagline</h3><p>{Insert a 15 words or fewer tagline, ending with a period.}</p>",
            "<h1>Step 1: Review the Opportunity</h1><h2>Basic information</h2>",
            "h1",
        )
        self.assertEqual(
            value, "{Insert a 15 words or fewer tagline, ending with a period.}"
        )


class ScopedTaglineWorkflowTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="tagline@example.com",
            password="local-test-only",
            group="bloom",
            force_password_reset=False,
        )
        self.client.force_login(self.user)

    def import_nofo(self, value="Stronger communities", **kwargs):
        response = self.client.post(
            reverse("nofos:nofo_import"), {"nofo-import": tagline_docx(value, **kwargs)}
        )
        self.assertEqual(response.status_code, 302)
        return Nofo.objects.latest("created")

    def assert_new_source_consumed(self, nofo, expected):
        nofo.refresh_from_db()
        self.assertEqual(nofo.tagline, expected)
        subsections = Subsection.objects.filter(section__nofo=nofo)
        self.assertFalse(subsections.filter(name__iexact="tagline").exists())
        self.assertTrue(subsections.filter(name="Key facts", callout_box=True).exists())
        self.assertTrue(
            any("Neighboring paragraph stays." in s.body for s in subsections)
        )
        if expected:
            self.assertFalse(any(expected in s.body for s in subsections))
        response = self.client.get(reverse("nofos:nofo_view", kwargs={"pk": nofo.pk}))
        soup = BeautifulSoup(response.content, "html.parser")
        if expected:
            self.assertEqual(
                soup.select_one(".nofo--tagline").get_text(strip=True), expected
            )
        else:
            self.assertIsNone(soup.select_one(".nofo--tagline"))
        self.assertIsNone(soup.find(["h3", "h4"], string="Tagline"))
        self.assertIn("Neighboring paragraph stays.", soup.get_text())
        context = {"nofo": nofo, "object": nofo}
        context.update(get_nofo_document_context(nofo))
        pdf = BeautifulSoup(
            render_to_string("nofos/nofo_pdf.html", context), "html.parser"
        )
        self.assertEqual(bool(pdf.select_one(".nofo--tagline")), bool(expected))
        self.assertIn("Neighboring paragraph stays.", pdf.get_text())

    def test_new_word_values_and_real_empty_paragraph(self):
        for value in ("Stronger communities", "Stronger communities.", ""):
            with self.subTest(value=value):
                nofo = self.import_nofo(value, empty=not value)
                self.assert_new_source_consumed(nofo, value)

    def test_legacy_values_and_underscore_blanks(self):
        for value in ("Legacy tagline", "____ ____"):
            with self.subTest(value=value):
                nofo = self.import_nofo(value, new=False)
                self.assertEqual(nofo.tagline, "" if "_" in value else value)

    def test_blank_new_source_has_precedence_over_legacy(self):
        upload = SimpleUploadedFile(
            "mixed.html",
            b"<h2>Step 1: Review the Opportunity</h2><h3>Basic information</h3><p>Opdiv: CDC</p><p>Tagline: Do not fall back</p><h4>Tagline</h4><p></p><h3>Eligibility</h3><p>Keep content</p>",
            content_type="text/html",
        )
        response = self.client.post(
            reverse("nofos:nofo_import"), {"nofo-import": upload}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Nofo.objects.latest("created").tagline, "")

    def test_all_four_reimports_replace_tagline_under_existing_contract(self):
        for original_new in (False, True):
            for incoming_new in (False, True):
                with self.subTest(original_new=original_new, incoming_new=incoming_new):
                    nofo = self.import_nofo("Original value", new=original_new)
                    response = self.client.post(
                        reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk}),
                        {
                            "nofo-import": tagline_docx(
                                "Incoming value", new=incoming_new
                            )
                        },
                    )
                    self.assertEqual(response.status_code, 302)
                    nofo.refresh_from_db()
                    self.assertEqual(nofo.tagline, "Incoming value")
                    if incoming_new:
                        self.assert_new_source_consumed(nofo, "Incoming value")

    def test_number_confirmation_keeps_extracted_value(self):
        nofo = self.import_nofo()
        response = self.client.post(
            reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk}),
            {"nofo-import": tagline_docx("Confirmed value", number="CDC-OTHER-1093")},
        )
        self.assertRedirects(
            response,
            reverse("nofos:nofo_import_confirm_overwrite", kwargs={"pk": nofo.pk}),
        )
        response = self.client.post(
            reverse("nofos:nofo_import_confirm_overwrite", kwargs={"pk": nofo.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assert_new_source_consumed(nofo, "Confirmed value")

    def test_existing_records_views_and_editing_other_fields_are_not_cleanup(self):
        nofo = self.import_nofo("Old stored tagline", new=False)
        section = nofo.sections.first()
        source = Subsection.objects.create(
            section=section,
            name="Tagline",
            tag="h4",
            order=99,
            body="Stored source paragraph",
        )
        before = list(Subsection.objects.filter(section__nofo=nofo).values())
        self.client.get(reverse("nofos:nofo_view", kwargs={"pk": nofo.pk}))
        self.client.get(reverse("nofos:nofo_edit", kwargs={"pk": nofo.pk}))
        context = {"nofo": nofo, "object": nofo}
        context.update(get_nofo_document_context(nofo))
        render_to_string("nofos/nofo_pdf.html", context)
        self.assertEqual(
            before, list(Subsection.objects.filter(section__nofo=nofo).values())
        )
        nofo.refresh_from_db()
        source.refresh_from_db()
        self.assertEqual(nofo.tagline, "Old stored tagline")
        self.assertEqual(source.body, "Stored source paragraph")

    def test_failed_and_status_blocked_reimport_preserve_saved_fields(self):
        nofo = self.import_nofo()
        before = list(Subsection.objects.filter(section__nofo=nofo).values())
        url = reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk})
        with patch(
            "nofos.views.overwrite_nofo",
            side_effect=ValidationError("Synthetic failure"),
        ):
            self.client.post(url, {"nofo-import": tagline_docx("Do not save")})
        nofo.refresh_from_db()
        self.assertEqual(nofo.tagline, "Stronger communities")
        self.assertEqual(
            before, list(Subsection.objects.filter(section__nofo=nofo).values())
        )
        nofo.status = "published"
        nofo.save()
        response = self.client.post(url, {"nofo-import": tagline_docx("Do not save")})
        self.assertEqual(response.status_code, 400)
        nofo.refresh_from_db()
        self.assertEqual(nofo.tagline, "Stronger communities")

    def test_tagline_remains_editable_through_existing_field(self):
        nofo = self.import_nofo()
        response = self.client.post(
            reverse("nofos:nofo_edit_tagline", kwargs={"pk": nofo.pk}),
            {"tagline": "Edited in the existing field"},
        )
        self.assertEqual(response.status_code, 302)
        self.assert_new_source_consumed(nofo, "Edited in the existing field")

    def test_internal_links_in_word_and_html_taglines_use_generated_targets(self):
        for upload in (
            tagline_docx(internal_link=True),
            SimpleUploadedFile(
                "tagline.html",
                b'<h2>Step 1: Review the Opportunity</h2><h3>Basic information</h3><p>Opdiv: CDC</p><h4>Tagline</h4><p>See <a href="#eligibility-original">eligibility</a>.</p><h3 id="eligibility-original">Eligibility</h3><p>Eligible applicants may apply.</p>',
                content_type="text/html",
            ),
        ):
            with self.subTest(file=upload.name):
                response = self.client.post(
                    reverse("nofos:nofo_import"), {"nofo-import": upload}
                )
                self.assertEqual(response.status_code, 302)
                nofo = Nofo.objects.latest("created")
                response = self.client.get(
                    reverse("nofos:nofo_view", kwargs={"pk": nofo.pk})
                )
                soup = BeautifulSoup(response.content, "html.parser")
                link = soup.select_one(".nofo--tagline a")
                self.assertIsNotNone(link)
                self.assertIsNotNone(soup.find(id=link["href"][1:]))

    def test_compare_and_composer_keep_the_source_heading_and_value(self):
        from compare.models import CompareSubsection
        from composer.models import ContentGuideSubsection

        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()
        for route, model in (
            ("compare:compare_import", CompareSubsection),
            ("composer:composer_import", ContentGuideSubsection),
        ):
            with self.subTest(route=route):
                response = self.client.post(
                    reverse(route), {"nofo-import": tagline_docx()}
                )
                self.assertEqual(response.status_code, 302)
                source = model.objects.get(name="Tagline")
                self.assertIn("Stronger communities", source.body)

    def test_incoming_links_to_consumed_heading_reach_basic_information(self):
        for value in ("Value", ""):
            for basic_id in ("", ' id="basic-original"'):
                with self.subTest(value=value, basic_id=basic_id):
                    html = f'<h2>Step 1: Review the Opportunity</h2><h3{basic_id}>Basic information</h3><p>Opdiv: CDC</p><h4 id="tagline-source">Tagline</h4><p>{value}</p><h3>Eligibility</h3><p><a href="#tagline-source">See tagline</a></p>'
                    response = self.client.post(
                        reverse("nofos:nofo_import"),
                        {
                            "nofo-import": SimpleUploadedFile(
                                "tagline.html", html.encode(), content_type="text/html"
                            )
                        },
                    )
                    self.assertEqual(response.status_code, 302)
                    nofo = Nofo.objects.latest("created")
                    response = self.client.get(
                        reverse("nofos:nofo_view", kwargs={"pk": nofo.pk})
                    )
                    soup = BeautifulSoup(response.content, "html.parser")
                    link = soup.find("a", string="See tagline")
                    target = soup.find(id=link["href"][1:])
                    self.assertEqual(target.get_text(strip=True), "Basic information")
                    self.assertFalse(
                        Subsection.objects.filter(
                            section__nofo=nofo, name__iexact="tagline"
                        ).exists()
                    )
