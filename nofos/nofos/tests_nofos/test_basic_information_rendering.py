from io import BytesIO
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from nofos.models import Nofo
from nofos.pdf_service import generate_nofo_pdf
from nofos.tests_nofos.test_editable_introduction import fy27_docx
from nofos.tests_nofos.test_introductory_page import introductory_docx

COVER_TEXT = "Synthetic program information."
APPLICANT_TEXT = "Include the sample project identifier."


def with_later_basic_information(document):
    output = BytesIO()
    with (
        ZipFile(BytesIO(document)) as source,
        ZipFile(output, "w", ZIP_DEFLATED) as target,
    ):
        for name in source.namelist():
            data = source.read(name)
            if name == "word/styles.xml":
                data = data.replace(
                    b"</w:styles>",
                    b'<w:style w:type="paragraph" w:styleId="Heading4">'
                    b'<w:name w:val="heading 4"/></w:style></w:styles>',
                )
            if name == "word/document.xml":
                section = (
                    '<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr>'
                    "<w:r><w:t>Step 3: Prepare Your Application</w:t></w:r></w:p>"
                    '<w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr>'
                    "<w:r><w:t>Project summary</w:t></w:r></w:p>"
                    '<w:p><w:pPr><w:pStyle w:val="Heading4"/></w:pPr>'
                    "<w:r><w:t>Basic information</w:t></w:r></w:p>"
                    f"<w:p><w:r><w:t>{APPLICANT_TEXT}</w:t></w:r></w:p>"
                ).encode()
                # Add the section before the FY27 trailing Metadata block, if present.
                metadata = (
                    b'<w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr>'
                    b"<w:r><w:t>Metadata</w:t></w:r></w:p>"
                )
                anchor = metadata if metadata in data else b"</w:body>"
                data = data.replace(anchor, section + anchor, 1)
            target.writestr(name, data)
    return output.getvalue()


class BasicInformationRenderingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="basic-info@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.force_login(self.user)

    def test_later_basic_information_survives_editor_preview_and_pdf(self):
        for source, has_intro in (
            (introductory_docx(name="Before You Begin"), False),
            (fy27_docx(), True),
        ):
            with self.subTest(imported_introduction=has_intro):
                result = self.client.post(
                    reverse("nofos:nofo_import"),
                    {
                        "nofo-import": SimpleUploadedFile(
                            "basic-information.docx",
                            with_later_basic_information(source),
                            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        ),
                    },
                )
                self.assertEqual(result.status_code, 302)
                nofo = Nofo.objects.latest("created")
                self.assertEqual(nofo.has_imported_introduction, has_intro)
                cover = nofo.sections.get(order=1).subsections.get(order=1)
                self.assertEqual(cover.name, "Basic information")
                self.assertIn(COVER_TEXT, cover.body)
                later = nofo.sections.get(order=3).subsections.get(
                    name="Basic information"
                )
                self.assertIn(APPLICANT_TEXT, later.body)

                editor = self.client.get(reverse("nofos:nofo_edit", args=[nofo.pk]))
                self.assertContains(editor, APPLICANT_TEXT, count=1)
                self.assertNotContains(editor, COVER_TEXT)
                editor_html = BeautifulSoup(editor.content, "html.parser")
                row = editor_html.find(id=later.html_id).find_parent("tr")
                self.assertIn(APPLICANT_TEXT, row.get_text())
                self.assertIsNotNone(
                    row.find(
                        "a",
                        href=reverse(
                            "nofos:subsection_edit",
                            args=[nofo.pk, later.section_id, later.pk],
                        ),
                    )
                )
                self.assertIsNotNone(
                    editor_html.find(id="nofo-edit--basic-information")
                )

                preview = self.client.get(reverse("nofos:nofo_view", args=[nofo.pk]))
                self.assertEqual(preview.status_code, 200)
                with patch("nofos.pdf_service.docraptor.DocApi") as provider:
                    generate_nofo_pdf(
                        nofo, base_url="https://example.test", is_test_pdf=True
                    )
                    pdf_html = provider.return_value.create_doc.call_args.args[0][
                        "document_content"
                    ]
                for source_html in (preview.content, pdf_html):
                    soup = BeautifulSoup(source_html, "html.parser")
                    heading = soup.find(id=later.html_id)
                    self.assertEqual(heading.get_text(strip=True), "Basic information")
                    self.assertIn(APPLICANT_TEXT, heading.find_parent("section").text)
                    self.assertEqual(soup.get_text().count(APPLICANT_TEXT), 1)
                    self.assertNotIn(COVER_TEXT, soup.get_text())
                    self.assertEqual(len(soup.find_all(id=cover.html_id)), 1)
                    metadata = soup.select(".section--content--basic-information")
                    self.assertEqual(len(metadata), 1)
                    self.assertIn(nofo.opdiv, metadata[0].get_text())
