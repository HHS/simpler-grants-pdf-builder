"""Original DOCX structure, not title text, controls Builder-only omission."""

from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.import_transforms import omit_leading_word_title
from nofos.models import Nofo, Subsection
from nofos.nofo import parse_uploaded_file_as_html_string

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def paragraph(text, style="Normal"):
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr><w:r><w:t>{text}</w:t></w:r></w:p>'


def title_docx(body, extra_styles="", title_style_id="Title"):
    """Keep a real DOCX package, replace only synthetic body/style definitions."""
    fixture = Path(__file__).parents[1] / "fixtures/docx/lists.docx"
    output = BytesIO()
    document = (
        f'<w:document xmlns:w="{W}"><w:body>{body}<w:sectPr/></w:body></w:document>'
    )
    styles = f'<w:styles xmlns:w="{W}"><w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/></w:style><w:style w:type="paragraph" w:styleId="{title_style_id}"><w:name w:val="Title"/></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style><w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/></w:style>{extra_styles}</w:styles>'
    with ZipFile(fixture) as source, ZipFile(output, "w") as target:
        for entry in source.infolist():
            data = source.read(entry)
            if entry.filename == "word/document.xml":
                data = document.encode()
            elif entry.filename == "word/styles.xml":
                data = styles.encode()
            target.writestr(entry, data)
    return SimpleUploadedFile(
        "synthetic-leading-title.docx", output.getvalue(), content_type=MIME
    )


def template(leading="", body="Applicant content."):
    return title_docx(
        leading
        + paragraph("Opportunity name: Applicant opportunity")
        + paragraph("Opportunity number: TEST-1094")
        + paragraph("Opdiv: CDC")
        + paragraph("Step 1: Review the opportunity", "Heading1")
        + paragraph("Summary", "Heading2")
        + paragraph(body)
    )


class LeadingTitleConversionTests(TestCase):
    def test_title_wording_and_case_do_not_control_removal(self):
        for text in (
            "HHS-WIDE NOFO MASTER TEMPLATE",
            "Other source heading",
            "Mixed Case",
            "Opportunity name: Wrong metadata",
            "",
        ):
            with self.subTest(text=text):
                upload = template(paragraph(text, "Title"))
                html, warnings = parse_uploaded_file_as_html_string(
                    upload, omit_leading_title=True
                )
                self.assertTrue(
                    html.startswith("<p>Opportunity name: Applicant opportunity</p>")
                )
                self.assertEqual(warnings, 0)

    def test_later_titles_and_surrounding_content_are_preserved(self):
        body = (
            paragraph("Remove only this", "Title")
            + paragraph("Opdiv: CDC")
            + paragraph("Step 1", "Heading1")
            + paragraph("Later Title", "Title")
        )
        body += (
            "<w:tbl><w:tr><w:tc>" + paragraph("Kept table") + "</w:tc></w:tr></w:tbl>"
        )
        body += '<w:p><w:hyperlink w:anchor="kept"><w:r><w:t>Kept link</w:t></w:r></w:hyperlink><w:bookmarkStart w:id="1" w:name="kept"/><w:bookmarkEnd w:id="1"/></w:p>'
        upload = title_docx(body)
        original = upload.read()
        result = omit_leading_word_title(upload)
        with ZipFile(result) as transformed, ZipFile(BytesIO(original)) as source:
            xml = transformed.read("word/document.xml")
            self.assertNotIn(b"Remove only this", xml)
            for text in (
                b"Opdiv: CDC",
                b"Later Title",
                b"Kept table",
                b"Kept link",
                b'anchor="kept"',
                b"bookmarkStart",
            ):
                self.assertIn(text, xml)
            for name in source.namelist():
                if name != "word/document.xml":
                    self.assertEqual(source.read(name), transformed.read(name))
        upload.seek(0)
        self.assertEqual(upload.read(), original)

    def test_do_not_scan_past_blank_table_drawing_or_other_content(self):
        prefixes = (
            "<w:p/>",
            paragraph("First ordinary paragraph"),
            "<w:tbl><w:tr><w:tc>" + paragraph("Table first") + "</w:tc></w:tr></w:tbl>",
            "<w:p><w:r><w:drawing/></w:r></w:p>",
            "<w:customXml><w:p/></w:customXml>",
        )
        for prefix in prefixes:
            with self.subTest(prefix=prefix):
                upload = title_docx(prefix + paragraph("Later Title", "Title"))
                self.assertIs(omit_leading_word_title(upload), upload)
                html, _ = parse_uploaded_file_as_html_string(
                    upload, omit_leading_title=True
                )
                self.assertIn("Later Title", html)

    def test_heading_manual_font_character_style_and_inherited_style_are_not_title(
        self,
    ):
        candidates = (
            paragraph("Keep heading", "Heading1"),
            '<w:p><w:r><w:rPr><w:b/><w:sz w:val="48"/></w:rPr><w:t>Keep enlarged bold</w:t></w:r></w:p>',
            '<w:p><w:r><w:rPr><w:rStyle w:val="TitleChar"/></w:rPr><w:t>Keep run Title</w:t></w:r></w:p>',
            paragraph("Keep derived style", "DerivedTitle"),
        )
        styles = '<w:style w:type="character" w:styleId="TitleChar"><w:name w:val="Title"/></w:style><w:style w:type="paragraph" w:styleId="DerivedTitle"><w:name w:val="Custom title"/><w:basedOn w:val="Title"/></w:style>'
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                upload = title_docx(candidate, extra_styles=styles)
                self.assertIs(omit_leading_word_title(upload), upload)

    def test_style_definition_not_style_id_determines_title(self):
        upload = title_docx(
            paragraph("Remove renamed ID", "LocalizedTitle"),
            title_style_id="LocalizedTitle",
        )
        with ZipFile(omit_leading_word_title(upload)) as result:
            self.assertNotIn(b"Remove renamed ID", result.read("word/document.xml"))

    def test_missing_or_non_title_style_definition_does_not_qualify(self):
        for definition in (
            '<w:style w:type="paragraph" w:styleId="Lookalike"><w:name w:val="Custom title"/></w:style>',
            '<w:style w:type="character" w:styleId="Lookalike"><w:name w:val="Title"/></w:style>',
            "",
        ):
            with self.subTest(definition=definition):
                upload = title_docx(
                    paragraph("Keep Title lookalike", "Lookalike"),
                    extra_styles=definition,
                )
                self.assertIs(omit_leading_word_title(upload), upload)

    def test_section_properties_do_not_count_as_content(self):
        upload = title_docx("<w:sectPr/>" + paragraph("Remove first content", "Title"))
        with ZipFile(omit_leading_word_title(upload)) as result:
            self.assertNotIn(b"Remove first content", result.read("word/document.xml"))

    def test_drawing_inside_leading_title_is_preserved(self):
        upload = title_docx(
            '<w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:r><w:t>Title with graphic</w:t><w:drawing/></w:r></w:p>'
        )
        self.assertIs(omit_leading_word_title(upload), upload)

    def test_empty_document_and_legacy_without_title_are_unchanged(self):
        for upload in (title_docx(""), template()):
            self.assertIs(omit_leading_word_title(upload), upload)

    def test_shared_conversion_default_preserves_leading_title(self):
        html, _ = parse_uploaded_file_as_html_string(
            template(paragraph("Shared caller Title", "Title"))
        )
        self.assertIn("Shared caller Title", html)

    def test_html_is_unchanged_even_when_builder_opted_in(self):
        source = '<p class="Title">HTML Title</p><h1>Program</h1><p>Body</p>'
        html, warnings = parse_uploaded_file_as_html_string(
            SimpleUploadedFile(
                "synthetic.html", source.encode(), content_type="text/html"
            ),
            omit_leading_title=True,
        )
        self.assertEqual(html, source)
        self.assertEqual(warnings, 0)


class LeadingTitleBuilderImportTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="title-review@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.force_login(self.user)

    def imported(self):
        response = self.client.post(
            reverse("nofos:nofo_import"),
            {
                "nofo-import": template(
                    paragraph("Opportunity name: Template identity", "Title")
                )
            },
        )
        self.assertEqual(response.status_code, 302)
        nofo = Nofo.objects.get()
        self.assertEqual(nofo.title, "Applicant opportunity")
        self.assertEqual(nofo.number, "TEST-1094")
        self.assertEqual(nofo.opdiv, "CDC")
        return nofo

    def test_new_word_import_omits_title_without_metadata_inference_or_alert(self):
        nofo = self.imported()
        self.assertNotIn(
            "Template identity",
            str(
                list(
                    Subsection.objects.filter(section__nofo=nofo).values_list(
                        "body", flat=True
                    )
                )
            ),
        )
        self.assertEqual(nofo.import_attempts.get().warning_count, 0)

    def test_authorized_reimport_uses_incoming_structure_and_keeps_archive(self):
        nofo = self.imported()
        response = self.client.post(
            reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk}),
            {
                "nofo-import": template(
                    paragraph("Remove incoming source title", "Title"),
                    body="Updated content.",
                )
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            "Updated content.",
            Subsection.objects.get(section__nofo=nofo, name="Summary").body,
        )
        self.assertNotIn(
            "Remove incoming",
            str(
                list(
                    Subsection.objects.filter(section__nofo=nofo).values_list(
                        "body", flat=True
                    )
                )
            ),
        )
        archive = Nofo.objects.get(successor=nofo)
        self.assertIn(
            "Applicant content.",
            Subsection.objects.get(section__nofo=archive, name="Summary").body,
        )

    def test_failed_reimport_rolls_back_archive_and_saved_content(self):
        nofo = self.imported()
        before = list(
            Subsection.objects.filter(section__nofo=nofo).values_list("pk", "body")
        )
        with patch(
            "nofos.views.add_headings_to_document",
            side_effect=RuntimeError("synthetic failure"),
        ):
            response = self.client.post(
                reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk}),
                {
                    "nofo-import": template(
                        paragraph("Incoming title", "Title"), body="Must roll back."
                    )
                },
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(Nofo.objects.count(), 1)
        self.assertEqual(
            list(
                Subsection.objects.filter(section__nofo=nofo).values_list("pk", "body")
            ),
            before,
        )

    def test_reimport_status_and_group_restrictions_still_apply(self):
        nofo = self.imported()
        before = list(
            Subsection.objects.filter(section__nofo=nofo).values_list("pk", "body")
        )
        for field, value in (("status", "published"), ("group", "hrsa")):
            with self.subTest(field=field):
                if field == "group":
                    self.user.group = "cdc"
                    self.user.save(update_fields=["group"])
                setattr(nofo, field, value)
                nofo.save(update_fields=[field])
                response = self.client.post(
                    reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk}),
                    {"nofo-import": template(paragraph("Incoming title", "Title"))},
                )
                self.assertEqual(
                    response.status_code, 400 if field == "status" else 403
                )
                self.assertEqual(Nofo.objects.count(), 1)
                self.assertEqual(
                    list(
                        Subsection.objects.filter(section__nofo=nofo).values_list(
                            "pk", "body"
                        )
                    ),
                    before,
                )
                setattr(nofo, field, "draft" if field == "status" else "bloom")
                nofo.save(update_fields=[field])

    def test_view_does_not_clean_existing_saved_title_content(self):
        nofo = self.imported()
        summary = Subsection.objects.get(section__nofo=nofo, name="Summary")
        summary.body = "Existing saved Title paragraph"
        summary.save()
        response = self.client.get(reverse("nofos:nofo_edit", kwargs={"pk": nofo.pk}))
        self.assertEqual(response.status_code, 200)
        summary.refresh_from_db()
        self.assertEqual(summary.body, "Existing saved Title paragraph")
