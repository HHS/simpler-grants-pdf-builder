from io import BytesIO
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

from bs4 import BeautifulSoup
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo
from nofos.note_paragraphs import normalize_note_labels
from nofos.pdf_service import generate_nofo_pdf
from nofos.templatetags.add_classes_to_paragraphs import style_note_paragraphs
from nofos.tests_nofos.test_editable_introduction import fy27_docx


class NoteWorkflowTests(TestCase):
    def test_word_import_and_both_document_renderers(self):
        output = BytesIO()
        with ZipFile(BytesIO(fy27_docx())) as source:
            with ZipFile(output, "w", ZIP_DEFLATED) as target:
                for name in source.namelist():
                    data = source.read(name)
                    if name == "word/document.xml":
                        needle = b"Distinctive source text is editable after import."
                        self.assertIn(needle, data)
                        data = data.replace(
                            needle, b"PLEASE NOTE: Keep the signed form."
                        )
                    target.writestr(name, data)
        self.client.force_login(
            BloomUser.objects.create_user(
                email="note-editor@example.test",
                password=None,
                group="bloom",
                force_password_reset=False,
            )
        )
        response = self.client.post(
            reverse("nofos:nofo_import"),
            {
                "nofo-import": SimpleUploadedFile(
                    "note.docx",
                    output.getvalue(),
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        self.assertEqual(response.status_code, 302)
        nofo = Nofo.objects.get()
        html = self.client.get(reverse("nofos:nofo_view", args=[nofo.pk]))
        self.assertEqual(html.status_code, 200)
        with patch("nofos.pdf_service.docraptor.DocApi") as provider:
            provider.return_value.create_doc.return_value = b"%PDF"
            generate_nofo_pdf(
                nofo, base_url="https://example.test/nofo", is_test_pdf=True
            )
            pdf_source = provider.return_value.create_doc.call_args.args[0][
                "document_content"
            ]
        for rendered in (html.content, pdf_source):
            note = BeautifulSoup(rendered, "html.parser").select_one("p.nofo-note")
            self.assertIsNotNone(note)
            self.assertEqual(
                note.get_text(strip=True, separator=" "), "Note: Keep the signed form."
            )
            self.assertEqual(note.strong.get_text(), "Note:")


class NoteParagraphTests(SimpleTestCase):
    def test_normalizes_only_prefix_and_preserves_inline_body(self):
        for prefix in (
            "<strong>PLEASE NOTE:</strong>",
            "NOTE:",
            "Please note:",
            "<strong>Please note</strong><strong>:</strong>",
            "Note&nbsp;–",
            "N.B.",
            "N. B.:",
        ):
            with self.subTest(prefix=prefix):
                soup = BeautifulSoup(
                    f'<p>{prefix}&nbsp;Keep <em>THIS</em> <a href="/guide">link</a>.</p>',
                    "html.parser",
                )
                normalize_note_labels(soup)
                expected = '<p><strong>Note:</strong> Keep <em>THIS</em> <a href="/guide">link</a>.</p>'
                self.assertEqual(str(soup), expected)
                normalize_note_labels(soup)
                self.assertEqual(str(soup), expected)

    def test_leaves_ordinary_prose_and_nonformatting_prefixes_alone(self):
        for body in (
            "Please note that forms are due Friday.",
            "Attach the form. Please note: retain a copy.",
            "Note where to sign.",
            '<a href="/guidance">Note:</a> Read more.',
            '<span id="anchor">Note:</span> Read more.',
            '<img src="cover.png"/>Note: Read more.',
            "Note<br/>: Read more.",
        ):
            with self.subTest(body=body):
                soup = BeautifulSoup(f"<p>{body}</p>", "html.parser")
                original = str(soup)
                normalize_note_labels(soup)
                self.assertEqual(str(soup), original)

    def test_styles_flat_and_nested_cell_notes_and_keeps_table_with_next_note(self):
        rendered = BeautifulSoup(
            style_note_paragraphs(
                '<table id="keep"><tr><td><strong>Note:</strong> Flat.</td>'
                "<td><p>Note: Nested.</p><p>Other.</p></td></tr></table>"
                "<p> </p><p><strong>Note:</strong> After the table.</p>"
                '<table id="ordinary"><tr><td>Other.</td></tr></table>'
                '<p><img src="example.png"/></p><p>Note: Not attached to the table.</p>'
            ),
            "html.parser",
        )
        self.assertEqual(len(rendered.select(".nofo-note--in-table")), 2)
        self.assertEqual(len(rendered.select("p.nofo-note")), 2)
        self.assertEqual(
            [t["id"] for t in rendered.select(".table--with-following-note")], ["keep"]
        )
        self.assertFalse(rendered.select("[role], [aria-level]"))
