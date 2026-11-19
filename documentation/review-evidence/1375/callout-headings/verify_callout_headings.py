"""Synthetic Word imports exercise the saved document and shared PDF/HTML template."""

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile

from bs4 import BeautifulSoup
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, Subsection
from nofos.nofo_document_context import get_nofo_document_context
from nofos.templatetags.utils import is_floating_callout_box


def deadline_docx(title="Application due date", both=False, plain_titles=False):
    """Reuse the repository's valid Word package, with a synthetic document body."""

    def p(text, style=None):
        properties = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
        return f'<w:p>{properties}<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'

    def callout(name, content, style="Heading3"):
        return f"<w:tbl><w:tr><w:tc>{p(name, style)}{content}</w:tc></w:tr></w:tbl>"

    date = p("December 1, 2026, at 4:30 p.m. ET")
    link = '<w:p><w:hyperlink w:anchor="other-dates"><w:r><w:t>See other key dates</w:t></w:r></w:hyperlink></w:p>'
    deadline = (
        date + link
        if "application" in title.casefold()
        else p("Application deadline: December 1, 2026")
    )
    body = (
        p("Step 1: Review the Opportunity", "Heading2")
        + p("Basic information", "Heading3")
        + p("Opdiv: CDC")
        + p("Opportunity Number: CDC-SYNTHETIC-1091")
        + p("This opportunity supports community health.")
    )
    title_style = None if plain_titles else "Heading3"
    body += callout(title, deadline, title_style)
    if both:
        body += callout("Key dates", p("Award date: March 1, 2027"), title_style)
    body += callout("Key facts", p("Funding: $100,000"), title_style)
    body += callout("Have questions?", p("Contact the program team."))
    body += '<w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr><w:bookmarkStart w:id="42" w:name="other-dates"/><w:r><w:t>Key dates</w:t></w:r><w:bookmarkEnd w:id="42"/></w:p>'
    body += p("Other key dates are listed here.")
    body += p("Application due date", "Heading3") + p(
        "Application due date is also ordinary prose."
    )
    body += (
        p("Step 2: Get Ready to Apply", "Heading2")
        + p("Prepare your application", "Heading3")
        + p("Gather the required documents.")
    )
    if plain_titles:
        body += callout("Key facts", p("Outside Basic information."), None)
    document = (
        '<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
        + body
        + "<w:sectPr/></w:body></w:document>"
    ).encode()
    result = BytesIO()
    base = Path(settings.BASE_DIR) / "nofos/fixtures/docx/lists.docx"
    with ZipFile(base) as source, ZipFile(result, "w") as target:
        for entry in source.infolist():
            target.writestr(
                entry,
                (
                    document
                    if entry.filename == "word/document.xml"
                    else source.read(entry)
                ),
            )
    return SimpleUploadedFile(
        "deadline.docx",
        result.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


class DeadlineCalloutWorkflowTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="deadline@example.com",
            password="local-test-only",
            group="bloom",
            force_password_reset=False,
        )
        self.client.force_login(self.user)

    def import_nofo(self, title="Application due date", both=False):
        response = self.client.post(
            reverse("nofos:nofo_import"), {"nofo-import": deadline_docx(title, both)}
        )
        self.assertEqual(response.status_code, 302)
        return Nofo.objects.latest("created")

    def assert_presentation(self, nofo, title):
        callout = Subsection.objects.get(
            section__nofo=nofo, callout_box=True, name=title
        )
        self.assertEqual(callout.tag, "h4")
        response = self.client.get(reverse("nofos:nofo_view", kwargs={"pk": nofo.pk}))
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, "html.parser")
        sidebar = soup.select_one(".section--content--right-col")
        self.assertIsNotNone(sidebar)
        self.assertEqual(len(sidebar.find_all("h4", string=title)), 1)
        self.assertIsNotNone(sidebar.find("h4", string="Key facts"))
        self.assertIn("Contact the program team.", sidebar.get_text())
        normal = Subsection.objects.get(
            section__nofo=nofo, name="Key dates", callout_box=False
        )
        self.assertFalse(is_floating_callout_box(normal))
        target = soup.find(id=normal.html_id)
        self.assertIsNone(target.find_parent(class_="section--content--right-col"))
        if title == "Application due date":
            self.assertIn("December 1, 2026, at 4:30 p.m. ET", callout.body)
            self.assertIsNotNone(
                sidebar.find(
                    "a", href="#" + normal.html_id, string="See other key dates"
                )
            )
            self.assertIsNone(sidebar.find("strong", string=lambda s: s and "4:" in s))
        else:
            legacy_body = sidebar.select_one(".callout-box--contents")
            self.assertEqual(
                legacy_body.find("strong").get_text().strip(), "Application deadline:"
            )
            self.assertIsNotNone(legacy_body.find("br"))
        # PDF generation uses this same document template through nofo_pdf.html.
        pdf_context = {"nofo": nofo, "object": nofo}
        pdf_context.update(get_nofo_document_context(nofo))
        pdf_soup = BeautifulSoup(
            render_to_string("nofos/nofo_pdf.html", pdf_context), "html.parser"
        )
        pdf_sidebar = pdf_soup.select_one(".section--content--right-col")
        for heading in sidebar.select("h4.callout-box--title"):
            self.assertIsNotNone(pdf_sidebar.find("h4", string=heading.get_text()))
        return soup

    def test_new_deadline_case_spacing_and_plain_names(self):
        for title in (
            "Application due date",
            " APPLICATION   DUE DATE ",
            "application due date",
        ):
            with self.subTest(title=title):
                nofo = self.import_nofo(title)
                self.assert_presentation(nofo, "Application due date")
                plain = Subsection.objects.get(
                    section__nofo=nofo, name="Application due date", callout_box=False
                )
                self.assertFalse(is_floating_callout_box(plain))

    def test_legacy_deadline_and_saved_record_do_not_change_on_render(self):
        nofo = self.import_nofo("Key dates")
        before = list(Subsection.objects.filter(section__nofo=nofo).values())
        self.assert_presentation(nofo, "Key dates")
        self.assertEqual(
            before, list(Subsection.objects.filter(section__nofo=nofo).values())
        )

    def test_all_four_reimport_transitions(self):
        for original in ("Key dates", "Application due date"):
            for replacement in ("Key dates", "Application due date"):
                with self.subTest(original=original, replacement=replacement):
                    nofo = self.import_nofo(original)
                    response = self.client.post(
                        reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk}),
                        {"nofo-import": deadline_docx(replacement)},
                    )
                    self.assertEqual(response.status_code, 302)
                    self.assert_presentation(nofo, replacement)
                    self.assertEqual(
                        Subsection.objects.filter(
                            section__nofo=nofo,
                            callout_box=True,
                            name__in=["Key dates", "Application due date"],
                        ).count(),
                        1,
                    )

    def test_both_deadlines_are_preserved_without_selection(self):
        nofo = self.import_nofo(both=True)
        soup = self.assert_presentation(nofo, "Application due date")
        self.assertIsNotNone(
            soup.select_one(".section--content--right-col").find(
                "h4", string="Key dates"
            )
        )

    def test_plain_callout_titles_on_import_and_reimport(self):
        def upload():
            return deadline_docx(both=True, plain_titles=True)

        response = self.client.post(
            reverse("nofos:nofo_import"), {"nofo-import": upload()}
        )
        self.assertEqual(response.status_code, 302)
        nofo = Nofo.objects.latest("created")

        for overwrite in (False, True):
            with self.subTest(overwrite=overwrite):
                if overwrite:
                    response = self.client.post(
                        reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk}),
                        {"nofo-import": upload()},
                    )
                    self.assertEqual(response.status_code, 302)
                soup = self.assert_presentation(nofo, "Application due date")
                sidebar = soup.select_one(".section--content--right-col")
                self.assertIsNotNone(sidebar.find("h4", string="Key dates"))
                self.assertIsNone(sidebar.find("p", string="Key facts"))
                outside = Subsection.objects.get(
                    section__nofo=nofo, section__order=2, callout_box=True
                )
                self.assertEqual(outside.name, "")
                self.assertIn("Key facts", outside.body)

    def test_edited_deadline_title_keeps_simple_time_formatting(self):
        nofo = self.import_nofo()
        deadline = Subsection.objects.get(
            section__nofo=nofo, callout_box=True, name="Application due date"
        )
        deadline.name = " APPLICATION   DUE DATE "
        deadline.save()
        response = self.client.get(reverse("nofos:nofo_view", kwargs={"pk": nofo.pk}))
        sidebar = BeautifulSoup(response.content, "html.parser").select_one(
            ".section--content--right-col"
        )
        self.assertIn("December 1, 2026, at 4:30 p.m. ET", sidebar.get_text())
        self.assertIsNone(sidebar.find("strong", string=lambda s: s and "4:" in s))


class ScopedCalloutVerificationTests(TestCase):
    def test_heading_and_table_boundaries(self):
        from nofos.content_processing import get_sections_and_subsections_from_soup

        def table(paragraphs):
            return f"<table><tr><td>{paragraphs}</td></tr></table>"

        for level in (1, 2):
            with self.subTest(source_heading_level=level):
                child = level + 1
                html = (
                    f"<h{level}>Step 1: Review the Opportunity</h{level}>"
                    + table("<p>Key facts</p><p>Before Basic information</p>")
                    + f"<h{child}>Basic information</h{child}>"
                    + table("<p><strong>KEY   DATES</strong></p><p>Keep dates</p>")
                    + table("<p>Introductory text</p><p>Key facts</p>")
                    + table("<p>Key facts for applicants</p>")
                    + "<table><tr><td><p>Key facts</p></td><td>Value</td></tr></table>"
                    + "<p>Application due date is stated in ordinary prose.</p>"
                    + f"<h{child}>Eligibility</h{child}>"
                    + table("<p>Application due date</p><p>Outside the Basic information scope</p>")
                )
                result = get_sections_and_subsections_from_soup(
                    BeautifulSoup(html, "html.parser"), f"h{level}", consume_metadata=True
                )
                subsections = result[0]["subsections"]
                boxes = [item for item in subsections if item["is_callout_box"]]
                self.assertEqual([item["name"] for item in boxes], ["", "Key dates", "", "", ""])
                self.assertEqual(boxes[1]["tag"], "h4")
                self.assertIn("Keep dates", boxes[1]["body"].get_text())
                self.assertIn("Key facts", boxes[2]["body"].get_text())
                self.assertTrue(
                    any(
                        tag.name == "table"
                        for item in subsections if not item["is_callout_box"]
                        for tag in item["body"]
                    )
                )

    def test_manual_line_break_is_title_whitespace(self):
        from nofos.content_processing import get_sections_and_subsections_from_soup

        html = (
            "<h2>Step 1: Review the Opportunity</h2><h3>Basic information</h3>"
            "<table><tr><td><p>Application<br>due date</p>"
            "<p>Preserved date text</p></td></tr></table>"
        )
        sections = get_sections_and_subsections_from_soup(
            BeautifulSoup(html, "html.parser"), "h2", consume_metadata=True
        )
        box = next(item for item in sections[0]["subsections"] if item["is_callout_box"])
        self.assertEqual((box["name"], box["tag"]), ("Application due date", "h4"))
        self.assertIn("Preserved date text", box["body"].get_text())
