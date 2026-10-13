"""Synthetic DOCX fixtures: no private master or agency content is committed."""

from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from bs4 import BeautifulSoup
from composer.models import ContentGuideSubsection
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, Subsection
from nofos.nofo import parse_uploaded_file_as_html_string, process_nofo_html
from nofos.word_instruction_boxes import REVIEW_MESSAGE, clean_instruction_boxes

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "v": "urn:schemas-microsoft-com:vml",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "wpg": "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def paragraph(text, style=""):
    return f'<w:p><w:pPr><w:pStyle w:val="{style or "Normal"}"/></w:pPr><w:r><w:t>{text}</w:t></w:r></w:p>'


def table(text):
    return f"<w:tbl><w:tr><w:tc>{paragraph(text)}</w:tc></w:tr></w:tbl>"


def box(text="Instruction box text", fill=None, vml=False):
    content = paragraph(text) + paragraph("Remove this entire box too.")
    if vml:
        return f'<w:pict><v:shape {fill or ""}><v:textbox><w:txbxContent>{content}</w:txbxContent></v:textbox></v:shape></w:pict>'
    fill = (
        fill
        if fill is not None
        else '<a:solidFill><a:schemeClr val="tx2"><a:lumMod val="10000"/><a:lumOff val="90000"/></a:schemeClr></a:solidFill>'
    )
    return f"<w:drawing><wps:wsp><wps:spPr>{fill}</wps:spPr><wps:txbx><w:txbxContent>{content}</w:txbxContent></wps:txbx></wps:wsp></w:drawing>"


def alternate(
    text="Instruction box text", modern=None, legacy='fillcolor="#dceaf7 [351]"'
):
    return f'<mc:AlternateContent><mc:Choice Requires="wps">{box(text, modern)}</mc:Choice><mc:Fallback>{box(text, legacy, True)}</mc:Fallback></mc:AlternateContent>'


def docx(body, theme_color="0E2841", mapping="dark2", extra_mappings=""):
    base = Path(settings.BASE_DIR) / "nofos/fixtures/docx/lists.docx"
    result = BytesIO()
    namespace = " ".join(f'xmlns:{prefix}="{uri}"' for prefix, uri in NS.items())
    document = f'<w:document {namespace} mc:Ignorable="wps"><w:body>{body}</w:body></w:document>'
    with ZipFile(base) as source, ZipFile(result, "w") as target:
        for entry in source.infolist():
            data = source.read(entry)
            if entry.filename == "word/document.xml":
                data = document.encode()
            elif entry.filename == "word/theme/theme1.xml":
                data = f'<a:theme xmlns:a="{NS["a"]}"><a:themeElements><a:clrScheme name="Synthetic"><a:dk2><a:srgbClr val="{theme_color}"/></a:dk2><a:lt2><a:srgbClr val="FFFFFF"/></a:lt2><a:accent1><a:srgbClr val="DCEAF7"/></a:accent1><a:accent2><a:srgbClr val="FFFFFF"/></a:accent2><a:hlink><a:srgbClr val="DCEAF7"/></a:hlink><a:folHlink><a:srgbClr val="FFFFFF"/></a:folHlink></a:clrScheme></a:themeElements></a:theme>'.encode()
            elif entry.filename == "word/settings.xml":
                data = f'<w:settings xmlns:w="{NS["w"]}"><w:clrSchemeMapping w:t2="{mapping}" {extra_mappings}/></w:settings>'.encode()
            target.writestr(entry, data)
    return SimpleUploadedFile("synthetic.docx", result.getvalue(), content_type=MIME)


def template(new, replacement="Applicant-facing content."):
    body = (
        paragraph("Opportunity name: Synthetic import review")
        + paragraph("Opportunity number: TEST-1089")
        + paragraph("Opdiv: CDC")
    )
    body += paragraph("Step 1: Review the opportunity", "Heading1")
    body += (
        '<w:p><w:bookmarkStart w:id="1" w:name="kept"/><w:bookmarkEnd w:id="1"/></w:p>'
    )
    body += paragraph("Summary", "Heading2") + paragraph(replacement)
    instructions = "Instructions for NOFO writers: Summary"
    body += (
        f"<w:p><w:r>{alternate(instructions)}</w:r></w:p>"
        if new
        else f'<w:tbl><w:tr><w:tc>{paragraph(instructions)}{paragraph("Writer guidance.")}</w:tc></w:tr></w:tbl>'
    )
    for title in ("Have questions?", "Application due date", "Key facts", "Need help?"):
        body += f'<w:tbl><w:tr><w:tc>{paragraph(title, "Heading3")}<w:p><w:hyperlink w:anchor="kept"><w:r><w:t>Applicant instructions and contact link</w:t></w:r></w:hyperlink></w:p></w:tc></w:tr></w:tbl>'
    body += paragraph("Requirements", "Heading2") + paragraph("Remaining prose.")
    return docx(body)


def repackage(upload, edits):
    result = BytesIO()
    with ZipFile(upload) as source, ZipFile(result, "w") as target:
        for entry in source.infolist():
            data = source.read(entry)
            if entry.filename in edits:
                data = edits[entry.filename](data)
            target.writestr(entry, data)
    return SimpleUploadedFile("synthetic.docx", result.getvalue(), content_type=MIME)


class InstructionBoxConversionTests(TestCase):
    def test_compatibility_link_ids_resolve_to_same_destination(self):
        modern = box().replace(
            "</w:txbxContent>",
            '<w:p><w:hyperlink r:id="rId9000" w:history="1"><w:r><w:t>Reference</w:t></w:r></w:hyperlink></w:p></w:txbxContent>',
        )
        legacy = box(fill='fillcolor="#DCEAF7"', vml=True).replace(
            "</w:txbxContent>",
            '<w:p><w:hyperlink r:id="rId9001" w:history="0"><w:r><w:t>Reference</w:t></w:r></w:hyperlink></w:p></w:txbxContent>',
        )
        unit = f'<mc:AlternateContent><mc:Choice Requires="wps">{modern}</mc:Choice><mc:Fallback>{legacy}</mc:Fallback></mc:AlternateContent>'
        upload = docx("<w:p><w:r>" + unit + "</w:r></w:p>")
        additions = b'<Relationship Id="rId9000" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://example.org/reference" TargetMode="External"/><Relationship Id="rId9001" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://example.org/reference" TargetMode="External"/>'
        upload = repackage(
            upload,
            {
                "word/_rels/document.xml.rels": lambda data: data.replace(
                    b"</Relationships>", additions + b"</Relationships>"
                )
            },
        )
        xml, warnings = self.cleaned(upload)
        self.assertNotIn(b"Instruction box text", xml)
        self.assertEqual(warnings, ())

    def test_theme_level_transforms_are_unknown_not_untransformed_blue(self):
        fill = '<a:solidFill><a:schemeClr val="accent1"/></a:solidFill>'
        upload = docx("<w:p><w:r>" + box("Applicant box", fill) + "</w:r></w:p>")
        upload = repackage(
            upload,
            {
                "word/theme/theme1.xml": lambda data: data.replace(
                    b'<a:accent1><a:srgbClr val="DCEAF7"/>',
                    b'<a:accent1><a:srgbClr val="DCEAF7"><a:lumOff val="100000"/></a:srgbClr>',
                )
            },
        )
        xml, warnings = self.cleaned(upload)
        self.assertIn(b"Applicant box", xml)
        self.assertEqual(warnings, (REVIEW_MESSAGE,))

    def test_grouped_independent_boxes_with_same_text_keep_both_links(self):
        shapes = []
        for anchor in ("first-program", "second-program"):
            shape = box("Application instructions", "<a:noFill/>")
            shape = shape.removeprefix("<w:drawing>").removesuffix("</w:drawing>")
            shape = shape.replace(
                "</w:txbxContent>",
                f'<w:p><w:hyperlink w:anchor="{anchor}"><w:r><w:t>Program link</w:t></w:r></w:hyperlink></w:p></w:txbxContent>',
            )
            shapes.append(shape)
        upload = docx(
            "<w:p><w:r><w:drawing><wpg:wgp>"
            + "".join(shapes)
            + "</wpg:wgp></w:drawing></w:r></w:p>"
        )
        html, _ = parse_uploaded_file_as_html_string(upload)
        self.assertEqual(html.count("Application instructions"), 2)
        self.assertEqual(html.count('href="#first-program"'), 1)
        self.assertEqual(html.count('href="#second-program"'), 1)

    def test_inserted_copy_reuses_nonstandard_word_namespace_prefix(self):
        upload = docx(
            "<w:p><w:r>"
            + box("Preserved applicant prose", "<a:noFill/>")
            + "</w:r></w:p>"
        )
        upload = repackage(
            upload,
            {
                "word/document.xml": lambda data: data.replace(
                    b"xmlns:w=", b"xmlns:doc="
                )
                .replace(b"<w:", b"<doc:")
                .replace(b"</w:", b"</doc:")
                .replace(b" w:", b" doc:")
            },
        )
        html, _ = parse_uploaded_file_as_html_string(upload)
        self.assertIn("Preserved applicant prose", html)

    def test_accent_and_hyperlink_mappings_resolve_actual_white_fill(self):
        for slot, attributes in (
            ("accent1", 'w:accent1="accent2"'),
            ("hlink", 'w:hyperlink="followedHyperlink"'),
        ):
            with self.subTest(slot=slot):
                fill = f'<a:solidFill><a:schemeClr val="{slot}"/></a:solidFill>'
                xml, warnings = self.cleaned(
                    docx(
                        "<w:p><w:r>"
                        + box("Applicant-facing box", fill)
                        + "</w:r></w:p>",
                        extra_mappings=attributes,
                    )
                )
                self.assertIn(b"Applicant-facing box", xml)
                self.assertEqual(warnings, ())

    def test_tint_boundaries_use_retained_source_fraction(self):
        for amount, removed in (("0", False), ("100000", True)):
            with self.subTest(amount=amount):
                fill = f'<a:solidFill><a:srgbClr val="DCEAF7"><a:tint val="{amount}"/></a:srgbClr></a:solidFill>'
                xml, warnings = self.cleaned(
                    docx(
                        "<w:p><w:r>"
                        + box("Applicant-facing box", fill)
                        + "</w:r></w:p>"
                    )
                )
                self.assertEqual(b"Applicant-facing box" not in xml, removed)
                self.assertEqual(warnings, ())

    def test_mixed_old_new_and_option_labels_do_not_remove_following_content(self):
        body = paragraph("Step 3", "Heading1") + table(
            "Instructions for NOFO writers: Summary"
        )
        body += "<w:p><w:r>" + alternate("Option 1 label") + "</w:r></w:p>"
        body += paragraph("Option 1 applicant content") + paragraph(
            "Option 2 applicant content"
        )
        html, _ = parse_uploaded_file_as_html_string(docx(body))
        soup, removed = process_nofo_html(BeautifulSoup(html, "html.parser"), "h1")
        self.assertEqual(len(removed), 1)
        self.assertNotIn("Option 1 label", str(soup))
        self.assertIn("Option 1 applicant content", str(soup))
        self.assertIn("Option 2 applicant content", str(soup))

    def test_retained_drawingml_content_reaches_converter_with_links(self):
        for fill in (
            "<a:noFill/>",
            '<a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill>',
            "<a:gradFill/>",
        ):
            unit = box("Applicant instructions", fill).replace(
                "Remove this entire box too.", "Keep applicant prose."
            )
            unit = unit.replace(
                "</w:txbxContent>",
                '<w:p><w:hyperlink w:anchor="target"><w:r><w:t>Keep link</w:t></w:r></w:hyperlink></w:p></w:txbxContent>',
            )
            html, _ = parse_uploaded_file_as_html_string(
                docx("<w:p><w:r>" + unit + "</w:r></w:p>")
            )
            self.assertIn("Applicant instructions", html)
            self.assertIn("Keep applicant prose", html)
            self.assertIn('href="#target"', html)

    def test_ambiguous_container_keeps_adjacent_bookmark_and_rejects_entities(self):
        unit = alternate().replace(
            '<mc:Choice Requires="wps">',
            '<mc:Choice Requires="wps"><w:bookmarkStart w:id="1" w:name="keep"/>',
        )
        xml, warnings = self.cleaned(docx("<w:p><w:r>" + unit + "</w:r></w:p>"))
        self.assertIn(b"bookmarkStart", xml)
        self.assertIn(b"Instruction box text", xml)
        self.assertEqual(warnings, (REVIEW_MESSAGE,))
        from nofos.word_instruction_boxes import _xml

        with self.assertRaises(ValueError):
            _xml(b'<!DOCTYPE x [<!ENTITY y "hidden">]><x>&y;</x>')

    def cleaned(self, upload):
        result, warnings = clean_instruction_boxes(upload)
        with ZipFile(result) as archive:
            xml = archive.read("word/document.xml")
        return xml, warnings

    def test_compatibility_container_removed_without_adjacent_text_or_bookmarks(self):
        upload = docx(
            '<w:p><w:bookmarkStart w:id="1" w:name="kept"/><w:r><w:t>Keep heading and link</w:t>'
            + alternate()
            + '</w:r><w:bookmarkEnd w:id="1"/></w:p>'
        )
        original = upload.read()
        xml, warnings = self.cleaned(upload)
        self.assertNotIn(b"txbxContent", xml)
        self.assertNotIn(b"Remove this entire box", xml)
        self.assertIn(b"Keep heading and link", xml)
        self.assertIn(b"bookmarkStart", xml)
        self.assertIn(b'mc:Ignorable="wps"', xml)
        self.assertEqual(warnings, ())
        upload.seek(0)
        self.assertEqual(upload.read(), original)

    def test_theme_mapping_actual_color_not_literal_tx2(self):
        xml, warnings = self.cleaned(
            docx("<w:p><w:r>" + box() + "</w:r></w:p>", theme_color="EE2222")
        )
        self.assertIn(b"Instruction box text", xml)
        self.assertEqual(warnings, (REVIEW_MESSAGE,))
        xml, warnings = self.cleaned(
            docx("<w:p><w:r>" + box() + "</w:r></w:p>", mapping="light2")
        )
        self.assertIn(b"Instruction box text", xml)
        self.assertEqual(warnings, ())

    def test_direct_color_tint_shade_and_standalone_legacy(self):
        for fill in (
            '<a:solidFill><a:srgbClr val="DCEAF7"/></a:solidFill>',
            '<a:solidFill><a:srgbClr val="B9D5EF"><a:tint val="50000"/></a:srgbClr></a:solidFill>',
            '<a:solidFill><a:srgbClr val="DCEAF7"><a:shade val="100000"/></a:srgbClr></a:solidFill>',
        ):
            with self.subTest(fill=fill):
                xml, warnings = self.cleaned(
                    docx("<w:p><w:r>" + box(fill=fill) + "</w:r></w:p>")
                )
                self.assertNotIn(b"txbxContent", xml)
                self.assertEqual(warnings, ())
        xml, _ = self.cleaned(
            docx(
                "<w:p><w:r>"
                + box(fill='fillcolor="#DCEAF7"', vml=True)
                + "</w:r></w:p>"
            )
        )
        self.assertNotIn(b"txbxContent", xml)

    def test_white_unfilled_transparent_and_instruction_like_content_survive(self):
        fills = (
            '<a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill>',
            "<a:noFill/>",
            "",
            '<a:solidFill><a:srgbClr val="DCEAF7"><a:alpha val="0"/></a:srgbClr></a:solidFill>',
        )
        for fill in fills:
            with self.subTest(fill=fill):
                xml, warnings = self.cleaned(
                    docx(
                        "<w:p><w:r>"
                        + box("Applicant instructions", fill)
                        + "</w:r></w:p>"
                    )
                )
                self.assertIn(b"Applicant instructions", xml)
                self.assertEqual(warnings, ())
        for fill in ('filled="f" fillcolor="#DCEAF7"', 'fillcolor="#FFFFFF"', ""):
            xml, warnings = self.cleaned(
                docx(
                    "<w:p><w:r>"
                    + box("Applicant instructions", fill, True)
                    + "</w:r></w:p>"
                )
            )
            self.assertIn(b"Applicant instructions", xml)
            self.assertEqual(warnings, ())

    def test_unknown_conflicting_or_partial_transparency_preserved(self):
        for unit in (
            alternate(legacy='fillcolor="#FFFFFF"'),
            box(fill="<a:gradFill/>"),
            box(fill='<a:solidFill><a:schemeClr val="unknown"/></a:solidFill>'),
            box(
                fill='<a:solidFill><a:srgbClr val="DCEAF7"><a:alpha val="50000"/></a:srgbClr></a:solidFill>'
            ),
        ):
            with self.subTest(unit=unit):
                xml, warnings = self.cleaned(docx("<w:p><w:r>" + unit + "</w:r></w:p>"))
                self.assertIn(b"Instruction box text", xml)
                self.assertEqual(warnings, (REVIEW_MESSAGE,))

    def test_old_tables_and_four_content_callouts_unchanged(self):
        for new in (False, True):
            html, _ = parse_uploaded_file_as_html_string(template(new))
            soup, removed = process_nofo_html(BeautifulSoup(html, "html.parser"), "h1")
            self.assertNotIn("Instructions for NOFO writers", str(soup))
            self.assertEqual(len(removed), 0 if new else 1)
            for title in (
                "Have questions?",
                "Application due date",
                "Key facts",
                "Need help?",
            ):
                self.assertIn(title, soup.get_text())
            self.assertEqual(len(soup.select('a[href="#kept"]')), 4)

    def test_composer_conversion_opt_out_keeps_guidance_and_legacy_extraction(self):
        html, _ = parse_uploaded_file_as_html_string(
            template(True), remove_instruction_boxes=False
        )
        self.assertIn("Instructions for NOFO writers", html)
        html, _ = parse_uploaded_file_as_html_string(
            template(False), remove_instruction_boxes=False
        )
        _, removed = process_nofo_html(BeautifulSoup(html, "html.parser"), "h1")
        self.assertEqual(len(removed), 1)


class InstructionBoxImportWorkflowTests(TestCase):
    def setUp(self):
        user = BloomUser.objects.create_user(
            email="instruction-review@example.com",
            password="synthetic-test",
            group="bloom",
            force_password_reset=False,
            is_composer_admin=True,
        )
        self.client.force_login(user)

    def imported(self, new):
        response = self.client.post(
            reverse("nofos:nofo_import"), {"nofo-import": template(new)}
        )
        self.assertEqual(response.status_code, 302)
        return Nofo.objects.get(archived__isnull=True)

    def assert_content(self, nofo, expected="Applicant-facing content."):
        rows = Subsection.objects.filter(section__nofo=nofo)
        bodies = " ".join(row.body for row in rows)
        self.assertIn(expected, bodies)
        self.assertNotIn("Instructions for NOFO writers", bodies)
        callouts = rows.filter(callout_box=True)
        self.assertEqual(callouts.count(), 4)
        self.assertEqual(
            set(callouts.values_list("name", flat=True)),
            {"Have questions?", "Application due date", "Key facts", "Need help?"},
        )
        self.assertTrue(
            all(
                "Applicant instructions" in row.body and "](#" in row.body
                for row in callouts
            ),
            [row.body for row in callouts],
        )

    def test_new_imports_both_formats_and_all_reimport_transitions(self):
        for old in (False, True):
            for new in (False, True):
                with self.subTest(old=old, new=new):
                    Nofo.objects.all().delete()
                    nofo = self.imported(old)
                    self.assert_content(nofo)
                    identity = (nofo.pk, nofo.number, nofo.group, nofo.before_you_begin)
                    response = self.client.post(
                        reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk}),
                        {"nofo-import": template(new, "Replaced applicant prose.")},
                    )
                    self.assertEqual(response.status_code, 302)
                    nofo.refresh_from_db()
                    self.assertEqual(
                        (nofo.pk, nofo.number, nofo.group, nofo.before_you_begin),
                        identity,
                    )
                    self.assert_content(nofo, "Replaced applicant prose.")

    def test_failed_reimport_and_existing_status_restrictions_preserve_record(self):
        nofo = self.imported(False)
        before = list(Subsection.objects.filter(section__nofo=nofo).values())
        url = reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk})
        bad = SimpleUploadedFile("broken.docx", b"not a zip", content_type=MIME)
        self.assertEqual(self.client.post(url, {"nofo-import": bad}).status_code, 422)
        self.assertEqual(
            list(Subsection.objects.filter(section__nofo=nofo).values()), before
        )
        for status in ("published", "review", "doge", "paused"):
            nofo.status = status
            nofo.save()
            response = self.client.post(url, {"nofo-import": template(True)})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(
                list(Subsection.objects.filter(section__nofo=nofo).values()), before
            )

    def test_open_and_html_export_never_clean_existing_content(self):
        nofo = self.imported(False)
        row = Subsection.objects.filter(section__nofo=nofo).first()
        row.body = "Existing saved instructions and applicant prose."
        row.save()
        before = list(Subsection.objects.filter(section__nofo=nofo).values())
        self.assertEqual(
            self.client.get(
                reverse("nofos:nofo_edit", kwargs={"pk": nofo.pk})
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("nofos:nofo_view", kwargs={"pk": nofo.pk})
            ).status_code,
            200,
        )
        self.assertEqual(
            list(Subsection.objects.filter(section__nofo=nofo).values()), before
        )

    def test_reimport_write_failure_rolls_back_snapshot_and_content(self):
        nofo = self.imported(False)
        before = list(Subsection.objects.filter(section__nofo=nofo).values())
        with patch(
            "nofos.views.overwrite_nofo", side_effect=RuntimeError("synthetic failure")
        ):
            response = self.client.post(
                reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk}),
                {"nofo-import": template(True)},
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(Nofo.objects.count(), 1)
        self.assertEqual(
            list(Subsection.objects.filter(section__nofo=nofo).values()), before
        )

    def test_composer_old_instruction_reattachment_is_unchanged(self):
        response = self.client.post(
            reverse("composer:composer_import"), {"nofo-import": template(False)}
        )
        self.assertEqual(response.status_code, 302)
        row = ContentGuideSubsection.objects.get(name="Summary")
        self.assertIn("Writer guidance", row.instructions)

    def test_unknown_fill_warning_is_shown_after_reimport(self):
        nofo = self.imported(False)
        upload = template(True)
        with ZipFile(upload) as source:
            result = BytesIO()
            with ZipFile(result, "w") as target:
                for entry in source.infolist():
                    data = source.read(entry)
                    if entry.filename == "word/document.xml":
                        data = data.replace(
                            b'fillcolor="#dceaf7 [351]"', b'fillcolor="#FFFFFF"'
                        )
                    target.writestr(entry, data)
        response = self.client.post(
            reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk}),
            {
                "nofo-import": SimpleUploadedFile(
                    "unknown.docx", result.getvalue(), content_type=MIME
                )
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, REVIEW_MESSAGE)
        self.assertIn(
            "Instructions for NOFO writers",
            " ".join(
                Subsection.objects.filter(section__nofo=nofo).values_list(
                    "body", flat=True
                )
            ),
        )

    def test_unknown_fill_surfaces_content_free_review_warning(self):
        body = (
            paragraph("Opdiv: CDC")
            + paragraph("Step 1", "Heading1")
            + paragraph("Summary", "Heading2")
        )
        body += (
            "<w:p><w:r>"
            + box("Unrecognized applicant content", "<a:gradFill/>")
            + "</w:r></w:p>"
        )
        response = self.client.post(
            reverse("nofos:nofo_import"), {"nofo-import": docx(body)}, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, REVIEW_MESSAGE)
        self.assertIn(
            "Unrecognized applicant content",
            " ".join(Subsection.objects.values_list("body", flat=True)),
        )
