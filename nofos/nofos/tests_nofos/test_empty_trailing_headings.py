"""Conservative removal of unused optional tail headings (IMPORT-071)."""

from io import BytesIO
from zipfile import ZipFile

from bs4 import BeautifulSoup
from compare.models import CompareDocument
from composer.models import ContentGuide
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from nofos.content_processing import (
    AmbiguousHeadingHierarchyError,
    ContentProcessingError,
    process_document_content,
    remove_empty_trailing_optional_headings,
)
from nofos.models import Nofo


class EmptyTrailingHeadingTests(SimpleTestCase):
    prefix = "<h1>Opportunity</h1><h2>Summary</h2><p>Applicant content.</p>"

    def test_exact_names_at_either_level_with_spacing_case_and_colon(self):
        for level in ("h1", "h2"):
            for title in ("Appendix", "ENDNOTES", " footnotes : "):
                with self.subTest(level=level, title=title):
                    result = process_document_content(
                        self.prefix + f"<{level}><span>{title}</span></{level}>"
                        "<p>&nbsp;<strong> </strong><br></p><!-- Word placeholder -->"
                    )
                    self.assertEqual(
                        [s["name"] for s in result.sections], ["Opportunity"]
                    )
                    self.assertEqual(
                        [s["name"] for s in result.sections[0]["subsections"]],
                        ["Summary"],
                    )
                    self.assertIn("Applicant content.", str(result.sections))

    def test_multiple_tail_headings_inside_ordinary_wrappers(self):
        result = process_document_content(
            self.prefix + "<div><h1>Appendix</h1><p><br></p>"
            "<div><h2>Endnotes</h2></div><h1>Footnotes</h1></div>"
        )
        self.assertEqual([s["name"] for s in result.sections], ["Opportunity"])

    def test_removes_empty_h1_before_hierarchy_validation_of_h2_document(self):
        result = process_document_content(
            "<h2>Opportunity</h2><p>One.</p><h2>Apply</h2><p>Two.</p>"
            "<h1>Appendix</h1><h2>Endnotes</h2>"
        )
        self.assertEqual([s["name"] for s in result.sections], ["Opportunity", "Apply"])
        with self.assertRaises(AmbiguousHeadingHierarchyError):
            process_document_content(
                "<h2>Opportunity</h2><p>One.</p><h1>Endnotes</h1><p>Source.</p>"
            )

    def test_content_and_unrecognized_headings_stop_tail_removal(self):
        # Test the early pass directly: subsequent existing generic cleanup may
        # independently remove empty elements, but must not make these deletable.
        for content in (
            "<p>Keep this text.</p>",
            '<img src="synthetic.png" alt="">',
            "<table><tr><td></td></tr></table>",
            "<ol><li></li></ol>",
            "<ul></ul>",
            "<h3>Child heading</h3>",
            "<h2>Other heading</h2>",
            '<div role="heading" aria-level="7">Child</div>',
            "<hr>",
            "<section></section>",
            '<div role="note"></div>',
            "<p>page-break</p>",
        ):
            with self.subTest(content=content):
                soup = BeautifulSoup(
                    self.prefix + "<h1>Appendix</h1>" + content, "html.parser"
                )
                before = str(soup)
                remove_empty_trailing_optional_headings(soup)
                self.assertEqual(str(soup), before)

    def test_only_exact_names_and_h1_h2_are_removed(self):
        for title in (
            "Appendix A",
            "Appendices",
            "Endnote",
            "Footnote",
            "End notes",
            "Foot notes",
            "Appendix::",
        ):
            for level in ("h1", "h2", "h3"):
                with self.subTest(title=title, level=level):
                    soup = BeautifulSoup(
                        self.prefix + f"<{level}>{title}</{level}>", "html.parser"
                    )
                    before = str(soup)
                    remove_empty_trailing_optional_headings(soup)
                    self.assertEqual(str(soup), before)
        soup = BeautifulSoup(self.prefix + "<h3>Endnotes</h3>", "html.parser")
        before = str(soup)
        remove_empty_trailing_optional_headings(soup)
        self.assertEqual(str(soup), before)

    def test_preserves_empty_heading_in_middle_and_populated_endnotes(self):
        result = process_document_content(
            self.prefix + "<h1>Appendix</h1><h1>Endnotes</h1><p>[1] Source.</p>"
        )
        self.assertEqual(
            [s["name"] for s in result.sections],
            ["Opportunity", "Appendix", "Endnotes"],
        )
        self.assertIn("Source.", str(result.sections))

    def test_native_note_list_preserves_heading_and_citation(self):
        for name in ("Endnotes", "Footnotes"):
            with self.subTest(name=name):
                result = process_document_content(
                    self.prefix
                    + '<p><a id="footnote-ref-1" href="#footnote-1">[1]</a></p>'
                    f"<h1>{name}</h1>"
                    '<ol><li id="footnote-1">Native citation<a href="#footnote-ref-1">↑</a></li></ol>'
                )
                self.assertEqual(
                    [s["name"] for s in result.sections], ["Opportunity", "Endnotes"]
                )
                self.assertIsNotNone(result.soup.find("li", id="footnote-1"))
                self.assertIn("Native citation", str(result.sections))

    def test_referenced_heading_bookmark_or_wrapper_is_preserved(self):
        for tail in (
            '<h1 id="keep">Appendix</h1>',
            '<h1>Appendix<a id="keep"></a></h1>',
            '<h1>Appendix</h1><p><a name="keep"></a></p>',
            '<div id="keep"><h1>Appendix</h1></div>',
        ):
            with self.subTest(tail=tail):
                soup = BeautifulSoup(
                    self.prefix + '<p><a href="#keep">See appendix</a></p>' + tail,
                    "html.parser",
                )
                before = str(soup)
                remove_empty_trailing_optional_headings(soup)
                self.assertEqual(str(soup), before)
        result = process_document_content(
            self.prefix
            + '<p><a href="#keep">See appendix</a></p><h1 id="keep">Appendix</h1>'
        )
        self.assertEqual(result.sections[-1]["name"], "Appendix")

    def test_idempotence_and_only_placeholders_still_fails_no_sections(self):
        soup = BeautifulSoup(
            self.prefix + "<h1>Appendix</h1><h1>Endnotes</h1>", "html.parser"
        )
        remove_empty_trailing_optional_headings(soup)
        once = str(soup)
        remove_empty_trailing_optional_headings(soup)
        self.assertEqual(str(soup), once)
        with self.assertRaises(ContentProcessingError) as caught:
            process_document_content("<h1>Appendix</h1><h2>Endnotes</h2>")
        self.assertEqual(caught.exception.code, "no_sections")


def placeholder_docx():
    """Minimal synthetic Word package using real Heading 1/Heading 2 styles."""
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            "</Types>",
        )
        archive.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        )
        archive.writestr(
            "word/_rels/document.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            "</Relationships>",
        )
        archive.writestr(
            "word/styles.xml",
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>'
            '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/></w:style>'
            "</w:styles>",
        )
        paragraphs = []
        for style, text in (
            (None, "Opdiv: CDC"),
            (None, "Opportunity number: SYNTHETIC-EMPTY-TAIL"),
            ("Heading1", "Opportunity"),
            ("Heading2", "Summary"),
            (None, "Applicant content."),
            ("Heading1", "Appendix"),
            ("Heading1", "Endnotes"),
        ):
            properties = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
            paragraphs.append(f"<w:p>{properties}<w:r><w:t>{text}</w:t></w:r></w:p>")
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
            + "".join(paragraphs)
            + "</w:body></w:document>",
        )
    return output.getvalue()


@override_settings(DEBUG=False)
class EmptyTrailingHeadingImportTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            email="empty-tail@example.com",
            password="local-test",
            group="bloom",
            force_password_reset=False,
            is_composer_admin=True,
        )
        self.client.force_login(user)

    def test_word_upload_removes_placeholders_in_all_three_consumers(self):
        for route, model in (
            ("nofos:nofo_import", Nofo),
            ("composer:composer_import", ContentGuide),
            ("compare:compare_import", CompareDocument),
        ):
            with self.subTest(route=route):
                response = self.client.post(
                    reverse(route),
                    {
                        "nofo-import": SimpleUploadedFile(
                            "empty-tail.docx",
                            placeholder_docx(),
                            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        )
                    },
                )
                self.assertEqual(response.status_code, 302)
                document = model.objects.get()
                self.assertEqual(
                    list(document.sections.values_list("name", flat=True)),
                    ["Opportunity"],
                )
                self.assertIn(
                    "Applicant content.", document.sections.get().subsections.get().body
                )

    def test_html_reimport_removes_previously_saved_empty_sections(self):
        html = "<p>Opdiv: CDC</p><p>Opportunity number: SYNTHETIC-EMPTY-TAIL</p><h1>Opportunity</h1><h2>Summary</h2><p>Updated content.</p><h1>Appendix</h1><h1>Endnotes</h1>"
        document = Nofo.objects.create(
            title="Synthetic tail cleanup",
            short_name="Synthetic tail cleanup",
            number="SYNTHETIC-EMPTY-TAIL",
            opdiv="CDC",
            group="bloom",
            status="draft",
        )
        document.sections.create(name="Appendix", order=1)
        document.sections.create(name="Endnotes", order=2)
        response = self.client.post(
            reverse("nofos:nofo_import_overwrite", args=[document.pk]),
            {
                "nofo-import": SimpleUploadedFile(
                    "empty-tail.html", html.encode(), content_type="text/html"
                )
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            list(document.sections.values_list("name", flat=True)), ["Opportunity"]
        )
        self.assertIn(
            "Updated content.", document.sections.get().subsections.get().body
        )
