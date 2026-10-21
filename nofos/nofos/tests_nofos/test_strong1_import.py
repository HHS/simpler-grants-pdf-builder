"""Strong1 and redundant bold must survive the import/render round trip."""

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import markdown
from bs4 import BeautifulSoup
from composer.models import ContentGuideSubsection
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.import_transforms import normalize_strong1_runs
from nofos.models import Nofo, Subsection
from nofos.nofo import parse_uploaded_file_as_html_string
from nofos.nofo_markdown import md

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def strong1_docx(properties="", *, style_name="Strong1", style_id="CustomBold"):
    """Synthetic content in a real DOCX package; no user document is committed."""
    fixture = Path(__file__).parents[1] / "fixtures/docx/lists.docx"
    body = "".join(
        f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"
        for text in (
            "Opportunity name: Synthetic emphasis test",
            "Opportunity number: TEST-1180",
            "Opdiv: HRSA",
        )
    )
    body += (
        '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
        "<w:r><w:t>Step 1: Review the opportunity</w:t></w:r></w:p>"
        '<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr>'
        "<w:r><w:t>Summary</w:t></w:r></w:p>"
        f'<w:p><w:r><w:rPr><w:rStyle w:val="{style_id}"/>{properties}'
        "</w:rPr><w:t>Applicant requirements</w:t></w:r></w:p>"
    )
    document = f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'
    styles = (
        f'<w:styles xmlns:w="{W}">'
        '<w:style w:type="paragraph" w:styleId="Heading1">'
        '<w:name w:val="heading 1"/></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading2">'
        '<w:name w:val="heading 2"/></w:style>'
        f'<w:style w:type="character" w:styleId="{style_id}">'
        f'<w:name w:val="{style_name}"/><w:rPr><w:b/></w:rPr>'
        "</w:style></w:styles>"
    )
    output = BytesIO()
    with ZipFile(fixture) as source, ZipFile(output, "w") as target:
        for entry in source.infolist():
            data = source.read(entry)
            if entry.filename == "word/document.xml":
                data = document.encode()
            elif entry.filename == "word/styles.xml":
                data = styles.encode()
            target.writestr(entry, data)
    return SimpleUploadedFile("strong1.docx", output.getvalue(), content_type=MIME)


def rendered(html):
    return BeautifulSoup(
        markdown.markdown(md(html), extensions=["extra"]), "html.parser"
    )


class Strong1ConversionTests(TestCase):
    def convert(self, properties="", **kwargs):
        html, warnings = parse_uploaded_file_as_html_string(
            strong1_docx(properties, **kwargs)
        )
        self.assertEqual(warnings, 0)
        return BeautifulSoup(html, "html.parser"), rendered(html)

    def test_style_only_is_bold_without_italics_or_visible_markers(self):
        source, result = self.convert()
        for soup in (source, result):
            self.assertEqual(soup.strong.get_text(), "Applicant requirements")
            self.assertIsNone(soup.find("em"))
            self.assertNotIn("*", soup.get_text())

    def test_explicit_bold_does_not_duplicate_style_bold(self):
        for properties in ("<w:b/>", '<w:b w:val="1"/>', '<w:b w:val="true"/>'):
            with self.subTest(properties=properties):
                source, result = self.convert(properties)
                self.assertEqual(len(source.find_all("strong")), 1)
                self.assertEqual(len(result.find_all("strong")), 1)
                self.assertIsNone(result.find("em"))
                self.assertNotIn("****", md(str(source)))
                self.assertNotIn("*", result.get_text())

    def test_explicit_bold_off_is_preserved(self):
        for value in ("0", "false", "off"):
            with self.subTest(value=value):
                source, result = self.convert(f'<w:b w:val="{value}"/>')
                for soup in (source, result):
                    self.assertIsNone(soup.find("strong"))
                    self.assertIn("Applicant requirements", soup.get_text())

    def test_intentional_italics_survive_with_and_without_bold(self):
        for properties, bold in (
            ("<w:i/>", True),
            ('<w:b w:val="0"/><w:i/>', False),
        ):
            with self.subTest(properties=properties):
                source, result = self.convert(properties)
                for soup in (source, result):
                    self.assertEqual(soup.em.get_text(), "Applicant requirements")
                    self.assertEqual(soup.find("strong") is not None, bold)
                    self.assertNotIn("*", soup.get_text())

    def test_style_name_not_style_id_controls_matching(self):
        self.convert(style_id="LocalizedCharacterStyle")
        upload = strong1_docx(style_name="Unrelated", style_id="Strong1")
        self.assertIs(normalize_strong1_runs(upload), upload)

    def test_source_upload_and_unrelated_zip_members_are_unchanged(self):
        upload = strong1_docx()
        original = upload.read()
        normalized = normalize_strong1_runs(upload)
        with ZipFile(BytesIO(original)) as before, ZipFile(normalized) as after:
            for name in before.namelist():
                if name != "word/document.xml":
                    self.assertEqual(before.read(name), after.read(name))
        upload.seek(0)
        self.assertEqual(upload.read(), original)

    def test_normalization_is_idempotent(self):
        first = normalize_strong1_runs(strong1_docx())
        self.assertIs(normalize_strong1_runs(first), first)

    def test_native_note_runs_are_normalized_too(self):
        output = BytesIO()
        with ZipFile(strong1_docx()) as source, ZipFile(output, "w") as target:
            for entry in source.infolist():
                if entry.filename not in ("word/footnotes.xml", "word/endnotes.xml"):
                    target.writestr(entry, source.read(entry))
            for name in ("footnotes", "endnotes"):
                target.writestr(
                    f"word/{name}.xml",
                    f'<w:{name} xmlns:w="{W}"><w:r><w:rPr>'
                    '<w:rStyle w:val="CustomBold"/></w:rPr>'
                    f"<w:t>Citation</w:t></w:r></w:{name}>",
                )
        with ZipFile(normalize_strong1_runs(BytesIO(output.getvalue()))) as result:
            for name in ("footnotes", "endnotes"):
                xml = result.read(f"word/{name}.xml")
                self.assertIn(b"<w:b/>", xml)
                self.assertNotIn(b"w:rStyle", xml)

    def test_html_upload_is_not_rewritten_by_word_style_handling(self):
        html = "<h1>Program</h1><p>Plain text</p>"
        result, warnings = parse_uploaded_file_as_html_string(
            SimpleUploadedFile("source.html", html.encode(), content_type="text/html")
        )
        self.assertEqual(result, html)
        self.assertEqual(warnings, 0)


class RedundantBoldConversionTests(SimpleTestCase):
    def test_nested_bold_renders_once_in_body_and_table_headers(self):
        for outer in ("strong", "b"):
            for inner in ("strong", "b"):
                for wrapper in (
                    "<p>{}</p>",
                    "<table><tr><th>{}</th></tr><tr><td>Body</td></tr></table>",
                ):
                    with self.subTest(outer=outer, inner=inner, wrapper=wrapper):
                        html = wrapper.format(
                            f"<{outer}><{inner}>Component</{inner}></{outer}>"
                        )
                        result = rendered(html)
                        self.assertEqual(result.strong.get_text(), "Component")
                        self.assertEqual(len(result.find_all("strong")), 1)
                        self.assertIsNone(result.find("em"))
                        self.assertNotIn("*", result.get_text())
                        self.assertNotIn("****", md(html))

    def test_nested_bold_preserves_italic_portion_and_surrounding_bold(self):
        result = rendered(
            "<p><strong>Before <em><strong>italic</strong></em> after</strong></p>"
        )
        self.assertEqual(result.strong.get_text(), "Before italic after")
        self.assertEqual(result.em.get_text(), "italic")
        self.assertNotIn("*", result.get_text())

    def test_literal_asterisk_in_table_header_is_preserved(self):
        result = rendered(
            "<table><tr><th><strong><strong>Included in page limit*?"
            "</strong></strong></th></tr><tr><td>Yes</td></tr></table>"
        )
        self.assertEqual(result.th.get_text(), "Included in page limit*?")
        self.assertIsNone(result.find("em"))


class Strong1ImportReimportTests(TestCase):
    def test_composer_uses_shared_word_style_handling(self):
        user = BloomUser.objects.create_user(
            email="strong1-composer@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
            is_composer_admin=True,
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("composer:composer_import"), {"nofo-import": strong1_docx("<w:i/>")}
        )
        self.assertEqual(response.status_code, 302)
        summary = ContentGuideSubsection.objects.get(name="Summary")
        result = BeautifulSoup(
            markdown.markdown(summary.body, extensions=["extra"]), "html.parser"
        )
        self.assertEqual(result.strong.get_text(), "Applicant requirements")
        self.assertEqual(result.em.get_text(), "Applicant requirements")
        self.assertNotIn("*", result.get_text())

    def test_import_and_reimport_across_opdiv_groups(self):
        for group in ("hrsa", "cdc", "nih", "acf"):
            with self.subTest(group=group):
                user = BloomUser.objects.create_user(
                    email=f"strong1-{group}@example.com",
                    password="testpass123",
                    group=group,
                    force_password_reset=False,
                )
                self.client.force_login(user)
                response = self.client.post(
                    reverse("nofos:nofo_import"), {"nofo-import": strong1_docx()}
                )
                self.assertEqual(response.status_code, 302)
                nofo = Nofo.objects.get(group=group, successor__isnull=True)
                summary = Subsection.objects.get(section__nofo=nofo, name="Summary")
                self.assertEqual(summary.body.strip(), "**Applicant requirements**")
                response = self.client.post(
                    reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk}),
                    {"nofo-import": strong1_docx('<w:b w:val="0"/><w:i/>')},
                )
                self.assertEqual(response.status_code, 302)
                summary = Subsection.objects.get(section__nofo=nofo, name="Summary")
                self.assertEqual(summary.body.strip(), "*Applicant requirements*")
                archive = Nofo.objects.get(successor=nofo)
                self.assertEqual(
                    Subsection.objects.get(
                        section__nofo=archive, name="Summary"
                    ).body.strip(),
                    "**Applicant requirements**",
                )
