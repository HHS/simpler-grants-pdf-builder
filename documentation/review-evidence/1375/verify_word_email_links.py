import unittest
from io import BytesIO
from unittest.mock import patch
from xml.sax.saxutils import escape, quoteattr
from zipfile import ZipFile

import django

django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from nofos.nofo import parse_uploaded_file_as_html_string

from nofos.content_processing import process_document_content


class WordEmailLinkChecks(unittest.TestCase):
    def check_target(self, href, label, expected):
        word = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        office = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        package = "http://schemas.openxmlformats.org/package/2006/relationships"
        content = (
            f'<w:document xmlns:w="{word}" xmlns:r="{office}"><w:body>'
            f'<w:p><w:hyperlink r:id="rId1"><w:r><w:t>{escape(label)}</w:t>'
            "</w:r></w:hyperlink></w:p></w:body></w:document>"
        )
        rels = (
            f'<Relationships xmlns="{package}"><Relationship Id="rId1" '
            f'Type="{office}/hyperlink" Target={quoteattr(href)} TargetMode="External"/>'
            "</Relationships>"
        )
        docx = BytesIO()
        with ZipFile(docx, "w") as fixture:
            fixture.writestr("word/document.xml", content)
            fixture.writestr("word/_rels/document.xml.rels", rels)
        upload = SimpleUploadedFile(
            "synthetic.docx",
            docx.getvalue(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        with patch("nofos.nofo.config") as config:
            config.WORD_IMPORT_STRICT_MODE = False
            html, warnings = parse_uploaded_file_as_html_string(upload)
        self.assertEqual(warnings, 0)
        html = "<h1>Eligibility</h1><h2>Contact</h2>" + html
        result = process_document_content(html, builder_import=True)
        body = result.sections[0]["subsections"][0]["body"]
        link = body[0].a
        self.assertEqual(link["href"], expected)
        self.assertEqual(link.get_text(), label)

    def test_repair_matching_file_targets(self):
        for href, label in (
            ("file://///server/share/contact@example.test", "contact@example.test"),
            (
                "file:///C:/contacts/user%2Bteam%40example.test",
                "user+team@example.test",
            ),
        ):
            with self.subTest(href=href):
                self.check_target(href, label, "mailto:" + label)

    def test_preserve_existing_email_and_web_links(self):
        for href in (
            "mailto:contact@example.test",
            "https://example.test/contact@example.test",
        ):
            with self.subTest(href=href):
                self.check_target(href, "contact@example.test", href)

    def test_preserve_ambiguous_file_targets(self):
        for suffix, label in (
            ("other@example.test", "contact@example.test"),
            ("contact@example.test", "Contact us"),
            ("contact@example.test?download=1", "contact@example.test"),
            ("contact@example.test#bookmark", "contact@example.test"),
            ("contact@example.test.pdf", "contact@example.test"),
        ):
            href = "file://///server/share/" + suffix
            with self.subTest(href=href, label=label):
                self.check_target(href, label, href)


if __name__ == "__main__":
    unittest.main(verbosity=2)
