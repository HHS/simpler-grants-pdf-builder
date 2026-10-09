"""Direct content callers need no request, upload, user or document record."""

from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, override_settings

from nofos.document_processing import process_document_content
from nofos.nofo import (
    decompose_before_you_begin_section,
    get_sections_from_soup,
    get_subsections_from_sections,
    process_nofo_html,
    replace_chars,
    replace_links,
    resolve_section_heading_level,
)


@override_settings(DEBUG=False)
class DocumentProcessingTests(SimpleTestCase):
    def test_direct_content_preserves_metadata_and_excludes_redundant_section(self):
        result = process_document_content(
            "<h1>Before you begin</h1><p>Redundant text.</p>"
            "<p>Opdiv: CDC</p><h1>Opportunity</h1>"
            "<h2>Summary</h2><p>Public&nbsp;agencies may apply.</p>"
        )
        self.assertIn("Opdiv: CDC", str(result.soup))
        self.assertNotIn("Redundant text.", str(result.soup))
        self.assertEqual([s["name"] for s in result.sections], ["Opportunity"])
        self.assertNotIn("Opdiv: CDC", str(result.sections))
        self.assertIn("Public agencies may apply.", str(result.sections))

    def test_existing_processing_sequence_has_identical_results(self):
        # Pre-extraction sequence provides a concrete before/after oracle.
        shapes = (
            "<div><h1>Opportunity</h1><h2>Eligibility</h2><p>Public agencies.</p></div>",
            "<h1>Opportunity</h1><h2>Awards</h2><table><caption>Funding</caption><tr><td>Program</td><td>Amount</td></tr><tr><td>Training</td><td>0</td></tr></table>",
            '<h1>Opportunity</h1><h2>Summary</h2><img src="logo.png" alt="Agency logo"><p><a href="#note-1">Read note</a></p><ol><li id="note-1">Source</li></ol>',
            "<p>Opdiv: CDC</p><h1>Opportunity</h1><h2>Summary</h2>"
            "<table><tr><td><p>Instructions for NOFO writers</p><p>Keep this instruction.</p></td></tr></table><p>Applicant text.</p>",
        )
        for html in shapes:
            with self.subTest(html=html):
                before = BeautifulSoup(
                    replace_links(replace_chars(html)), "html.parser"
                )
                decompose_before_you_begin_section(before)
                level = resolve_section_heading_level(before)
                before, instructions = process_nofo_html(before, level)
                sections = get_subsections_from_sections(
                    get_sections_from_soup(before, level), level
                )
                after = process_document_content(html)
                self.assertEqual(str(after.soup), str(before))
                self.assertEqual(str(after.sections), str(sections))
                self.assertEqual(str(after.instructions_tables), str(instructions))

    def test_section_parser_extension_keeps_mutable_identity(self):
        sections = [{"name": "Consumer result", "subsections": []}]
        calls = []

        def section_parser(soup, level):
            calls.append((soup, level))
            return sections

        result = process_document_content(
            "<h1>Opportunity</h1>", section_parser=section_parser
        )
        self.assertIs(result.sections, sections)
        self.assertIs(calls[0][0], result.soup)
        self.assertEqual(calls[0][1], "h1")

    def test_no_sections_failure_propagates_without_web_presentation(self):
        with self.assertRaises(ValidationError) as error:
            process_document_content("<p>Only body text.</p>")
        self.assertEqual(error.exception.code, "no_sections")
