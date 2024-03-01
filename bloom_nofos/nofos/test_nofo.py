from unittest.mock import MagicMock, patch

import requests
from bs4 import BeautifulSoup
from django.test import TestCase
from freezegun import freeze_time

from .models import Nofo, Section, Subsection
from .nofo import DEFAULT_NOFO_OPPORTUNITY_NUMBER
from .nofo import (
    _get_classnames_for_font_weight_bold as get_classnames_for_font_weight_bold,
)
from .nofo import _get_font_size_from_cssText as get_font_size_from_cssText
from .nofo import _update_link_statuses as update_link_statuses
from .nofo import (
    add_endnotes_header_if_exists,
    add_headings_to_nofo,
    add_strongs_to_soup,
    clean_table_cells,
    combine_consecutive_links,
    convert_table_first_row_to_header_row,
    create_nofo,
    decompose_empty_tags,
    escape_asterisks_in_table_cells,
    find_broken_links,
    find_external_links,
    get_logo,
    get_sections_from_soup,
    get_subsections_from_sections,
    join_nested_lists,
    overwrite_nofo,
    remove_google_tracking_info_from_links,
    replace_src_for_inline_images,
    suggest_nofo_agency,
    suggest_nofo_author,
    suggest_nofo_keywords,
    suggest_nofo_opdiv,
    suggest_nofo_opportunity_number,
    suggest_nofo_subagency,
    suggest_nofo_subagency2,
    suggest_nofo_subject,
    suggest_nofo_tagline,
    suggest_nofo_theme,
    suggest_nofo_title,
)
from .utils import clean_string, match_view_url


class MatchUrlTests(TestCase):
    def test_match_valid_urls(self):
        """
        Test the match_url function with valid URLs.
        """
        self.assertTrue(match_view_url("/nofos/123"))
        self.assertTrue(match_view_url("/nofos/1"))
        self.assertTrue(match_view_url("/nofos/0"))

    def test_match_invalid_urls(self):
        """
        Test the match_url function with invalid URLs.
        """
        self.assertFalse(match_view_url("/nofos"))
        self.assertFalse(match_view_url("/nofos/"))
        self.assertFalse(match_view_url("/nofos/abc"))
        self.assertFalse(match_view_url("/nofos/123/456"))
        self.assertFalse(match_view_url("/nofos/1/2"))


class TestsCleanTableCells(TestCase):
    def test_remove_span_keep_content(self):
        html = "<table><tr><td><span>Content</span> and more <span>content</span></td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        clean_table_cells(soup)
        self.assertEqual(str(soup.td), "<td>Content and more content</td>")

    def test_replace_non_breaking_space(self):
        html = "<table><tr><td>Content\xa0here</td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        clean_table_cells(soup)
        self.assertIn("Content here", soup.td.text)

    def test_table_with_one_cell(self):
        html = "<table><tr><td>Only one cell</td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        clean_table_cells(soup)
        self.assertIn("Only one cell", soup.td.text)

    def test_table_with_span_and_nbsp(self):
        html = "<table><tr><td><span>Some</span>\xa0content and<span> more content</span></td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        clean_table_cells(soup)
        self.assertEqual(soup.td.text, "Some content and more content")

    def test_table_with_span_and_nbsp_and_link(self):
        html = "<table><tr><td><span>Some</span>\xa0content and<span> <a href='https://groundhog-day.com'>a link</a></span></td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        clean_table_cells(soup)
        self.assertEqual(
            str(soup.td),
            '<td>Some content and <a href="https://groundhog-day.com">a link</a></td>',
        )

    def test_table_with_span_and_nbsp_and_a_list(self):
        html = "<table><tr><td><span>Some</span>\xa0content and<span> <ul><li>a list item 1</li><li>a list item 2</li></ul></span></td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        clean_table_cells(soup)
        self.assertEqual(
            str(soup.td),
            "<td>Some content and <ul><li>a list item 1</li><li>a list item 2</li></ul></td>",
        )

    def test_multiple_spans_in_cell(self):
        html = "<table><tr><td><span>First</span><span>Second</span></td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        clean_table_cells(soup)
        self.assertEqual(soup.td.text, "FirstSecond")


class CleanStringTests(TestCase):
    def test_trim_leading_and_trailing_spaces(self):
        self.assertEqual(clean_string("  test string  "), "test string")

    def test_replace_newlines(self):
        self.assertEqual(clean_string("test\nstring"), "test string")

    def test_replace_carriage_returns(self):
        self.assertEqual(clean_string("test\rstring"), "test string")

    def test_replace_tabs(self):
        self.assertEqual(clean_string("test\tstring"), "test string")

    def test_replace_multiple_spaces(self):
        self.assertEqual(clean_string("test  string"), "test string")

    def test_replace_mixed_whitespace(self):
        self.assertEqual(clean_string("test \t\n\r string"), "test string")

    def test_replace_leading_weird_space(self):
        self.assertEqual(clean_string(" test \t\n\r string"), "test string")

    def test_replace_trailing_weird_space(self):
        self.assertEqual(clean_string("test \t\n\r string "), "test string")

    def test_no_whitespace_change(self):
        self.assertEqual(clean_string("test string"), "test string")

    def test_empty_string(self):
        self.assertEqual(clean_string(""), "")

    def test_only_whitespace(self):
        self.assertEqual(clean_string(" \t\r\n "), "")


class TableConvertFirstRowToHeaderRowTests(TestCase):
    def setUp(self):
        self.caption_text = "Physician Assistant Training Chart"
        self.html_filename = "nofos/fixtures/html/table.html"
        self.soup = BeautifulSoup(open(self.html_filename), "html.parser")

    def test_table_before_convert_table_first_row_to_header_row(self):
        table = self.soup.find("table")

        # Confirm no header cells
        header_cells = table.find_all("th")
        self.assertEqual(len(header_cells), 0)

        # Count the rows
        rows = table.find_all("tr")
        self.assertEqual(len(rows), 6)

        # Count the columns
        first_row = rows[0]
        columns = first_row.find_all("td")
        self.assertEqual(len(columns), 4)

        # Find the first cell and check its content
        first_cell = first_row.find("td")
        self.assertIn("Year", first_cell.text.strip())

    def test_table_after_convert_table_first_row_to_header_row(self):
        table = self.soup.find("table")
        # Convert first row of tds to ths
        convert_table_first_row_to_header_row(table)

        # Confirm no header cells
        header_cells = table.find_all("th")
        self.assertEqual(len(header_cells), 4)

        # Count the rows
        rows = table.find_all("tr")
        self.assertEqual(len(rows), 6)

        # Count the columns
        first_row = rows[0]
        columns = first_row.find_all("th")
        self.assertEqual(len(columns), 4)

        # Find the first cell and check its content
        first_cell = first_row.find("th")
        self.assertIn("Year", first_cell.text.strip())


class HTMLSectionTests(TestCase):
    def test_get_sections_from_soup(self):
        soup = BeautifulSoup("<h1>Section 1</h1><p>Section 1 body</p>", "html.parser")
        sections = get_sections_from_soup(soup)
        self.assertEqual(len(sections), 1)

        section = sections[0]
        self.assertEqual(section.get("name"), "Section 1")
        self.assertEqual(section.get("html_id"), "")
        self.assertEqual(section.get("order"), 1)
        self.assertEqual(str(section.get("body")[0]), "<p>Section 1 body</p>")
        self.assertEqual(section.get("has_section_page"), True)

    def test_get_sections_from_soup_length_zero(self):
        soup = BeautifulSoup("<p>Section 1 body</p>", "html.parser")
        sections = get_sections_from_soup(soup)
        self.assertEqual(sections, [])

    def test_get_sections_from_soup_length_two(self):
        soup = BeautifulSoup("<h1>Section 1</h1><h1>Section 2</h1>", "html.parser")
        sections = get_sections_from_soup(soup)
        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0].get("order"), 1)
        self.assertEqual(sections[1].get("order"), 2)

    def test_get_sections_from_soup_with_html_id(self):
        soup = BeautifulSoup(
            '<h1 id="section-1">Section 1</h1><p>Section 1 body</p>', "html.parser"
        )
        sections = get_sections_from_soup(soup)
        self.assertEqual(sections[0].get("html_id"), "section-1")

    def test_get_sections_from_soup_no_body(self):
        soup = BeautifulSoup("<h1>Section 1</h1>", "html.parser")
        sections = get_sections_from_soup(soup)
        self.assertEqual(sections[0].get("body"), [])

    def test_get_sections_from_soup_with_whitespace(self):
        soup = BeautifulSoup(
            '<h1 id="section-1"><span class="c21">Section 1 </span></h1><p>Section 1 body</p>',
            "html.parser",
        )
        sections = get_sections_from_soup(soup)
        self.assertEqual(sections[0].get("name"), "Section 1")

    def test_get_sections_from_soup_with_nonbreaking_space(self):
        # contains nonbreaking space before the "1" character
        soup = BeautifulSoup(
            '<h1 id="section-1"><span class="c21">Step[a][b][c][d] 1: Review the Opportunity</span></h1><p>Section 1 body</p>',
            "html.parser",
        )
        sections = get_sections_from_soup(soup)
        self.assertEqual(
            sections[0].get("name"), "Step[a][b][c][d] 1: Review the Opportunity"
        )

    def test_get_sections_from_soup_with_multiple_spaces(self):
        # contains nonbreaking space before the "1" character
        soup = BeautifulSoup(
            '<h1 id="section-1"><span class="c21">Step    \n1: Review the Opportunity</span></h1><p>Section 1 body</p>',
            "html.parser",
        )
        sections = get_sections_from_soup(soup)
        self.assertEqual(sections[0].get("name"), "Step 1: Review the Opportunity")

    def test_get_sections_from_soup_with_no_section_page(self):
        for no_section_page_title in [
            "Appendix",
            "Appendices",
            "Glossary",
            "Endnotes",
            "References",
        ]:
            soup = BeautifulSoup(
                '<h1 id="section-1">{}</span></h1><p>Section 1 body</p>'.format(
                    no_section_page_title
                ),
                "html.parser",
            )
            sections = get_sections_from_soup(soup)
            self.assertEqual(sections[0].get("name"), no_section_page_title)
            self.assertEqual(sections[0].get("has_section_page"), False)


class HTMLSubsectionTests(TestCase):
    def test_get_subsections_from_soup(self):
        soup = BeautifulSoup(
            "<h1>Section 1</h1><h2>Subsection 1</h2><p>Section 1 body</p>",
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        # 1 section
        self.assertEqual(len(sections), 1)

        # assert section values
        section = sections[0]
        self.assertEqual(section.get("name"), "Section 1")
        self.assertEqual(section.get("html_id"), "")
        self.assertEqual(section.get("order"), 1)

        # 1 subsection
        self.assertEqual(len(section.get("subsections")), 1)
        subsection = section.get("subsections")[0]

        # assert subsection values
        self.assertEqual(subsection.get("name"), "Subsection 1")
        self.assertEqual(subsection.get("html_id"), "")
        self.assertEqual(subsection.get("order"), 1)
        self.assertEqual(str(subsection.get("body")[0]), "<p>Section 1 body</p>")

    def test_get_subsections_from_soup_section_body_disappears(self):
        soup = BeautifulSoup(
            "<h1>Section 1</h1><h2>Subsection 1</h2><p>Section 1 body</p>",
            "html.parser",
        )
        sections = get_sections_from_soup(soup)
        self.assertEqual(
            [str(tag) for tag in sections[0].get("body")],
            ["<h2>Subsection 1</h2>", "<p>Section 1 body</p>"],
        )

        # body is gone after get_sections_from_soup
        sections = get_subsections_from_sections(sections)
        self.assertIsNone(sections[0].get("body", None))

    def test_get_subsections_from_soup_section_html_id(self):
        soup = BeautifulSoup(
            '<h1>Section 1</h1><h2 id="subsection-1">Subsection 1</h2><p>Section 1 body</p>',
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        subsection = sections[0].get("subsections")[0]
        self.assertEqual(subsection.get("html_id"), "subsection-1")

    def test_get_subsections_from_soup_section_heading_demoted(self):
        soup = BeautifulSoup(
            '<h1>Section 1</h1><h2 id="subsection-1">Subsection 1</h2><p>Section 1 body</p>',
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        subsection = sections[0].get("subsections")[0]
        self.assertEqual(subsection.get("tag"), "h3")

    def test_get_subsections_from_soup_nested_heading_not_a_section(self):
        soup = BeautifulSoup(
            '<h1>Section 1</h1><h2 id="subsection-1">Subsection 1</h2><p>Section 1 body</p><div><h2>Not a subsection</h2>',
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        subsections = sections[0].get("subsections")
        self.assertEqual(len(subsections), 1)

    def test_get_subsections_from_soup_no_body(self):
        soup = BeautifulSoup(
            '<h1>Section 1</h1><h2 id="subsection-1">Subsection 1</h2>',
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        subsection = sections[0].get("subsections")[0]
        self.assertEqual(subsection.get("body"), [])

    def test_get_subsections_from_soup_lost_paragraph_before_heading(self):
        soup = BeautifulSoup(
            "<h1>Section 1</h1><p>This paragraph disappears</p><h2>Subsection 1</h2><p>Section 1 body</p>",
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        subsection = sections[0].get("subsections")[0]
        self.assertEqual(str(subsection.get("body")[0]), "<p>Section 1 body</p>")

    def test_get_subsections_from_soup_two_subsections(self):
        soup = BeautifulSoup(
            '<h1>Section 1</h1><h2>Subsection 1</h2><p>Section 1 body</p><h3 id="subsection-2">Subsection 2</h3><p>Section 1 body continued</p>',
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        subsections = sections[0].get("subsections")
        self.assertEqual(len(subsections), 2)

        subsection_one = subsections[0]
        self.assertEqual(subsection_one.get("name"), "Subsection 1")
        self.assertEqual(subsection_one.get("html_id"), "")
        self.assertEqual(subsection_one.get("order"), 1)
        self.assertEqual(str(subsection_one.get("body")[0]), "<p>Section 1 body</p>")

        subsection_two = subsections[1]
        self.assertEqual(subsection_two.get("name"), "Subsection 2")
        self.assertEqual(subsection_two.get("html_id"), "subsection-2")
        self.assertEqual(subsection_two.get("tag"), "h4")
        self.assertEqual(subsection_two.get("order"), 2)
        self.assertEqual(
            str(subsection_two.get("body")[0]), "<p>Section 1 body continued</p>"
        )

    def test_get_subsections_from_soup_section_heading_h6(self):
        soup = BeautifulSoup(
            '<h1>Section 1</h1><h6 id="subsection-1">Subsection 1</h6><p>Section 1 body</p>',
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        subsection = sections[0].get("subsections")[0]
        self.assertEqual(subsection.get("tag"), "h7")

    def test_get_subsections_from_soup_with_whitespace(self):
        soup = BeautifulSoup(
            "<h1><span>Section 1 </span></h1><h2><span>Subsection 1 </span> </h2><p>Section 1 body</p>",
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        # 1 section
        self.assertEqual(len(sections), 1)

        # assert section values
        section = sections[0]
        self.assertEqual(section.get("name"), "Section 1")

        # 1 subsection
        self.assertEqual(len(section.get("subsections")), 1)
        subsection = section.get("subsections")[0]
        self.assertEqual(subsection.get("name"), "Subsection 1")

    def test_get_subsections_from_soup_with_nonbreaking_space(self):
        # nonbreaking space before "1" in the h1 and the h2
        soup = BeautifulSoup(
            "<h1><span>Section 1</span></h1><h2><span>Subsection 1</span> </h2><p>Section 1 body</p>",
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        # 1 section
        self.assertEqual(len(sections), 1)

        # assert section values
        section = sections[0]
        self.assertEqual(section.get("name"), "Section 1")

        # 1 subsection
        self.assertEqual(len(section.get("subsections")), 1)
        subsection = section.get("subsections")[0]
        self.assertEqual(subsection.get("name"), "Subsection 1")

    def test_get_subsections_from_soup_with_carriage_returns(self):
        # nonbreaking space before "1" in the h1 and the h2
        soup = BeautifulSoup(
            "<h1><span>Section\r\n1</span></h1><h2><span>Subsection\t1</span> </h2><p>Section 1 body</p>",
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        # 1 section
        self.assertEqual(len(sections), 1)

        # assert section values
        section = sections[0]
        self.assertEqual(section.get("name"), "Section 1")

        # 1 subsection
        self.assertEqual(len(section.get("subsections")), 1)
        subsection = section.get("subsections")[0]
        self.assertEqual(subsection.get("name"), "Subsection 1")


class HTMLNofoFileTests(TestCase):
    def setUp(self):
        self.html_filename = "nofos/fixtures/html/nofo.html"
        self.soup = BeautifulSoup(open(self.html_filename), "html.parser")

    def test_get_sections_from_soup_html_file(self):
        sections = get_sections_from_soup(self.soup)
        self.assertEqual(len(sections), 7)

        section = sections[0]
        self.assertEqual(section.get("name"), "Step 1: Review the Opportunity")
        self.assertEqual(section.get("html_id"), "")
        self.assertEqual(section.get("order"), 1)
        self.assertIsNotNone(section.get("body", None))

    def test_get_subsections_from_soup_html_file(self):
        sections = get_subsections_from_sections(get_sections_from_soup(self.soup))
        self.assertEqual(len(sections), 7)

        section_info = [
            {
                "name": "Step 1: Review the Opportunity",
                "subsections_len": 24,
                "subsections_first_title": "Basic Information",
            },
            {
                "name": "Step 2: Get Ready to Apply",
                "subsections_len": 6,
                "subsections_first_title": "Get Registered",
            },
            {
                "name": "Step 3: Write Your Application",
                "subsections_len": 32,
                "subsections_first_title": "Application Contents & Format",
            },
            {
                "name": "Step 4: Learn About Review & Award",
                "subsections_len": 13,
                "subsections_first_title": "Application Review",
            },
            {
                "name": "Step 5: Submit Your Application",
                "subsections_len": 8,
                "subsections_first_title": "Application Submission & Deadlines",
            },
            {
                "name": "Learn What Happens After Award",
                "subsections_len": 4,
                "subsections_first_title": "Post-Award Requirements & Administration",
            },
            {
                "name": "Contacts & Support",
                "subsections_len": 8,
                "subsections_first_title": "Agency Contacts",
            },
        ]

        for index, section in enumerate(sections):
            self.assertEqual(section.get("name"), section_info[index].get("name"))
            self.assertEqual(
                len(section.get("subsections")),
                section_info[index].get("subsections_len"),
            )
            self.assertEqual(
                section.get("subsections")[0].get("name"),
                section_info[index].get("subsections_first_title"),
            )


def _get_sections_dict():
    return [
        {
            "name": "Section 1",
            "order": 1,
            "html_id": "",
            "has_section_page": True,
            "subsections": [
                {
                    "name": "Subsection 1",
                    "order": 1,
                    "tag": "h3",
                    "html_id": "",
                    "body": ["<p>Section 1 body</p>"],
                },
                {
                    "name": "Subsection 2",
                    "order": 2,
                    "tag": "h4",
                    "html_id": "subsection-2",
                    "body": ["<p>Section 1 body continued</p>"],
                },
            ],
        }
    ]


class CreateNOFOTests(TestCase):
    def setUp(self):
        self.sections = _get_sections_dict()

    def test_create_nofo_success(self):
        """
        Test creating a nofo object successfully
        """
        nofo = create_nofo("Test Nofo", self.sections)
        self.assertEqual(nofo.title, "Test Nofo")
        self.assertEqual(nofo.number, "NOFO #999")
        self.assertEqual(nofo.theme, "portrait-hrsa-blue")
        self.assertEqual(len(nofo.sections.all()), 1)
        self.assertEqual(len(nofo.sections.first().subsections.all()), 2)

    def test_create_nofo_success_duplicate_nofos(self):
        """
        Test creating two duplicate nofo objects successfully
        """
        nofo = create_nofo("Test Nofo", self.sections)
        nofo2 = create_nofo("Test Nofo", self.sections)
        self.assertEqual(nofo.title, nofo2.title)
        self.assertEqual(nofo.number, nofo2.number)
        self.assertEqual(len(nofo.sections.all()), len(nofo2.sections.all()))
        self.assertEqual(
            len(nofo.sections.first().subsections.all()),
            len(nofo2.sections.first().subsections.all()),
        )

    def test_create_nofo_success_no_sections(self):
        """
        Test with empty nofo sections
        """
        nofo = create_nofo("Test Nofo", [])
        self.assertEqual(nofo.title, "Test Nofo")
        self.assertEqual(len(nofo.sections.all()), 0)

    def test_create_nofo_success_no_title(self):
        """
        Test with empty nofo title and empty sections
        """
        nofo = create_nofo("", [])
        self.assertEqual(nofo.title, "")
        self.assertEqual(len(nofo.sections.all()), 0)


class OverwriteNOFOTests(TestCase):
    def setUp(self):
        self.sections = _get_sections_dict()

        self.new_sections = [
            {
                "name": "New Section 100",
                "order": 1,
                "html_id": "",
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "New Subsection 100",
                        "order": 1,
                        "tag": "h3",
                        "html_id": "",
                        "body": ["<p>New Section 100 body</p>"],
                    }
                ],
            }
        ]

    def test_overwrite_nofo_success(self):
        """
        Test overwriting a nofo object successfully
        """
        nofo = create_nofo("Test Nofo", self.sections)
        self.assertEqual(nofo.title, "Test Nofo")
        self.assertEqual(nofo.number, "NOFO #999")
        self.assertEqual(nofo.sections.first().name, "Section 1")
        self.assertEqual(len(nofo.sections.first().subsections.all()), 2)
        self.assertEqual(nofo.sections.first().subsections.first().name, "Subsection 1")

        nofo = overwrite_nofo(nofo, self.new_sections)
        self.assertEqual(nofo.title, "Test Nofo")  # same name
        self.assertEqual(nofo.number, "NOFO #999")  # same number
        self.assertEqual(nofo.sections.first().name, "New Section 100")
        self.assertEqual(
            len(nofo.sections.first().subsections.all()), 1
        )  # only 1 subsection
        self.assertEqual(
            nofo.sections.first().subsections.first().name, "New Subsection 100"
        )

    def test_overwrite_nofo_success_empty_sections(self):
        """
        Test overwriting a nofo with empty sections also succeeds
        """
        nofo = create_nofo("Test Nofo", self.sections)
        self.assertEqual(nofo.title, "Test Nofo")
        self.assertEqual(nofo.number, "NOFO #999")
        self.assertEqual(nofo.sections.first().name, "Section 1")
        self.assertEqual(len(nofo.sections.first().subsections.all()), 2)
        self.assertEqual(nofo.sections.first().subsections.first().name, "Subsection 1")

        nofo = overwrite_nofo(nofo, [])
        self.assertEqual(nofo.title, "Test Nofo")  # same name
        self.assertEqual(nofo.number, "NOFO #999")  # same number
        self.assertEqual(len(nofo.sections.all()), 0)  # empty sections


class AddHeadingsTests(TestCase):
    def setUp(self):
        self.sections = _get_sections_dict()
        self.sections_with_link = [
            {
                "name": "Section 1",
                "order": 1,
                "html_id": "",
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "Subsection 1",
                        "order": 1,
                        "tag": "h3",
                        "html_id": "custom-link",
                        "body": [
                            '<p>Section 1 body with <a href="#custom-link">custom link</a>.</p>'
                        ],
                    },
                    {
                        "name": "Subsection 2",
                        "order": 2,
                        "tag": "h4",
                        "html_id": "h.haapch",
                        "body": [
                            '<p>Section 2 body with 2 <a href="#custom-link">custom</a> <a href="#h.haapch">links</a></a>.</p>'
                        ],
                    },
                ],
            }
        ]

        self.sections_with_really_long_subsection_title = [
            {
                "name": "Program description",
                "order": 1,
                "html_id": "",
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "This opportunity provides financial and technical aid to help communities monitor behavioral risk factors and chronic health conditions among adults in the United States and territories.",
                        "order": 1,
                        "tag": "h3",
                        "html_id": "custom-link",
                        "body": [
                            '<p>Section 1 body with <a href="#custom-link">custom link</a>.</p>'
                        ],
                    }
                ],
            }
        ]

    def test_add_headings_success(self):
        nofo = create_nofo("Test Nofo", self.sections)
        self.assertEqual(nofo.title, "Test Nofo")

        section = nofo.sections.first()
        subsection_1 = nofo.sections.first().subsections.all()[0]
        subsection_2 = nofo.sections.first().subsections.all()[1]

        # check section heading has no id
        self.assertEqual(section.html_id, "")
        # check first subsection heading has no html_id
        self.assertEqual(subsection_1.html_id, "1--section-1--subsection-1")
        # check second subsection heading has html_id
        self.assertEqual(subsection_2.html_id, "subsection-2")

        ################
        # ADD HEADINGS
        ################
        add_headings_to_nofo(nofo)
        section = nofo.sections.first()
        subsection_1 = nofo.sections.first().subsections.all()[0]
        subsection_2 = nofo.sections.first().subsections.all()[1]

        # check section heading has new html_id
        self.assertEqual(section.html_id, "section-1")
        # check subsection headings have new html_id
        self.assertEqual(subsection_1.html_id, "1--section-1--subsection-1")
        self.assertEqual(subsection_2.html_id, "2--section-1--subsection-2")

    def test_add_headings_success_replace_link(self):
        nofo = create_nofo("Test Nofo 2", self.sections_with_link)
        self.assertEqual(nofo.title, "Test Nofo 2")

        section = nofo.sections.first()
        subsection_1 = nofo.sections.first().subsections.all()[0]
        subsection_2 = nofo.sections.first().subsections.all()[1]

        # check section 1 heading has no id
        self.assertEqual(section.html_id, "")
        # check subsection 1 heading has html_id
        self.assertEqual(subsection_1.html_id, "custom-link")
        # check the body of subsection 1 includes link
        self.assertIn(
            "Section 1 body with [custom link](#custom-link)", subsection_1.body
        )
        # check subsection 2 heading has html_id
        self.assertEqual(subsection_2.html_id, "h.haapch")
        # check the body of subsection 2 includes links
        self.assertIn(
            "Section 2 body with 2 [custom](#custom-link) [links](#h.haapch).",
            subsection_2.body,
        )

        ################
        # ADD HEADINGS
        ################
        add_headings_to_nofo(nofo)
        section = nofo.sections.first()
        subsection_1 = nofo.sections.first().subsections.all()[0]
        subsection_2 = nofo.sections.first().subsections.all()[1]

        # check section heading has new html_id
        self.assertEqual(section.html_id, "section-1")
        # check subsection1 heading has new html_id
        self.assertEqual(subsection_1.html_id, "1--section-1--subsection-1")
        # check the body of subsection 1 link is updated to new id
        self.assertIn(
            "Section 1 body with [custom link](#1--section-1--subsection-1)",
            subsection_1.body,
        )
        # check subsection 2 heading has new html_id
        self.assertEqual(subsection_2.html_id, "2--section-1--subsection-2")
        # check the body of subsection link is updated to new id
        self.assertIn(
            "Section 2 body with 2 [custom](#1--section-1--subsection-1) [links](#2--section-1--subsection-2).",
            subsection_2.body,
        )

    def test_add_headings_with_really_long_title_replace_link(self):
        nofo = create_nofo(
            "Test Nofo 2", self.sections_with_really_long_subsection_title
        )
        self.assertEqual(nofo.title, "Test Nofo 2")

        section = nofo.sections.first()
        subsection_1 = nofo.sections.first().subsections.all()[0]

        # check section 1 heading has no id
        self.assertEqual(section.html_id, "")
        # check subsection 1 heading has html_id
        self.assertEqual(subsection_1.html_id, "custom-link")
        # check the body of subsection 1 includes link
        self.assertIn(
            "Section 1 body with [custom link](#custom-link)", subsection_1.body
        )

        ################
        # ADD HEADINGS
        ################
        add_headings_to_nofo(nofo)
        section = nofo.sections.first()
        subsection_1 = nofo.sections.first().subsections.all()[0]

        # check section heading has new html_id
        self.assertEqual(section.html_id, "program-description")
        # check subsection1 heading has new html_id
        self.assertEqual(
            subsection_1.html_id,
            "1--program-description--this-opportunity-provides-financial-and-technical-aid-to-help-communities-monitor-behavioral-risk-factors-and-chronic-health-conditions-among-adults-in-the-united-states-and-territories",
        )
        # check the body of subsection 1 link is updated to new id
        self.assertIn(
            "Section 1 body with [custom link](#1--program-description--this-opportunity-provides-financial-and-technical-aid-to-help-communities-monitor-behavioral-risk-factors-and-chronic-health-conditions-among-adults-in-the-united-states-and-territories)",
            subsection_1.body,
        )


class TestGetLogo(TestCase):
    def test_cdc_blue_logo_portrait(self):
        """Test for CDC with blue colour"""
        logo_path = get_logo("cdc", "blue")
        self.assertEqual(logo_path, "img/logos/cdc/white/cdc-logo.svg")

    def test_cdc_blue_logo_hero(self):
        """Test for CDC with blue colour with hero title"""
        logo_path = get_logo("cdc", "blue", cover="nofo--cover-page--hero")
        self.assertEqual(logo_path, "img/logos/cdc/blue/cdc-logo.svg")

    def test_cdc_blue_logo_landscape(self):
        """Test for CDC with blue colour landscape"""
        logo_path = get_logo("cdc", "blue", orientation="landscape")
        self.assertEqual(logo_path, "img/logos/cdc/blue/cdc-logo.svg")

    def test_cdc_blue_logo_hero_landscape(self):
        """Test for CDC with blue colour with hero title in landscape"""
        logo_path = get_logo(
            "cdc", "blue", cover="nofo--cover-page--hero", orientation="landscape"
        )
        self.assertEqual(logo_path, "img/logos/cdc/blue/cdc-logo.svg")

    def test_cdc_white_logo_portrait(self):
        """Test for CDC with white colour"""
        logo_path = get_logo("white", "blue")
        self.assertEqual(logo_path, "img/logos/cdc/blue/cdc-logo.svg")

    def test_cdc_white_logo_hero(self):
        """Test for CDC with white colour with hero title"""
        logo_path = get_logo("cdc", "white", cover="nofo--cover-page--hero")
        self.assertEqual(logo_path, "img/logos/cdc/blue/cdc-logo.svg")

    def test_cdc_white_logo_landscape(self):
        """Test for CDC with white colour landscape"""
        logo_path = get_logo("cdc", "white", orientation="landscape")
        self.assertEqual(logo_path, "img/logos/cdc/white/cdc-logo.svg")

    def test_cdc_white_logo_hero_landscape(self):
        """Test for CDC with white colour with hero title in landscape"""
        logo_path = get_logo(
            "cdc", "white", cover="nofo--cover-page--hero", orientation="landscape"
        )
        self.assertEqual(logo_path, "img/logos/cdc/white/cdc-logo.svg")

    def test_cdc_dop_logo_replacement(self):
        """Test for CDC with 'dop' colour, which should be replaced with 'white'"""
        logo_path = get_logo("cdc", "dop")
        self.assertEqual(logo_path, "img/logos/cdc/white/cdc-logo.svg")

    def test_cdc_any_colour_logo(self):
        """Test for CDC with any other colour"""
        logo_path = get_logo("cdc", "green")
        self.assertEqual(logo_path, "img/logos/cdc/white/cdc-logo.svg")

    def test_non_cdc_default_logo(self):
        """Test for non-CDC opdiv should return the default CDC blue logo"""
        logo_path = get_logo("other", "blue")
        # Assuming a fallback to default logo
        self.assertEqual(logo_path, "img/logos/cdc/blue/cdc-logo.svg")

    def test_cdc_no_colour_provided(self):
        """Test for CDC with no colour provided"""
        logo_path = get_logo("cdc")
        # Assuming a fallback to default logo
        self.assertEqual(logo_path, "img/logos/cdc/white/cdc-logo.svg")

    def test_hrsa_blue_logo(self):
        """Test for HRSA with blue colour"""
        logo_path = get_logo("hrsa", "blue")
        self.assertEqual(logo_path, "img/logos/hrsa/blue/hrsa-logo.svg")

    def test_hrsa_white_logo(self):
        """Test for HRSA with blue colour"""
        logo_path = get_logo("hrsa", "blue")
        self.assertEqual(logo_path, "img/logos/hrsa/blue/hrsa-logo.svg")

    def test_hrsa_with_text_cover(self):
        """Test for HRSA with text cover"""
        logo_path = get_logo("hrsa", "blue", "nofo--cover-page--text")
        self.assertEqual(logo_path, "img/logos/hrsa/white/hrsa-logo.svg")

    def test_hrsa_no_color_provided(self):
        """Test for HRSA with blue colour"""
        logo_path = get_logo("hrsa")
        self.assertEqual(logo_path, "img/logos/hrsa/blue/hrsa-logo.svg")

    def test_acf_white_logo(self):
        """Test for ACF with white colour"""
        logo_path = get_logo("acf", "blue")
        self.assertEqual(logo_path, "img/logos/acf/blue/acf-logo.svg")

    def test_acf_blue_with_text_cover(self):
        """Test for ACF blue with text cover"""
        logo_path = get_logo("acf", "blue", "nofo--cover-page--text")
        self.assertEqual(logo_path, "img/logos/acf/white/acf-logo.svg")

    def test_acf_white_with_text_cover(self):
        """Test for ACF blue with text cover"""
        logo_path = get_logo("acf", "white", "nofo--cover-page--text")
        self.assertEqual(logo_path, "img/logos/acf/blue/acf-logo.svg")

    def test_acf_no_color_provided(self):
        """Test for ACF with blue colour"""
        logo_path = get_logo("acf")
        self.assertEqual(logo_path, "img/logos/acf/blue/acf-logo.svg")

    def test_no_opdiv_no_colour(self):
        """Test for CDC with no opdiv or colour provided"""
        logo_path = get_logo()
        # Assuming a fallback to default logo
        self.assertEqual(logo_path, "img/logos/cdc/white/cdc-logo.svg")

    def test_empty_opdiv_raises_error(self):
        """Verify that an empty opdiv raises ValueError"""
        with self.assertRaises(ValueError):
            get_logo("", "blue")

    def test_empty_colour_raises_error(self):
        """Verify that an empty colour raises ValueError"""
        with self.assertRaises(ValueError):
            get_logo("cdc", "")

    def test_empty_cover_raises_error(self):
        """Test for CDC, blue colour, empty cover"""
        with self.assertRaises(ValueError):
            get_logo("cdc", "blue", "")

    def test_all_empty_raises_error(self):
        """Verify that both empty opdiv, colour, cover raise ValueError"""
        with self.assertRaises(ValueError):
            get_logo("", "", "")


class TestFindBrokenLinks(TestCase):
    def setUp(self):
        # Set up a Nofo instance and related Sections and Subsections
        nofo = Nofo.objects.create(title="Test Nofo")
        section = Section.objects.create(nofo=nofo, name="Test Section", order=1)

        Subsection.objects.create(
            section=section,
            name="Subsection with an #h Link",
            tag="h3",
            body="This is a test [broken link](#h.broken-link) in markdown.",
            order=1,
        )

        # Subsection without a broken link
        Subsection.objects.create(
            section=section,
            name="Subsection without Broken Link",
            tag="h3",
            body="This is a test with a [valid link](https://example.com).",
            order=2,
        )

        Subsection.objects.create(
            section=section,
            name="Subsection with an #id link",
            tag="h3",
            body="This is a second [broken link](#id.broken-link) in markdown.",
            order=3,
        )

        Subsection.objects.create(
            section=section,
            name='Subsection with a slash ("/") link',
            tag="h3",
            body="This is a [link that assumes a root domain](/contacts) in markdown.",
            order=4,
        )

        Subsection.objects.create(
            section=section,
            name="Subsection with a Google Docs link",
            tag="h3",
            body="This is a [Google Docs link](https://docs.google.com/document/d/some-document) in markdown.",
            order=5,
        )

    def test_find_broken_links_identifies_broken_links(self):
        nofo = Nofo.objects.get(title="Test Nofo")
        broken_links = find_broken_links(nofo)
        self.assertEqual(len(broken_links), 4)
        self.assertEqual(broken_links[0]["link_href"], "#h.broken-link")
        self.assertEqual(broken_links[1]["link_href"], "#id.broken-link")
        self.assertEqual(broken_links[2]["link_href"], "/contacts")
        self.assertEqual(
            broken_links[3]["link_href"],
            "https://docs.google.com/document/d/some-document",
        )

    def test_find_broken_links_ignores_valid_links(self):
        nofo = Nofo.objects.get(title="Test Nofo")
        broken_links = find_broken_links(nofo)
        valid_links = [
            link
            for link in broken_links
            if not (
                link["link_href"].startswith("#h.")
                or link["link_href"].startswith("#id.")
                or link["link_href"].startswith("/")
                or link["link_href"].startswith("https://docs.google.com")
            )
        ]
        self.assertEqual(len(valid_links), 0)


class TestUpdateLinkStatuses(TestCase):
    @patch("nofos.nofo.requests.head")
    def test_status_code_200(self, mock_head):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.history = []
        mock_head.return_value = mock_response

        all_links = [{"url": "https://example.com", "status": ""}]
        update_link_statuses(all_links)
        self.assertEqual(all_links[0]["status"], 200)

    @patch("nofos.nofo.requests.head")
    def test_status_code_404(self, mock_head):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.history = []
        mock_head.return_value = mock_response

        all_links = [{"url": "https://example.com", "status": ""}]
        update_link_statuses(all_links)
        self.assertEqual(all_links[0]["status"], 404)

    @patch("nofos.nofo.requests.head")
    def test_status_code_301_with_redirect(self, mock_head):
        mock_response = MagicMock()
        mock_response.status_code = 301
        mock_response.url = "https://redirected.com"
        mock_response.history = ["dummy_history"]
        mock_head.return_value = mock_response

        all_links = [{"url": "https://example.com", "status": ""}]
        update_link_statuses(all_links)
        self.assertEqual(all_links[0]["status"], 301)
        self.assertEqual(all_links[0]["redirect_url"], "https://redirected.com")

    @patch("nofos.nofo.requests.head")
    def test_request_exception(self, mock_head):
        mock_head.side_effect = requests.RequestException("Connection error")

        all_links = [{"url": "https://example.com", "status": ""}]
        update_link_statuses(all_links)
        self.assertIn("Error: Connection error", all_links[0]["error"])


class TestFindExternalLinks(TestCase):
    def setUp(self):
        self.sections = _get_sections_dict()

    def test_find_external_links_with_one_link_in_subsections(self):
        self_sections = self.sections
        # add external links to subsections
        self_sections[0]["subsections"][0]["body"] = [
            '<p>Section 1 body with link to <a href="https://groundhog-day.com">Groundhog Day</a></p>'
        ]

        nofo = create_nofo("Test Nofo", self_sections)
        links = find_external_links(nofo, with_status=False)

        # Assertions
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["url"], "https://groundhog-day.com")

    def test_find_external_links_with_two_links_in_subsections(self):
        self_sections = self.sections
        # add external links to subsections
        self_sections[0]["subsections"][0]["body"] = [
            '<p>Section 1 body with link to <a href="https://groundhog-day.com">Groundhog Day</a></p>'
        ]
        self_sections[0]["subsections"][1]["body"] = [
            '<p>Section 2 body with link to <a href="https://canada-holidays.ca">Canada Holidays</a></p>'
        ]

        nofo = create_nofo("Test Nofo", self_sections)
        links = find_external_links(nofo, with_status=False)

        self.assertEqual(len(links), 2)
        self.assertEqual(links[0]["url"], "https://groundhog-day.com")
        self.assertEqual(links[1]["url"], "https://canada-holidays.ca")

    def test_find_external_links_no_link_in_subsection(self):
        # no links in the original subsections
        nofo = create_nofo("Test Nofo", self.sections)
        links = find_external_links(nofo, with_status=False)

        self.assertEqual(len(links), 0)


#########################################################
#################### SUGGEST X TESTS ####################
#########################################################


class HTMLSuggestTitleTests(TestCase):
    def setUp(self):
        self.nofo_title = "Primary Care Training and Enhancement: Physician Assistant Rural Training in Mental and Behavioral Health (PCTE-PARM) Program"
        self.html_filename = "nofos/fixtures/html/nofo.html"
        self.soup = BeautifulSoup(open(self.html_filename), "html.parser")

    def test_suggest_nofo_title_returns_correct_title(self):
        self.assertEqual(suggest_nofo_title(self.soup), self.nofo_title)

    @freeze_time("1917-04-17")
    def test_suggest_nofo_title_returns_default_title_for_bad_html(self):
        default_name = "NOFO: 1917-04-17 00:00:00"
        self.assertEqual(
            suggest_nofo_title(
                BeautifulSoup(
                    "<html><title>THESES</title><body><h1>THESES</h1></body></html>",
                    "html.parser",
                )
            ),
            default_name,
        )

    def test_suggest_nofo_title_returns_default_title_for_p_span(self):
        name = "Primary Care Training and Enhancement: Physician Assistant Rural Training in Mental and Behavioral Health (PCTE-PARM) Program"
        self.assertEqual(
            suggest_nofo_title(
                BeautifulSoup(
                    '<html><title>THESES</title><body><h1>THESES</h1><p class="c0"><span>Opportunity Name: Primary Care Training and Enhancement: Physician Assistant Rural Training in Mental and Behavioral Health (PCTE-PARM) Program</span></p></body></html>',
                    "html.parser",
                )
            ),
            name,
        )

    def test_suggest_nofo_title_returns_default_title_for_p_span_span(self):
        name = "Improving Adolescent Health and Well-Being Through School-Based Surveillance and the What Works in Schools Program"
        self.assertEqual(
            suggest_nofo_title(
                BeautifulSoup(
                    '<html><title>THESES</title><body><h1>THESES</h1><p class="c0"><span class="c24">Opportunity Name: </span><span class="c1">Improving Adolescent Health and Well-Being Through School-Based Surveillance and the What Works in Schools Program</span></p></body></html>',
                    "html.parser",
                )
            ),
            name,
        )


class HTMLSuggestNumberTests(TestCase):
    def setUp(self):
        self.nofo_opportunity_number = "HRSA-24-019"
        self.html_filename = "nofos/fixtures/html/nofo.html"
        self.soup = BeautifulSoup(open(self.html_filename), "html.parser")

    def test_suggest_nofo_title_returns_correct_title(self):
        self.assertEqual(
            suggest_nofo_opportunity_number(self.soup), self.nofo_opportunity_number
        )

    def test_suggest_nofo_number_returns_default_number_for_bad_html(self):
        default_number = "NOFO #999"
        self.assertEqual(
            suggest_nofo_opportunity_number(
                BeautifulSoup(
                    "<html><title>THESES</title><body><h1>THESES</h1></body></html>",
                    "html.parser",
                )
            ),
            default_number,
        )

    def test_suggest_nofo_number_returns_default_title_for_p_span(self):
        name = "HRSA-24-019"
        self.assertEqual(
            suggest_nofo_opportunity_number(
                BeautifulSoup(
                    '<html><title>THESES</title><body><h1>THESES</h1><p class="c0"><span class="c3">Opportunity Number: HRSA-24-019</span></p></body></html>',
                    "html.parser",
                )
            ),
            name,
        )

    def test_suggest_nofo_number_returns_default_title_for_p_span_span(self):
        name = "CDC-RFA-DP-24-0139"
        self.assertEqual(
            suggest_nofo_opportunity_number(
                BeautifulSoup(
                    '<html><title>THESES</title><body><h1>THESES</h1><p class="c0"><span class="c180">Opportunity Number: </span><span class="c7">CDC-RFA-DP-24-0139</span><span class="c53 c7 c192">&nbsp;</span></p></body></html>',
                    "html.parser",
                )
            ),
            name,
        )


class HTMLSuggestThemeTests(TestCase):
    def test_suggest_nofo_number_hrsa_returns_hrsa_theme(self):
        nofo_number = "HRSA-24-019"
        nofo_theme = "portrait-hrsa-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_cdc_returns_cdc_theme(self):
        nofo_number = "CDC-RFA-DP-24-0139"
        nofo_theme = "portrait-cdc-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_acf_returns_acf_theme(self):
        nofo_number = "HHS-2024-ACF-ANA-NB-0050"
        nofo_theme = "portrait-acf-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_acl_returns_hrsa_theme(self):
        nofo_number = "HHS-2024-ACL-NIDILRR-REGE-0078"
        nofo_theme = "portrait-hrsa-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_no_match_returns_hrsa_theme(self):
        nofo_number = "abc-def-ghi"
        nofo_theme = "portrait-hrsa-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_empty_returns_hrsa_theme(self):
        nofo_number = ""
        nofo_theme = "portrait-hrsa-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)


class SuggestNofoOpDivTests(TestCase):
    def test_opdiv_present_in_paragraph(self):
        html = "<div><p>Opdiv: Center for Awesome NOFOs</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_opdiv(soup), "Center for Awesome NOFOs")

    def test_opdiv_present_not_in_paragraph(self):
        html = "<div><span>Opdiv: Center for Awesome NOFOs</span></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_opdiv(soup), "Center for Awesome NOFOs")

    def test_opdiv_not_present(self):
        html = "<div><p>Center for Awesome NOFOs</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_opdiv(soup), "")

    def test_opdiv_present_but_no_parent_paragraph(self):
        html = "<div>Opdiv: Center for Awesome NOFOs</div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_opdiv(soup), "Center for Awesome NOFOs")

    def test_opdiv_present_weird_casing(self):
        html = "<div><p><span>OPdiV: </span><span>Center for </span><span>Awesome NOFOs</span></p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_opdiv(soup), "Center for Awesome NOFOs")

    def test_opdiv_present_broken_up_by_spans(self):
        html = "<div><p><span>Opdiv: </span><span>Center for </span><span>Awesome NOFOs</span></p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_opdiv(soup), "Center for Awesome NOFOs")


class SuggestNofoAgencyTests(TestCase):
    def test_agency_present_in_paragraph(self):
        html = "<div><p>Agency: Agency for Weird Tables</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_agency(soup), "Agency for Weird Tables")

    def test_agency_present_not_in_paragraph(self):
        html = "<div><span>Agency: Agency for Weird Tables</span></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_agency(soup), "Agency for Weird Tables")

    def test_agency_not_present(self):
        html = "<div><p>Agency for Weird Tables</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_agency(soup), "")

    def test_agency_present_but_no_parent_paragraph(self):
        html = "<div>Agency: Agency for Weird Tables</div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_agency(soup), "Agency for Weird Tables")

    def test_agency_present_broken_up_by_spans(self):
        html = "<div><p><span>Agency: </span><span>Agency for </span><span>Weird Tables</span></p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_agency(soup), "Agency for Weird Tables")


class SuggestNofoSubagencyTests(TestCase):
    def test_subagency_present_in_paragraph(self):
        html = "<div><p>Subagency: Subagency for Multiple Header Rows</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(
            suggest_nofo_subagency(soup), "Subagency for Multiple Header Rows"
        )

    def test_subagency_present_not_in_paragraph(self):
        html = "<div><span>Subagency: Subagency for Multiple Header Rows</span></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(
            suggest_nofo_subagency(soup), "Subagency for Multiple Header Rows"
        )

    def test_subagency_not_present(self):
        html = "<div><p>Subagency for Multiple Header Rows</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_subagency(soup), "")

    def test_subagency_present_but_no_parent_paragraph(self):
        html = "<div>Subagency: Subagency for Multiple Header Rows</div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(
            suggest_nofo_subagency(soup), "Subagency for Multiple Header Rows"
        )

    def test_subagency_present_broken_up_by_spans(self):
        html = "<div><p><span>Subagency: </span><span>Subagency for </span><span>Multiple Header Rows</span></p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(
            suggest_nofo_subagency(soup), "Subagency for Multiple Header Rows"
        )


class SuggestNofoSubagency2Tests(TestCase):
    def test_subagency2_present_in_paragraph(self):
        html = "<div><p>Subagency2: Subagency for Complex Tables</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_subagency2(soup), "Subagency for Complex Tables")

    def test_subagency2_present_not_in_paragraph(self):
        html = "<div><span>Subagency2: Subagency for Complex Tables</span></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_subagency2(soup), "Subagency for Complex Tables")

    def test_subagency2_not_present(self):
        html = "<div><p>Subagency: Subagency for Complex Tables</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_subagency2(soup), "")

    def test_subagency2_present_broken_up_by_spans(self):
        html = "<div><p><span>Subagency2: </span><span>Subagency for </span><span>Complex Tables</span></p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_subagency2(soup), "Subagency for Complex Tables")


class SuggestNofoTaglineTests(TestCase):
    def test_tagline_present_in_paragraph(self):
        html = "<div><p>Tagline: The best NOFO ever</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_tagline(soup), "The best NOFO ever")

    def test_tagline_present_not_in_paragraph(self):
        html = "<div><span>Tagline: The best NOFO ever</span></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_tagline(soup), "The best NOFO ever")

    def test_tagline_not_present(self):
        html = "<div><p>The best NOFO ever</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_tagline(soup), "")

    def test_tagline_present_but_no_parent_paragraph(self):
        html = "<div>Tagline: The best NOFO ever</div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_tagline(soup), "The best NOFO ever")

    def test_tagline_present_broken_up_by_spans(self):
        html = "<div><p><span>Tagline: </span><span>The best </span><span>NOFO ever</span></p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_tagline(soup), "The best NOFO ever")


class SuggestNofoAuthorTests(TestCase):
    def test_author_present_in_paragraph(self):
        html = "<div><p>Metadata Author: Paul Craig</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_author(soup), "Paul Craig")

    def test_author_not_present(self):
        html = "<div><p>Author: Paul Craig</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_author(soup), "")

    def test_author_present_but_lowercased(self):
        html = "<div><p>metadata author: Paul Craig</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_author(soup), "Paul Craig")


class SuggestNofoSubjectTests(TestCase):
    def test_subject_present_in_paragraph(self):
        html = "<div><p>Metadata Subject: This NOFO is about helping people</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(
            suggest_nofo_subject(soup), "This NOFO is about helping people"
        )

    def test_subject_not_present(self):
        html = "<div><p>Subject: Medicine, CDC, Awesome, Notice, Opportunity</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_subject(soup), "")

    def test_subject_present_but_lowercased(self):
        html = "<div><p>metadata subject: This NOFO is about helping people</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(
            suggest_nofo_subject(soup), "This NOFO is about helping people"
        )


###########################################################
#################### MUTATE HTML TESTS ####################
###########################################################


class CombineLinksTestCase(TestCase):
    def test_consecutive_links_merged(self):
        html = '<p>See <a href="#link">link</a><a href="#link">.</a></p>'
        expected_html = '<p>See <a href="#link">link.</a></p>'
        soup = BeautifulSoup(html, "html.parser")
        combine_consecutive_links(soup)
        self.assertEqual(str(soup), expected_html)

    def test_span_wrapped_links_unwrapped_and_merged(self):
        html = '<p>Check <span><a href="#link">this link</a></span><span><a href="#link">.</a></span></p>'
        expected_html = '<p>Check <a href="#link">this link.</a></p>'
        soup = BeautifulSoup(html, "html.parser")
        combine_consecutive_links(soup)
        self.assertEqual(str(soup), expected_html)

    def test_non_consecutive_links_not_merged(self):
        html = '<p><a href="#link1">Link1</a> and <a href="#link2">Link2</a></p>'
        soup = BeautifulSoup(html, "html.parser")
        combine_consecutive_links(soup)
        self.assertEqual(str(soup), html)

    def test_different_href_links_not_merged(self):
        html = '<p>See <a href="#link1">link one</a><a href="#link2">link two</a></p>'
        soup = BeautifulSoup(html, "html.parser")
        combine_consecutive_links(soup)
        self.assertEqual(str(soup), html)

    def test_links_with_text_between_not_merged(self):
        html = (
            '<p>See <a href="#link">link</a> and <a href="#link">another link</a>.</p>'
        )
        soup = BeautifulSoup(html, "html.parser")
        combine_consecutive_links(soup)
        self.assertEqual(str(soup), html)

    def test_links_with_whitespace_between_not_merged(self):
        html = '<p>See <a href="#link">link +</a> <a href="#link">another link</a>.</p>'
        expected_html = '<p>See <a href="#link">link + another link</a>.</p>'
        soup = BeautifulSoup(html, "html.parser")
        combine_consecutive_links(soup)
        self.assertEqual(str(soup), expected_html)

    def test_links_with_one_span_one_no_span_are_merged(self):
        html = '<p>See <a href="#link">this link </a><span><a href="#link">is combined</a></span>.</p>'
        expected_html = '<p>See <a href="#link">this link is combined</a>.</p>'
        soup = BeautifulSoup(html, "html.parser")
        combine_consecutive_links(soup)
        self.assertEqual(str(soup), expected_html)


class SuggestNofoKeywordsTests(TestCase):
    def test_keywords_present_in_paragraph(self):
        html = "<div><p>Metadata Keywords: Medicine, CDC, Awesome, Notice, Opportunity</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(
            suggest_nofo_keywords(soup), "Medicine, CDC, Awesome, Notice, Opportunity"
        )

    def test_keywords_not_present(self):
        html = "<div><p>Keywords: Medicine, CDC, Awesome, Notice, Opportunity</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_keywords(soup), "")

    def test_keywords_present_but_lowercased(self):
        html = "<div><p>metadata keywords: Medicine, CDC, Awesome, Notice, Opportunity</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(
            suggest_nofo_keywords(soup), "Medicine, CDC, Awesome, Notice, Opportunity"
        )

    def test_keywords_present_broken_up_by_spans(self):
        html = "<div><p><span>Metadata keywords: </span><span>Medicine, CDC, </span><span>Awesome,</span> Notice, Opportunity</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(
            suggest_nofo_keywords(soup), "Medicine, CDC, Awesome, Notice, Opportunity"
        )


class TestDecomposeEmptyTags(TestCase):
    def test_remove_empty_tags(self):
        html = "<body><div></div><p>  </p><span>Text</span><br></body>"
        soup = BeautifulSoup(html, "html.parser")
        decompose_empty_tags(soup)
        self.assertEqual(len(soup.find_all("div")), 0)
        self.assertEqual(len(soup.find_all("p")), 0)
        self.assertEqual(len(soup.find_all("span")), 1)

    def test_keep_non_empty_tags(self):
        html = "<body><div>Content</div><p>Text</p></body>"
        soup = BeautifulSoup(html, "html.parser")
        decompose_empty_tags(soup)
        self.assertEqual(len(soup.find_all("div")), 1)
        self.assertEqual(len(soup.find_all("p")), 1)

    def test_keep_br_and_hr_tags(self):
        html = "<body><br><hr></body>"
        soup = BeautifulSoup(html, "html.parser")
        decompose_empty_tags(soup)
        self.assertEqual(len(soup.find_all("br")), 1)
        self.assertEqual(len(soup.find_all("hr")), 1)

    def test_remove_empty_nested_tags(self):
        html = "<body><div><p></p></div><span>Hello</span></body>"
        soup = BeautifulSoup(html, "html.parser")
        decompose_empty_tags(soup)
        self.assertEqual(len(soup.find_all("div")), 0)
        self.assertEqual(len(soup.find_all("span")), 1)

    def test_remove_empty_nested_tags(self):
        html = "<body><div><p><a href='#'></a></p></div><div><span>Hello</span></div></body>"
        soup = BeautifulSoup(html, "html.parser")
        decompose_empty_tags(soup)
        # first div is removed because everything is empty
        self.assertEqual(len(soup.find_all("div")), 1)
        self.assertEqual(len(soup.find_all("a")), 0)

    def test_keep_empty_nested_tags_if_parent_tag_is_not_empty(self):
        html = "<body><div><p><a href='#'></a></p><span>Hello</span></div><div><span>Hello</span></div></body>"
        soup = BeautifulSoup(html, "html.parser")
        decompose_empty_tags(soup)
        # first div is kept because span in first div is not empty
        self.assertEqual(len(soup.find_all("div")), 2)
        # empty anchor tag is kept
        self.assertEqual(len(soup.find_all("a")), 1)

    def test_remove_empty_list_items(self):
        html = "<body><div><p>Hello</p><ul><li></li><li>Item</li></ul></div></body>"
        soup = BeautifulSoup(html, "html.parser")
        decompose_empty_tags(soup)
        self.assertEqual(len(soup.find_all("li")), 1)  # Only one li should remain

    def test_handle_completely_empty_body(self):
        html = "<body>   </body>"
        soup = BeautifulSoup(html, "html.parser")
        decompose_empty_tags(soup)
        self.assertEqual(soup.body.contents, [" "])  # Body should be empty


class TestRemoveGoogleTrackingInfoFromLinks(TestCase):
    def test_remove_tracking_from_google_links(self):
        html = '<a href="https://www.google.com/url?q=https://www.cdc.gov/link&sa=D&source=editors&ust=1234567890&usg=AOvVaw0"></a>'
        soup = BeautifulSoup(html, "html.parser")
        remove_google_tracking_info_from_links(soup)
        self.assertEqual(soup.find("a")["href"], "https://www.cdc.gov/link")

    def test_ignore_non_google_links(self):
        html = '<a href="https://www.example.com"></a>'
        soup = BeautifulSoup(html, "html.parser")
        remove_google_tracking_info_from_links(soup)
        self.assertEqual(soup.find("a")["href"], "https://www.example.com")

    def test_handle_multiple_links(self):
        html = """
        <a href="https://www.google.com/url?q=https://www.cdc.gov/link1&sa=D"></a>
        <a href="https://www.google.com/url?q=https://www.cdc.gov/link2&sa=D"></a>
        <a href="https://www.example.com/link3"></a>
        """
        soup = BeautifulSoup(html, "html.parser")
        remove_google_tracking_info_from_links(soup)
        self.assertEqual(soup.find_all("a")[0]["href"], "https://www.cdc.gov/link1")
        self.assertEqual(soup.find_all("a")[1]["href"], "https://www.cdc.gov/link2")
        self.assertEqual(soup.find_all("a")[2]["href"], "https://www.example.com/link3")

    def test_remove_tracking_from_google_links_with_hashtag_in_url(self):
        html = '<a href="https://www.google.com/url?q=https://www.cdc.gov/grants/already-have-grant/Reporting.html%23:~:text%3DCDC%2520requires%2520recipient%2520to%2520submit,Progress%2520Reports&sa=D&source=editors&ust=1706211338264361&usg=AOvVaw0n3u21sko3WVBKQUeWKGyP"></a>'
        soup = BeautifulSoup(html, "html.parser")
        remove_google_tracking_info_from_links(soup)
        self.assertEqual(
            soup.find("a")["href"],
            "https://www.cdc.gov/grants/already-have-grant/Reporting.html#:~:text=CDC%20requires%20recipient%20to%20submit,Progress%20Reports",
        )

    def test_remove_tracking_from_google_links_with_equals_sign_in_url(self):
        html = '<a href="https://www.google.com/url?q=https://cdc.zoomgov.com/j/1609422163?pwd%3DQVFuNzZLWTRMTXMrT2hURkFnb21LUT09&sa=D&source=editors&ust=1706211338171041&usg=AOvVaw1zbYZH1Hv5HZQJbFp5VXbT"></a>'
        soup = BeautifulSoup(html, "html.parser")
        remove_google_tracking_info_from_links(soup)
        self.assertEqual(
            soup.find("a")["href"],
            "https://cdc.zoomgov.com/j/1609422163?pwd=QVFuNzZLWTRMTXMrT2hURkFnb21LUT09",
        )


class TestReplaceSrcForInlineImages(TestCase):
    @patch("nofos.nofo.suggest_nofo_opportunity_number")
    def test_replace_src_when_nofo_number_is_not_default(self, mock_suggest_nofo):
        mock_suggest_nofo.return_value = "hrsa-24-017"
        html = '<img src="images/image1.png">'
        soup = BeautifulSoup(html, "html.parser")

        replace_src_for_inline_images(soup)
        self.assertEqual(
            soup.find("img")["src"], "/static/img/inline/hrsa-24-017/image1.png"
        )

    @patch("nofos.nofo.suggest_nofo_opportunity_number")
    def test_do_not_replace_src_when_nofo_number_is_default(self, mock_suggest_nofo):
        mock_suggest_nofo.return_value = DEFAULT_NOFO_OPPORTUNITY_NUMBER
        html = '<img src="images/image1.png">'
        soup = BeautifulSoup(html, "html.parser")

        replace_src_for_inline_images(soup)
        self.assertEqual(soup.find("img")["src"], "images/image1.png")

    @patch("nofos.nofo.suggest_nofo_opportunity_number")
    def test_ignore_img_without_src(self, mock_suggest_nofo):
        mock_suggest_nofo.return_value = "hrsa-24-017"
        html = "<img alt='no src, deal with it'>"
        soup = BeautifulSoup(html, "html.parser")

        replace_src_for_inline_images(soup)
        self.assertIsNone(soup.find("img").get("src"))


class TestAddEndnotesHeaderIfExists(TestCase):
    def test_basic_with_hr_without_style(self):
        html_content = "<div><hr></div>"
        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup)
        self.assertEqual(
            str(soup),
            "<div><h1>Endnotes</h1><h2>Select the endnote number to jump to the related section in the document.</h2></div>",
        )

    def test_no_hr_tags_present(self):
        html_content = "<div><p>Some text</p></div>"
        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup)
        self.assertEqual(str(soup), "<div><p>Some text</p></div>")

    def test_multiple_hr_tags_with_styles(self):
        html_content = """<div><hr style="color: red;"/><hr style="border: 1px solid blue;"/><hr style="font-size: 14px;"/></div>"""

        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup)
        self.assertEqual(
            str(soup),
            """<div><hr style="color: red;"/><hr style="border: 1px solid blue;"/><hr style="font-size: 14px;"/></div>""",
        )

    def test_multiple_hr_tags_without_style(self):
        html_content = "<div><hr/><hr/></div>"
        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup)
        self.assertEqual(
            str(soup),
            "<div><hr/><h1>Endnotes</h1><h2>Select the endnote number to jump to the related section in the document.</h2></div>",
        )


class TestEscapeAsterisksInTableCells(TestCase):
    def test_asterisk_escaped_in_table_cells(self):
        html = "<table><tr><td>Test* Text</td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        escape_asterisks_in_table_cells(soup)
        self.assertIn(r"Test\* Text", soup.td.text)

    def test_already_escaped_asterisk_not_doubly_escaped(self):
        html = "<table><tr><td>Test\\* Text</td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        escape_asterisks_in_table_cells(soup)
        self.assertIn(r"Test\* Text", soup.td.text)
        self.assertNotIn(r"Test\\* Text", soup.td.text)

    def test_multiple_asterisks_escaped(self):
        html = "<table><tr><td>*Test* Text*</td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        escape_asterisks_in_table_cells(soup)
        self.assertIn(r"\*Test\* Text\*", soup.td.text)

    def test_no_asterisks_unmodified(self):
        html = "<table><tr><td>No asterisks here</td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        original_text = soup.td.text
        escape_asterisks_in_table_cells(soup)
        self.assertEqual(original_text, soup.td.text)

    def test_asterisk_in_nested_tags_preserved(self):
        html = "<table><tr><td>Before <span>Test* Text</span> After</td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        escape_asterisks_in_table_cells(soup)
        self.assertIn(r"Test\* Text", soup.span.text)

    def test_asterisk_outside_of_table_not_modified(self):
        html = "<div><p>Test*</p><table><tr><td>Test* Text</td></tr></table></div>"
        soup = BeautifulSoup(html, "html.parser")
        escape_asterisks_in_table_cells(soup)
        self.assertIn(
            str(soup),
            "<div><p>Test*</p><table><tr><td>Test\\* Text</td></tr></table></div>",
        )


class TestGetFontSizeFromCssText(TestCase):
    def test_get_font_size_in_points(self):
        css_text = """
        background-color: #fff;
        color: #000;
        font-weight: 700;
        text-decoration: none;
        vertical-align: baseline;
        font-size: 12pt;
        font-family: "Calibri";
        font-style: normal
        """
        self.assertEqual(get_font_size_from_cssText(css_text), 12)

    def test_get_font_size_in_points_with_decimal(self):
        css_text = """
        font-size: 10.5pt;
        """
        self.assertEqual(get_font_size_from_cssText(css_text), "10.5pt")

    def test_get_font_size_in_pixels(self):
        css_text = """
        font-size: 16px;
        """
        self.assertEqual(get_font_size_from_cssText(css_text), "16px")

    def test_font_size_missing(self):
        css_text = """
        background-color: #fff;
        color: #000;
        """
        with self.assertRaises(IndexError):
            get_font_size_from_cssText(css_text)

    def test_font_size_with_extra_spaces(self):
        css_text = """
        font-size:    14pt   ;
        """
        self.assertEqual(get_font_size_from_cssText(css_text), 14)

    def test_font_size_with_multiple_rules(self):
        css_text = """
        font-size: 10pt;
        font-size: 18pt;
        """
        self.assertEqual(
            get_font_size_from_cssText(css_text), 18
        )  # Should return the last defined size


class TestGetClassnamesForFontWeightBold(TestCase):
    def test_get_classnames_for_bold_font_weight(self):
        styles_as_text = """
        .c1{font-weight:700;font-size:12pt;}
        .c2{font-weight:700;font-size:18px;}
        .c3{font-weight:700;font-size:36pt;}
        """
        expected_classes = {"c1", "c2"}
        self.assertEqual(
            get_classnames_for_font_weight_bold(styles_as_text), expected_classes
        )

    def test_exclude_large_font_size(self):
        styles_as_text = """
        .c1{font-weight:700;font-size:12pt;}
        .c3{font-weight:700;font-size:36pt;}
        """
        expected_classes = {"c1"}
        self.assertEqual(
            get_classnames_for_font_weight_bold(styles_as_text), expected_classes
        )

    def test_no_bold_font_weight(self):
        styles_as_text = """
        .c1{font-weight:400;font-size:12pt;}
        .c2{font-weight:400;font-size:18px;}
        """
        expected_classes = set()
        self.assertEqual(
            get_classnames_for_font_weight_bold(styles_as_text), expected_classes
        )

    def test_mixed_rules(self):
        styles_as_text = """
        .c1{font-weight:700;font-size:12pt;}
        .c2{font-weight:700;}
        .c3{font-size:36pt;}
        .c4{font-weight:700;font-size:16pt;}
        """
        expected_classes = {"c1", "c2", "c4"}
        self.assertEqual(
            get_classnames_for_font_weight_bold(styles_as_text), expected_classes
        )


class TestAddStrongsToSoup(TestCase):
    def test_add_strongs_to_elements(self):
        html = """
        <html>
            <head>
                <style>.bold{font-weight:700;}</style>
            </head>
            <body>
                <p><span class="bold">Bold text</span></p>
                <p>Normal text</p>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        add_strongs_to_soup(soup)
        self.assertEqual(soup.find("span", class_="bold").parent.name, "strong")

    def test_do_not_bold_elements_in_first_row_td(self):
        html = """
        <html>
            <head>
                <style>.bold{font-weight:700;}</style>
            </head>
            <table>
                <tr>
                    <td><span class="bold first-row">Bold heading</span></th>
                </tr>
                <tr>
                    <td><span class="bold second-row">Bold heading</span></th>
                </tr>
            </table>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        add_strongs_to_soup(soup)

        # no strong tag on this one
        self.assertEqual(soup.find("span", class_="first-row").parent.name, "td")
        self.assertEqual(soup.find("span", class_="second-row").parent.name, "strong")

    def test_multiple_bold_elements(self):
        html = """
        <html>
            <head>
                <style>.bold{font-weight:700;}</style>
            </head>
            <body>
                <p><span class="bold">First bold text</span></p>
                <p><span class="bold">Second bold text</span></p>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        add_strongs_to_soup(soup)
        bold_elements = soup.find_all("span", class_="bold")
        for element in bold_elements:
            self.assertEqual(element.parent.name, "strong")

    def test_do_not_bold_heading_classes(self):
        html = """
        <html>
            <head>
                <style>
                    .bold-heading{font-weight:700; font-size: 36pt;}
                    .bold{font-weight:700;}
                </style>
            </head>
            <body>
                <h1><span class="bold-heading">First bold text</span></h1>
                <p><span class="bold">Second bold text</span></p>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        add_strongs_to_soup(soup)
        self.assertEqual(soup.find("span", class_="bold-heading").parent.name, "h1")
        self.assertEqual(soup.find("span", class_="bold").parent.name, "strong")

    def test_do_not_bold_other_font_weights(self):
        html = """
        <html>
            <head>
                <style>
                    .bold-600{font-weight:600;}
                    .bold-700{font-weight:700;}
                    .bold-800{font-weight:800;}
                </style>
            </head>
            <body>
                <p><span class="bold-600">Bold text 600</span></p>
                <p><span class="bold-700">Bold text 700</span></p>
                <p><span class="bold-800">Bold text 800</span></p>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        add_strongs_to_soup(soup)
        self.assertEqual(soup.find("span", class_="bold-600").parent.name, "p")
        self.assertEqual(soup.find("span", class_="bold-700").parent.name, "strong")
        self.assertEqual(soup.find("span", class_="bold-800").parent.name, "p")

    def test_multiple_bold_classes_are_added(self):
        html = """
        <html>
            <head>
                <style>
                    .bold-1{font-weight:700; font-size: 20pt;}
                    .bold-2{font-weight:700; font-size: 10pt;}
                    .bold-3{font-weight:700; font-size: 100px;}
                </style>
            </head>
            <body>
                <p><span class="bold-1">Bold text 1</span></p>
                <p><span class="bold-2">Bold text 2</span></p>
                <p><span class="bold-3">Bold text 3</span></p>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        add_strongs_to_soup(soup)
        self.assertEqual(soup.find("span", class_="bold-1").parent.name, "p")
        self.assertEqual(soup.find("span", class_="bold-2").parent.name, "strong")
        self.assertEqual(soup.find("span", class_="bold-3").parent.name, "strong")


###########################################################
################### NESTED LIST TESTS #####################
###########################################################


class NestedListTests(TestCase):
    def setUp(self):
        self.html_single_list = """
            <h4 class="c1"><span class="c35">Funding strategy</span></h4>
            <p class="c9"><span class="c4">Funding may differ based on demonstration of need such as burden data, reach of proposed activities, and availability of funds.</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c77 c58 c96">Component 1:</span><span class="c4">&nbsp;If funding allows, we intend to fund up to 35 organizations for Component 1.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c77 c58 c96">Component 2:</span><span class="c4">&nbsp;If funding allows, we intend to fund up to 5 organizations for Component 2.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c77 c58 c96">Component 3:</span><span class="c4">&nbsp;If funding allows, we intend to fund up to 50 states, 7 U.S. territories, and 2 tribal nations for Component 3. We will fund only one Component 3 application per state, territory, or tribal nation. </span></li>
            </ul>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

        self.html_nested_list = """
            <h6 class="c27" id="h.3rdcrjn"><span class="c77 c54">Strategy 1A – Health education (HED)</span></h6>
            <p class="c9"><span class="c4">You will implement a technical assistance plan and provide professional development to support the delivery of quality health education through the following activities:</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">HED1. Develop, implement, and review a technical assistance plan. Its goal is to support and improve teacher and school staff’s knowledge, comfort, and skills for delivering health education to students in secondary grades (6 to 12). This includes sexual and mental health education.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HED2. Each year, provide professional development for teachers and school staff delivering health education instructional programs to students in secondary grades (6 to 12). This includes sexual health and mental health education. Prioritize instructional competencies needed for culturally responsive and inclusive education.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HED3. Each year, implement a health education instructional program for students in grades K to 12. Health education instructional programs should: </span></li>
            </ul>
            <ul class="c34 lst-kix_list_7-0 start">
                <li class="c91 c80 li-bullet-0"><span class="c4">Align with a district or school scope and sequence</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Be culturally responsive, inclusive, developmentally appropriate, and focused on meeting the needs of students who have been marginalized, including students from racial and ethnic minority groups, students who identify as LGBTQ+, and students with intellectual and developmental disabilities</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Incorporate sexual and mental health content</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Prioritize skills to identify and access health services</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Assess student performance</span></li>
            </ul>
        """

        self.html_nested_list_followed_by_li = """
            <h6 class="c27" id="h.26in1rg"><span class="c77 c54">Strategy 1B – Health services (HS)</span></h6>
            <p class="c9"><span class="c4">You will assess district and school capacity and implement a plan to increase access to school- and community-based services through the following activities:</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">HS1. Each year, assess district and school capacity, infrastructure, and partnerships. The assessment reviews the ability to implement activities that increase student access to youth-friendly and inclusive sexual, behavioral, and mental health services.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HS2. Build partnerships with health care providers. The goal is to support student access to youth-friendly and inclusive sexual, behavioral, and mental health services.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HS3. Provide annual professional development to help staff support student access to health services, specifically sexual, behavioral, and mental health services. Each year, you must provide professional development to both: </span></li>
            </ul>
            <ul class="c34 lst-kix_list_22-0 start">
                <li class="c9 c80 li-bullet-0"><span class="c4">Staff who provide health services, and </span></li>
                <li class="c9 c80 li-bullet-0"><span class="c4">Other school staff</span></li>
            </ul>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">HS4. Implement or enhance school-based activities that increase access to services. The goal is to increase student access to youth-friendly and inclusive school- and community-based sexual, behavioral, and mental health services. Activities must include at least one of the following:</span></li>
            </ul>
        """

        self.html_2_nested_lists = """
            <h6 class="c27" id="h.26in1rg"><span class="c77 c54">Strategy 1B – Health services (HS)</span></h6>
            <p class="c9"><span class="c4">You will assess district and school capacity and implement a plan to increase access to school- and community-based services through the following activities:</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">HS1. Each year, assess district and school capacity, infrastructure, and partnerships. The assessment reviews the ability to implement activities that increase student access to youth-friendly and inclusive sexual, behavioral, and mental health services.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HS2. Build partnerships with health care providers. The goal is to support student access to youth-friendly and inclusive sexual, behavioral, and mental health services.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HS3. Provide annual professional development to help staff support student access to health services, specifically sexual, behavioral, and mental health services. Each year, you must provide professional development to both: </span></li>
            </ul>
            <ul class="c34 lst-kix_list_22-0 start">
                <li class="c9 c80 li-bullet-0"><span class="c4">Staff who provide health services, and </span></li>
                <li class="c9 c80 li-bullet-0"><span class="c4">Other school staff</span></li>
            </ul>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">HS4. Implement or enhance school-based activities that increase access to services. The goal is to increase student access to youth-friendly and inclusive school- and community-based sexual, behavioral, and mental health services. Activities must include at least one of the following:</span></li>
            </ul>
            <ul class="c34 lst-kix_list_7-0">
                <li class="c91 c80 li-bullet-0"><span class="c4">Create a referral system to link students to sexual, behavioral, and mental health services.</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Provide school-based sexual, behavioral, and mental health services to students. For example, STI screening, making condoms available, school-based counseling, and mental health supports.</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Provide school-based health center services that support sexual, behavioral, and mental health services for students.</span></li>
            </ul>
        """

        self.html_2_nested_lists_followed_by_li = """
            <h6 class="c27" id="h.26in1rg"><span class="c77 c54">Strategy 1B – Health services (HS)</span></h6>
            <p class="c9"><span class="c4">You will assess district and school capacity and implement a plan to increase access to school- and community-based services through the following activities:</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">HS1. Each year, assess district and school capacity, infrastructure, and partnerships. The assessment reviews the ability to implement activities that increase student access to youth-friendly and inclusive sexual, behavioral, and mental health services.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HS2. Build partnerships with health care providers. The goal is to support student access to youth-friendly and inclusive sexual, behavioral, and mental health services.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HS3. Provide annual professional development to help staff support student access to health services, specifically sexual, behavioral, and mental health services. Each year, you must provide professional development to both: </span></li>
            </ul>
            <ul class="c34 lst-kix_list_22-0 start">
                <li class="c9 c80 li-bullet-0"><span class="c4">Staff who provide health services, and </span></li>
                <li class="c9 c80 li-bullet-0"><span class="c4">Other school staff</span></li>
            </ul>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">HS4. Implement or enhance school-based activities that increase access to services. The goal is to increase student access to youth-friendly and inclusive school- and community-based sexual, behavioral, and mental health services. Activities must include at least one of the following:</span></li>
            </ul>
            <ul class="c34 lst-kix_list_7-0">
                <li class="c91 c80 li-bullet-0"><span class="c4">Create a referral system to link students to sexual, behavioral, and mental health services.</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Provide school-based sexual, behavioral, and mental health services to students. For example, STI screening, making condoms available, school-based counseling, and mental health supports.</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Provide school-based health center services that support sexual, behavioral, and mental health services for students.</span></li>
            </ul>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">Last bullet by itself</span></li>
            </ul>
        """

        self.html_double_nested_list = """
            <h6 class="c27"><span class="c77 c54">Strategy 1C – Safe and supportive environments (SSE)</span></h6>
            <p class="c9"><span class="c4">You will foster safe and supportive school environments and support the mental health and well-being of students and staff through the following activities:</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE2. Each year, provide professional development to school staff on fostering safe and supportive school environments. Professional development topics may include supporting youth with LGBTQ+ identities and racial and ethnic minority youth, classroom management, and mental health awareness and crisis response.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE3. Implement activities to support school staff’s mental health and well-being.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE4. Implement school-wide practices to support the behavioral and mental health and social and emotional well-being of students.</span></li>
            </ul>
            <ul class="c34 lst-kix_list_7-0">
                <li class="c91 c80 li-bullet-0"><span class="c4">Establish dedicated time within the school schedule for students to connect with teachers and peers. The goal is to hold structured discussions that promote social-emotional well-being and strengthen relationships. These might include advisory programs or periods and morning meetings.</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Implement schoolwide positive behavioral interventions and support for student and teacher well-being. This includes:</span></li>
            </ul>
            <ul class="c34 lst-kix_list_13-1 start">
                <li class="c91 c143 li-bullet-0"><span class="c4">Setting positive behavioral expectations for students</span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">Teaching academic and social behaviors that students need to meet school expectations</span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">Defining behaviors that negatively affect school environments </span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">Using positive disciplinary practices to respond to negative behaviors</span></li>
            </ul>
        """

        self.html_double_nested_list_followed_by_li = """
            <h6 class="c27"><span class="c77 c54">Strategy 1C – Safe and supportive environments (SSE)</span></h6>
            <p class="c9"><span class="c4">You will foster safe and supportive school environments and support the mental health and well-being of students and staff through the following activities:</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE2. Each year, provide professional development to school staff on fostering safe and supportive school environments. Professional development topics may include supporting youth with LGBTQ+ identities and racial and ethnic minority youth, classroom management, and mental health awareness and crisis response.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE3. Implement activities to support school staff’s mental health and well-being.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE4. Implement school-wide practices to support the behavioral and mental health and social and emotional well-being of students.</span></li>
            </ul>
            <ul class="c34 lst-kix_list_7-0">
                <li class="c91 c80 li-bullet-0"><span class="c4">Establish dedicated time within the school schedule for students to connect with teachers and peers. The goal is to hold structured discussions that promote social-emotional well-being and strengthen relationships. These might include advisory programs or periods and morning meetings.</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Implement schoolwide positive behavioral interventions and support for student and teacher well-being. This includes:</span></li>
            </ul>
            <ul class="c34 lst-kix_list_13-1 start">
                <li class="c91 c143 li-bullet-0"><span class="c4">Setting positive behavioral expectations for students</span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">Teaching academic and social behaviors that students need to meet school expectations</span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">Defining behaviors that negatively affect school environments </span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">Using positive disciplinary practices to respond to negative behaviors</span></li>
            </ul>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE5. Implement positive youth development approaches. Specifically, provide school-based mentoring, service learning, or other positive youth development programs or connect students to community-based programs.</span></li>
            </ul>
        """

        self.html_2_lists_to_join = """
            <h4 class="c1"><span class="c35">Funding strategy</span></h4>
            <p class="c9"><span class="c4">Funding may differ based on demonstration of need such as burden data, reach of proposed activities, and availability of funds.</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c77 c58 c96">Component 1:</span><span class="c4">&nbsp;If funding allows, we intend to fund up to 35 organizations for Component 1.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c77 c58 c96">Component 2:</span><span class="c4">&nbsp;If funding allows, we intend to fund up to 5 organizations for Component 2.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c77 c58 c96">Component 3:</span><span class="c4">&nbsp;If funding allows, we intend to fund up to 50 states, 7 U.S. territories, and 2 tribal nations for Component 3. We will fund only one Component 3 application per state, territory, or tribal nation. </span></li>
            </ul>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c77 c58 c96">Component 4:</span><span class="c4">&nbsp;If funding allows, we intend to fund up to 35 organizations for Component 1.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c77 c58 c96">Component 5:</span><span class="c4">&nbsp;If funding allows, we intend to fund up to 5 organizations for Component 2.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c77 c58 c96">Component 6:</span><span class="c4">&nbsp;If funding allows, we intend to fund up to 50 states, 7 U.S. territories, and 2 tribal nations for Component 3. We will fund only one Component 3 application per state, territory, or tribal nation. </span></li>
            </ul>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

        self.html_2_nested_lists_to_join = """
            <h6 class="c27"><span class="c77 c54">Strategy 1C – Safe and supportive environments (SSE)</span></h6>
            <p class="c9"><span class="c4">You will foster safe and supportive school environments and support the mental health and well-being of students and staff through the following activities:</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE2. Each year, provide professional development to school staff on fostering safe and supportive school environments. Professional development topics may include supporting youth with LGBTQ+ identities and racial and ethnic minority youth, classroom management, and mental health awareness and crisis response.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE3. Implement activities to support school staff’s mental health and well-being.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE4. Implement school-wide practices to support the behavioral and mental health and social and emotional well-being of students.</span></li>
            </ul>
            <ul class="c34 lst-kix_list_7-0">
                <li class="c91 c80 li-bullet-0"><span class="c4">1. Establish dedicated time within the school schedule for students to connect with teachers and peers. The goal is to hold structured discussions that promote social-emotional well-being and strengthen relationships. These might include advisory programs or periods and morning meetings.</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">2. Implement schoolwide positive behavioral interventions and support for student and teacher well-being. This includes:</span></li>
            </ul>
            <ul class="c34 lst-kix_list_7-0">
                <li class="c91 c143 li-bullet-0"><span class="c4">3. Setting positive behavioral expectations for students</span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">4. Teaching academic and social behaviors that students need to meet school expectations</span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">5. Defining behaviors that negatively affect school environments </span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">6. Using positive disciplinary practices to respond to negative behaviors</span></li>
            </ul>
        """

        self.html_2_nested_lists_to_join_after_double_nested_list = """
            <h6 class="c27"><span class="c77 c54">Strategy 1C – Safe and supportive environments (SSE)</span></h6>
            <p class="c9"><span class="c4">You will foster safe and supportive school environments and support the mental health and well-being of students and staff through the following activities:</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE2. Each year, provide professional development to school staff on fostering safe and supportive school environments. Professional development topics may include supporting youth with LGBTQ+ identities and racial and ethnic minority youth, classroom management, and mental health awareness and crisis response.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE3. Implement activities to support school staff’s mental health and well-being.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE4. Implement school-wide practices to support the behavioral and mental health and social and emotional well-being of students.</span></li>
            </ul>
            <ul class="c34 lst-kix_list_7-0">
                <li class="c91 c80 li-bullet-0"><span class="c4">1. Establish dedicated time within the school schedule for students to connect with teachers and peers. The goal is to hold structured discussions that promote social-emotional well-being and strengthen relationships. These might include advisory programs or periods and morning meetings.</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">2. Implement schoolwide positive behavioral interventions and support for student and teacher well-being. This includes:</span></li>
            </ul>
            <ul class="c34 lst-kix_list_13-1 start">
                <li class="c91 c143 li-bullet-0"><span class="c4">Setting positive behavioral expectations for students</span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">Teaching academic and social behaviors that students need to meet school expectations</span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">Defining behaviors that negatively affect school environments </span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">Using positive disciplinary practices to respond to negative behaviors</span></li>
            </ul>
            <ul class="c34 lst-kix_list_7-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">3. Implement positive youth development approaches. Specifically, provide school-based mentoring, service learning, or other positive youth development programs or connect students to community-based programs.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">4. Implement positive youth development approaches. Specifically, provide school-based mentoring, service learning, or other positive youth development programs or connect students to community-based programs.</span></li>
            </ul>
        """

    def test_single_list_nothing_happens(self):
        soup = join_nested_lists(BeautifulSoup(self.html_single_list, "html.parser"))
        self.assertEqual(len(soup.select("ul")), 1)

        # last li of first list DOES NOT HAVE a nested ul
        last_li = soup.find("ul").find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ul")), 0)

    def test_nested_list_becomes_nested(self):
        soup = join_nested_lists(BeautifulSoup(self.html_nested_list, "html.parser"))
        # two uls
        self.assertEqual(len(soup.select("ul")), 2)
        # one nested list
        self.assertEqual(len(soup.select("ul > li > ul")), 1)
        # no uls are siblings
        self.assertEqual(len(soup.select("ul + ul")), 0)

        # last li of first list HAS a nested ul
        last_li = soup.find("ul").find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ul")), 1)

    def test_nested_list_becomes_nested_and_last_item_added_to_first_list(self):
        soup = join_nested_lists(
            BeautifulSoup(self.html_nested_list_followed_by_li, "html.parser")
        )

        # two uls
        self.assertEqual(len(soup.select("ul")), 2)
        # one nested list
        self.assertEqual(len(soup.select("ul > li > ul")), 1)
        # no uls are siblings
        self.assertEqual(len(soup.select("ul + ul")), 0)

        # first ul has 4 li children
        first_ul = soup.find("ul")
        self.assertEqual(len(first_ul.find_all("li", recursive=False)), 4)

    def test_2_nested_lists_become_nested(self):
        soup = join_nested_lists(BeautifulSoup(self.html_2_nested_lists, "html.parser"))
        # three uls
        self.assertEqual(len(soup.select("ul")), 3)
        # two nested lists
        self.assertEqual(len(soup.select("ul > li > ul")), 2)
        # no uls are siblings
        self.assertEqual(len(soup.select("ul + ul")), 0)

        # first ul has 4 li children
        first_ul = soup.find("ul")
        self.assertEqual(len(first_ul.find_all("li", recursive=False)), 4)

        # last li of first list HAS a nested ul
        last_li = first_ul.find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ul")), 1)

    def test_2_nested_lists_becomes_nested_and_last_item_added_to_first_list(self):
        soup = join_nested_lists(
            BeautifulSoup(self.html_2_nested_lists_followed_by_li, "html.parser")
        )
        # three uls
        self.assertEqual(len(soup.select("ul")), 3)
        # two nested lists
        self.assertEqual(len(soup.select("ul > li > ul")), 2)
        # no uls are siblings
        self.assertEqual(len(soup.select("ul + ul")), 0)

        # first ul has 5 li children
        first_ul = soup.find("ul")
        self.assertEqual(len(first_ul.find_all("li", recursive=False)), 5)

        # last li of first list DOES NOT HAVE a nested ul
        last_li = first_ul.find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ul")), 0)

    def test_double_nested_list_becomes_nested(self):
        soup = join_nested_lists(
            BeautifulSoup(self.html_double_nested_list, "html.parser")
        )
        # three uls
        self.assertEqual(len(soup.select("ul")), 3)
        # two single nested lists
        self.assertEqual(len(soup.select("ul > li > ul")), 2)
        # one double nested list
        self.assertEqual(len(soup.select("ul > li > ul > li > ul")), 1)
        # no uls are siblings
        self.assertEqual(len(soup.select("ul + ul")), 0)

        # first ul has 3 li children
        first_ul = soup.find("ul")
        self.assertEqual(len(first_ul.find_all("li", recursive=False)), 3)

        # last li of first list HAS 2 uls
        last_li = first_ul.find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ul")), 2)

    def test_double_nested_list_becomes_nested_and_last_item_added_to_first_list(self):
        soup = join_nested_lists(
            BeautifulSoup(self.html_double_nested_list_followed_by_li, "html.parser")
        )
        # three uls
        self.assertEqual(len(soup.select("ul")), 3)
        # two single nested lists
        self.assertEqual(len(soup.select("ul > li > ul")), 2)
        # one double nested list
        self.assertEqual(len(soup.select("ul > li > ul > li > ul")), 1)
        # no uls are siblings
        self.assertEqual(len(soup.select("ul + ul")), 0)

        # first ul has 4 li children
        first_ul = soup.find("ul")
        self.assertEqual(len(first_ul.find_all("li", recursive=False)), 4)

        # last li of first list DOES NOT HAVE uls
        last_li = first_ul.find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ul")), 0)

    def test_join_2_lists_with_same_classname(self):
        soup = join_nested_lists(
            BeautifulSoup(self.html_2_lists_to_join, "html.parser")
        )
        # two uls
        self.assertEqual(len(soup.select("ul")), 1)
        # one nested list
        self.assertEqual(len(soup.select("ul > li > ul")), 0)
        # no uls are siblings
        self.assertEqual(len(soup.select("ul + ul")), 0)

        # first ul has 6 li children
        first_ul = soup.find("ul")
        self.assertEqual(len(first_ul.find_all("li", recursive=False)), 6)

    def test_join_2_nested_lists_with_same_classname(self):
        soup = join_nested_lists(
            BeautifulSoup(self.html_2_nested_lists_to_join, "html.parser")
        )
        # two uls
        self.assertEqual(len(soup.select("ul")), 2)
        # one nested list
        self.assertEqual(len(soup.select("ul > li > ul")), 1)
        # no uls are siblings
        self.assertEqual(len(soup.select("ul + ul")), 0)

        # last li of first list HAS a nested ul
        last_li = soup.find("ul").find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ul")), 1)
        # nested ul has 5 lis
        self.assertEqual(len(last_li.find("ul").find_all("li")), 6)

    def test_join_2_nested_lists_with_same_classname_after_a_double_nested_list(self):
        soup = join_nested_lists(
            BeautifulSoup(
                self.html_2_nested_lists_to_join_after_double_nested_list, "html.parser"
            )
        )
        # three uls
        self.assertEqual(len(soup.select("ul")), 3)
        # two nested lists
        self.assertEqual(len(soup.select("ul > li > ul")), 2)
        # one double nested list
        self.assertEqual(len(soup.select("ul > li > ul > li > ul")), 1)
        # no uls are siblings
        self.assertEqual(len(soup.select("ul + ul")), 0)

        # last li of first list HAS a nested ul
        last_li = soup.find("ul").find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ul")), 2)
        # nested ul has 5 lis
        self.assertEqual(len(last_li.find("ul").find_all("li", recursive=False)), 4)


###########################################################
#################### CALLOUT BOX TESTS ####################
###########################################################


class HTMLCalloutBoxTests(TestCase):
    def assertSubsectionsMatch(self, subsections, subsections_assertions):
        for index, _s in enumerate(subsections):
            self.assertEqual(_s.get("name"), subsections_assertions[index]["name"])
            self.assertEqual(
                _s.get("is_callout_box"), subsections_assertions[index]["callout_box"]
            )

    def get_subsections(self, html_filename):
        soup = BeautifulSoup(open(html_filename), "html.parser")
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        return sections[0].get("subsections")

    def test_get_html_with_no_callout_boxes(self):
        subsections = self.get_subsections(
            "nofos/fixtures/html/callouts/callout-1.html"
        )

        self.assertEqual(len(subsections), 5)
        subsections_assertions = [
            {
                "name": "Basic information",
                "callout_box": False,
            },
            {
                "name": "Summary",
                "callout_box": False,
            },
            {
                "name": "Purpose",
                "callout_box": False,
            },
            {
                "name": "Summary 2",
                "callout_box": False,
            },
            {
                "name": "Purpose 2",
                "callout_box": False,
            },
        ]

        self.assertSubsectionsMatch(subsections, subsections_assertions)

    def test_get_html_with_1_callout_box(self):
        subsections = self.get_subsections(
            "nofos/fixtures/html/callouts/callout-2.html"
        )

        self.assertEqual(len(subsections), 4)
        subsections_assertions = [
            {
                "name": "Basic information",
                "callout_box": False,
            },
            {
                "name": "Summary",
                "callout_box": False,
            },
            {
                "name": "Callout box title",
                "callout_box": True,
            },
            {
                "name": "Purpose",
                "callout_box": False,
            },
        ]

        self.assertSubsectionsMatch(subsections, subsections_assertions)

    def test_get_html_with_1_untitled_callout_box(self):
        subsections = self.get_subsections(
            "nofos/fixtures/html/callouts/callout-2b.html"
        )

        self.assertEqual(len(subsections), 4)
        subsections_assertions = [
            {
                "name": "Basic information",
                "callout_box": False,
            },
            {
                "name": "Summary",
                "callout_box": False,
            },
            {
                "name": "",
                "callout_box": True,
            },
            {
                "name": "Purpose",
                "callout_box": False,
            },
        ]

        self.assertSubsectionsMatch(subsections, subsections_assertions)

    def test_get_html_with_1_callout_box_followed_by_empty_section(self):
        subsections = self.get_subsections(
            "nofos/fixtures/html/callouts/callout-3.html"
        )

        self.assertEqual(len(subsections), 5)
        subsections_assertions = [
            {
                "name": "Basic information",
                "callout_box": False,
            },
            {
                "name": "Summary",
                "callout_box": False,
            },
            {
                "name": "Callout box title",
                "callout_box": True,
            },
            {
                "name": "",
                "callout_box": False,
            },
            {
                "name": "Purpose",
                "callout_box": False,
            },
        ]

        self.assertSubsectionsMatch(subsections, subsections_assertions)

    def test_get_html_with_1_untitled_callout_box_followed_by_empty_section(self):
        subsections = self.get_subsections(
            "nofos/fixtures/html/callouts/callout-3b.html"
        )

        self.assertEqual(len(subsections), 5)
        subsections_assertions = [
            {
                "name": "Basic information",
                "callout_box": False,
            },
            {
                "name": "Summary",
                "callout_box": False,
            },
            {
                "name": "",
                "callout_box": True,
            },
            {
                "name": "",
                "callout_box": False,
            },
            {
                "name": "Purpose",
                "callout_box": False,
            },
        ]

        self.assertSubsectionsMatch(subsections, subsections_assertions)

    def test_get_html_with_2_callout_boxes_followed_by_heading(self):
        subsections = self.get_subsections(
            "nofos/fixtures/html/callouts/callout-4.html"
        )

        self.assertEqual(len(subsections), 5)
        subsections_assertions = [
            {
                "name": "Basic information",
                "callout_box": False,
            },
            {
                "name": "Summary",
                "callout_box": False,
            },
            {
                "name": "Callout box title",
                "callout_box": True,
            },
            {
                "name": "Callout box title 2",
                "callout_box": True,
            },
            {
                "name": "Purpose",
                "callout_box": False,
            },
        ]

        self.assertSubsectionsMatch(subsections, subsections_assertions)

    def test_get_html_with_2_untitled_callout_boxes_followed_by_heading(self):
        subsections = self.get_subsections(
            "nofos/fixtures/html/callouts/callout-4b.html"
        )

        self.assertEqual(len(subsections), 5)
        subsections_assertions = [
            {
                "name": "Basic information",
                "callout_box": False,
            },
            {
                "name": "Summary",
                "callout_box": False,
            },
            {
                "name": "",
                "callout_box": True,
            },
            {
                "name": "",
                "callout_box": True,
            },
            {
                "name": "Purpose",
                "callout_box": False,
            },
        ]

        self.assertSubsectionsMatch(subsections, subsections_assertions)

    def test_get_html_with_2_callout_boxes_followed_by_empty_section_and_heading(self):
        subsections = self.get_subsections(
            "nofos/fixtures/html/callouts/callout-5.html"
        )

        self.assertEqual(len(subsections), 6)
        subsections_assertions = [
            {
                "name": "Basic information",
                "callout_box": False,
            },
            {
                "name": "Summary",
                "callout_box": False,
            },
            {
                "name": "Callout box title",
                "callout_box": True,
            },
            {
                "name": "Callout box title 2",
                "callout_box": True,
            },
            {
                "name": "",
                "callout_box": False,
            },
            {
                "name": "Purpose",
                "callout_box": False,
            },
        ]

        self.assertSubsectionsMatch(subsections, subsections_assertions)

    def test_get_html_with_2_untitled_callout_boxes_followed_by_empty_section_and_heading(
        self,
    ):
        subsections = self.get_subsections(
            "nofos/fixtures/html/callouts/callout-5b.html"
        )

        self.assertEqual(len(subsections), 6)
        subsections_assertions = [
            {
                "name": "Basic information",
                "callout_box": False,
            },
            {
                "name": "Summary",
                "callout_box": False,
            },
            {
                "name": "",
                "callout_box": True,
            },
            {
                "name": "",
                "callout_box": True,
            },
            {
                "name": "",
                "callout_box": False,
            },
            {
                "name": "Purpose",
                "callout_box": False,
            },
        ]

        self.assertSubsectionsMatch(subsections, subsections_assertions)

    def test_get_html_with_callout_box_followed_by_empty_section_followed_by_empty_section_twice(
        self,
    ):
        subsections = self.get_subsections(
            "nofos/fixtures/html/callouts/callout-6.html"
        )

        self.assertEqual(len(subsections), 7)
        subsections_assertions = [
            {
                "name": "Basic information",
                "callout_box": False,
            },
            {
                "name": "Summary",
                "callout_box": False,
            },
            {
                "name": "Callout box title",
                "callout_box": True,
            },
            {
                "name": "",
                "callout_box": False,
            },
            {
                "name": "Callout box title 2",
                "callout_box": True,
            },
            {
                "name": "",
                "callout_box": False,
            },
            {
                "name": "Purpose",
                "callout_box": False,
            },
        ]

        self.assertSubsectionsMatch(subsections, subsections_assertions)

    def test_get_html_with_untitled_callout_box_followed_by_empty_section_followed_by_empty_section_twice(
        self,
    ):
        subsections = self.get_subsections(
            "nofos/fixtures/html/callouts/callout-6b.html"
        )

        self.assertEqual(len(subsections), 7)
        subsections_assertions = [
            {
                "name": "Basic information",
                "callout_box": False,
            },
            {
                "name": "Summary",
                "callout_box": False,
            },
            {
                "name": "",
                "callout_box": True,
            },
            {
                "name": "",
                "callout_box": False,
            },
            {
                "name": "",
                "callout_box": True,
            },
            {
                "name": "",
                "callout_box": False,
            },
            {
                "name": "Purpose",
                "callout_box": False,
            },
        ]

        self.assertSubsectionsMatch(subsections, subsections_assertions)
