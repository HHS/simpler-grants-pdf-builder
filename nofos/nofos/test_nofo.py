import logging
from unittest.mock import MagicMock, patch

import requests
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from freezegun import freeze_time

from .models import Nofo, Section, Subsection
from .nofo import (
    DEFAULT_NOFO_OPPORTUNITY_NUMBER,
    PUBLIC_INFORMATION_SUBSECTION,
    REQUEST_HEADERS,
)
from .nofo import _get_all_id_attrs_for_nofo as get_all_id_attrs_for_nofo
from .nofo import (
    _get_classnames_for_font_weight_bold as get_classnames_for_font_weight_bold,
)
from .nofo import _get_font_size_from_cssText as get_font_size_from_cssText
from .nofo import _update_link_statuses as update_link_statuses
from .nofo import (
    add_em_to_de_minimis,
    add_endnotes_header_if_exists,
    add_final_subsection_to_step_3,
    add_headings_to_document,
    add_instructions_to_subsections,
    add_page_breaks_to_headings,
    add_strongs_to_soup,
    clean_heading_tags,
    clean_table_cells,
    combine_consecutive_links,
    convert_table_first_row_to_header_row,
    convert_table_with_all_ths_to_a_regular_table,
    create_nofo,
    decompose_empty_tags,
    decompose_instructions_tables,
    find_broken_links,
    find_external_links,
    find_incorrectly_nested_heading_levels,
    find_matches_with_context,
    find_same_or_higher_heading_levels_consecutive,
    find_subsections_with_nofo_field_value,
    get_cover_image,
    get_nofo_action_links,
    get_sections_from_soup,
    get_side_nav_links,
    get_step_2_section,
    get_subsections_from_sections,
    is_callout_box_table,
    join_nested_lists,
    modifications_update_announcement_text,
    normalize_whitespace_img_alt_text,
    overwrite_nofo,
    preserve_bookmark_links,
    preserve_bookmark_targets,
    preserve_heading_links,
    preserve_table_heading_links,
    remove_cover_image_from_s3,
    remove_google_tracking_info_from_links,
    replace_chars,
    replace_src_for_inline_images,
    replace_value_in_subsections,
    suggest_all_nofo_fields,
    suggest_nofo_agency,
    suggest_nofo_application_deadline,
    suggest_nofo_author,
    suggest_nofo_cover,
    suggest_nofo_keywords,
    suggest_nofo_opdiv,
    suggest_nofo_opportunity_number,
    suggest_nofo_subagency,
    suggest_nofo_subagency2,
    suggest_nofo_subject,
    suggest_nofo_tagline,
    suggest_nofo_theme,
    suggest_nofo_title,
    unwrap_empty_elements,
    unwrap_nested_lists,
    upload_cover_image_to_s3,
)
from .nofo_markdown import md

#########################################################
################### FUNCTION TESTS ######################
#########################################################


class ReplaceCharsTests(TestCase):
    def test_replace_nonbreaking_space(self):
        """Test replacing nonbreaking spaces with normal spaces."""
        self.assertEqual(
            replace_chars("<h1>Hello\xa0World</h1>"), "<h1>Hello World</h1>"
        )
        self.assertEqual(
            replace_chars("<h1>Hello&nbsp;World</h1>"), "<h1>Hello World</h1>"
        )

    def test_replace_ballot_box_with_white_square(self):
        """Test replacing U+2610 (ballot box) with U+25FB (white medium square)."""
        self.assertEqual(
            replace_chars("<td><p>☐ Work plan</p></td>"), "<td><p>◻ Work plan</p></td>"
        )

    def test_replace_diaeresis_with_white_square(self):
        """Test replacing U+00A8 (diaeresis) with U+25FB (white medium square)."""
        self.assertEqual(
            replace_chars("<td><p>¨ Work plan</p></td>"), "<td><p>◻ Work plan</p></td>"
        )

    def test_replace_delete_character_with_white_square(self):
        """Test replacing U+007F (delete) with U+25FB (white medium square)."""
        self.assertEqual(
            replace_chars("<td><p> Work plan</p></td>"), "<td><p>◻ Work plan</p></td>"
        )

    def test_multiple_replacements(self):
        """Test multiple replacements in a single string."""
        test_string = "<tr><th scope='row'>Table\xa0row</th><td><p>☐ Work plan 1</p></td><td><p>¨ Work plan 2</p></td><td><p> Work plan 3</p></td></tr>"
        expected_string = "<tr><th scope='row'>Table row</th><td><p>◻ Work plan 1</p></td><td><p>◻ Work plan 2</p></td><td><p>◻ Work plan 3</p></td></tr>"
        self.assertEqual(replace_chars(test_string), expected_string)

    def test_no_replacements_needed(self):
        """Test a string that requires no replacements."""
        test_string = (
            "<tr><th scope='row'>Table row</th><td><p>◻ Work plan 1</p></td></tr>"
        )
        self.assertEqual(replace_chars(test_string), test_string)


class TestsCleanTableCells(TestCase):
    def test_remove_span_keep_content(self):
        html = "<table><tr><td><span>Content</span> and more <span>content</span></td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        clean_table_cells(soup)
        self.assertEqual(str(soup.td), "<td>Content and more content</td>")

    def test_table_with_one_cell(self):
        html = "<table><tr><td>Only one cell</td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        clean_table_cells(soup)
        self.assertIn("Only one cell", soup.td.text)

    def test_table_with_span(self):
        html = "<table><tr><td><span>Some</span> content and<span> more content</span></td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        clean_table_cells(soup)
        self.assertEqual(soup.td.text, "Some content and more content")

    def test_table_with_span_and_link(self):
        html = "<table><tr><td><span>Some</span> content and<span> <a href='https://groundhog-day.com'>a link</a></span></td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        clean_table_cells(soup)
        self.assertEqual(
            str(soup.td),
            '<td>Some content and <a href="https://groundhog-day.com">a link</a></td>',
        )

    def test_table_with_span_and_a_list(self):
        html = "<table><tr><td><span>Some</span> content and<span> <ul><li>a list item 1</li><li>a list item 2</li></ul></span></td></tr></table>"
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


class TableConvertFirstRowToHeaderRowTests(TestCase):
    def setUp(self):
        self.caption_text = "Physician Assistant Training Chart"
        self.html_filename = "nofos/fixtures/html/table.html"
        with open(self.html_filename, "r", encoding="UTF-8") as file:
            self.soup = BeautifulSoup(file, "html.parser")

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


class ConvertTableTest(TestCase):
    def test_no_thead(self):
        html_content = """
        <table>
            <tr><th>Header 1</th><th>Header 2</th></tr>
            <tr><th>Data 1</th><th>Data 2</th></tr>
        </table>
        """
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table")
        convert_table_with_all_ths_to_a_regular_table(table)
        result = str(soup)
        self.assertIn("<th>Header 1</th>", result)
        self.assertIn("<th>Header 2</th>", result)
        self.assertIn("<th>Data 1</th>", result)
        self.assertIn("<th>Data 2</th>", result)

    def test_thead_with_one_row(self):
        html_content = """
        <table>
            <thead>
                <tr><th>Header 1</th><th>Header 2</th></tr>
            </thead>
        </table>
        """
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table")
        convert_table_with_all_ths_to_a_regular_table(table)
        result = str(soup)
        self.assertNotIn("<tbody>", result)
        self.assertIn("<th>Header 1</th>", result)
        self.assertIn("<th>Header 2</th>", result)

    def test_thead_with_multiple_rows(self):
        html_content = """
        <table>
            <thead>
                <tr><th>Header 1</th><th>Header 2</th></tr>
                <tr><th>Data 1</th><th>Data 2</th></tr>
            </thead>
        </table>
        """
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table")
        convert_table_with_all_ths_to_a_regular_table(table)
        result = str(soup)
        self.assertIn("<tbody>", result)
        self.assertIn("<td>Data 1</td>", result)
        self.assertNotIn("<th>Data 1</th>", result)
        self.assertIn("<th>Header 1</th>", result)
        self.assertNotIn("<td>Header 1</td>", result)

    def test_thead_with_multiple_rows_and_existing_tbody(self):
        html_content = """
        <table>
            <thead>
                <tr><th>Header 1</th><th>Header 2</th></tr>
                <tr><th>Data 1</th><th>Data 2</th></tr>
            </thead>
            <tbody>
                <tr><td>More Data 1</td><td>More Data 2</td></tr>
            </tbody>
        </table>
        """
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table")
        convert_table_with_all_ths_to_a_regular_table(table)
        result = str(soup)
        self.assertEqual(result.count("<tbody>"), 1)
        self.assertEqual(len(soup.select("thead > tr")), 2)
        self.assertIn("<td>More Data 1</td>", result)
        self.assertIn("<th>Data 1</th>", result)

    def test_thead_with_empty_tbody(self):
        html_content = """
        <table>
            <thead>
                <tr><th>Header 1</th><th>Header 2</th></tr>
                <tr><th>Data 1</th><th>Data 2</th></tr>
            </thead>
            <tbody></tbody>
        </table>
        """
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table")
        convert_table_with_all_ths_to_a_regular_table(table)
        result = str(soup)
        self.assertEqual(result.count("<tbody>"), 1)
        self.assertEqual(len(soup.select("thead > tr")), 2)
        self.assertIn("<th>Data 1</th>", result)
        self.assertNotIn("<td>Data 1</td>", result)

    def test_th_with_rowspan_2(self):
        html_content = """
        <table>
            <thead>
                <tr><th>Header 1</th><th rowspan="2">Header 2</th><th>Header 3</th></tr>
                <tr><th>Header 1</th><th>Data 3</th></tr>
            </thead>
        </table>
        """
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table")
        convert_table_with_all_ths_to_a_regular_table(table)
        result = str(soup)
        self.assertEqual(result.count("<tbody>"), 0)
        rows = soup.select("thead > tr")
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[0].find_all("th")), 3)
        self.assertEqual(len(rows[1].find_all("th")), 2)

    def test_table_with_complex_html_in_ths(self):
        html_content = """<table><thead><tr><th><p>Navigator activity</p></th><th><p>Description of project goal</p></th><th><p>Target number</p></th></tr><tr><th><p>Training and certification</p></th><th><p><a id="_heading=h.1v1yuxt"></a>Navigator staff to be federally trained and certified or re-certified for PY 2025 by October 1, 2024, broken out as follows:</p><ul><li>Total number of federally trained and certified or re-certified Navigators.</li><li>Portion of Navigators that will be paid full-time (100%) from Navigator funding.</li><li>Portion of Navigators that will be paid part-time from Navigator funding, including what percentage of their time will be paid from Navigator funding.</li><li>Portion of Navigators that will be volunteers or otherwise not paid from Navigator funding.</li></ul></th><th><p>Sample response:</p><ul><li>15 Navigators</li><li>8 Navigators</li><li>3 Navigators (2 at 50% and 1 at 25%)</li><li>4 Navigators</li></ul></th></tr><tr><th><p>Education, enrollment, and post-enrollment assistance</p></th><th><p>Number of 1:1 interactions between Navigators and consumers (including both general and specific inquiries). </p></th><th></th></tr><tr><th><p>Enrollment assistance</p></th><th><p>Number of consumers assisted with enrollment or re-enrollment in a QHP.</p></th><th></th></tr><tr><th><p>Enrollment assistance</p></th><th><p>Number of consumers assisted with Medicaid/CHIP applications or referrals.</p></th><th></th></tr><tr><th><p>Health literacy and education </p></th><th><p>Number of consumers assisted with understanding the basic concepts and rights related to <a href="https://www.cms.gov/marketplace/technical-assistance-resources/coverage-to-care-presentation.pdf">health coverage and how to use it.</a></p></th><th></th></tr><tr><th><p>Post-enrollment assistance: Resolving enrollment issues and referrals</p></th><th><p>Number of consumers assisted with complex cases, other Exchange (Marketplace) enrollment issues, or referrals.</p></th><th></th></tr><tr><th><p>Post-enrollment assistance: Tax forms and appeals</p></th><th><p>Number of consumers assisted with Marketplace forms, exemptions, and appeals. </p></th><th></th></tr></thead></table>"""
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table")
        convert_table_with_all_ths_to_a_regular_table(table)
        result = """<table><thead><tr><th><p>Navigator activity</p></th><th><p>Description of project goal</p></th><th><p>Target number</p></th></tr></thead><tbody><tr><td><p>Training and certification</p></td><td><p><a id="_heading=h.1v1yuxt"></a>Navigator staff to be federally trained and certified or re-certified for PY 2025 by October 1, 2024, broken out as follows:</p><ul><li>Total number of federally trained and certified or re-certified Navigators.</li><li>Portion of Navigators that will be paid full-time (100%) from Navigator funding.</li><li>Portion of Navigators that will be paid part-time from Navigator funding, including what percentage of their time will be paid from Navigator funding.</li><li>Portion of Navigators that will be volunteers or otherwise not paid from Navigator funding.</li></ul></td><td><p>Sample response:</p><ul><li>15 Navigators</li><li>8 Navigators</li><li>3 Navigators (2 at 50% and 1 at 25%)</li><li>4 Navigators</li></ul></td></tr><tr><td><p>Education, enrollment, and post-enrollment assistance</p></td><td><p>Number of 1:1 interactions between Navigators and consumers (including both general and specific inquiries). </p></td><td></td></tr><tr><td><p>Enrollment assistance</p></td><td><p>Number of consumers assisted with enrollment or re-enrollment in a QHP.</p></td><td></td></tr><tr><td><p>Enrollment assistance</p></td><td><p>Number of consumers assisted with Medicaid/CHIP applications or referrals.</p></td><td></td></tr><tr><td><p>Health literacy and education </p></td><td><p>Number of consumers assisted with understanding the basic concepts and rights related to <a href="https://www.cms.gov/marketplace/technical-assistance-resources/coverage-to-care-presentation.pdf">health coverage and how to use it.</a></p></td><td></td></tr><tr><td><p>Post-enrollment assistance: Resolving enrollment issues and referrals</p></td><td><p>Number of consumers assisted with complex cases, other Exchange (Marketplace) enrollment issues, or referrals.</p></td><td></td></tr><tr><td><p>Post-enrollment assistance: Tax forms and appeals</p></td><td><p>Number of consumers assisted with Marketplace forms, exemptions, and appeals. </p></td><td></td></tr></tbody></table>"""
        self.assertEqual(str(table), result)


class HTMLSectionTestsH1(TestCase):
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
            "Modifications",
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


class HTMLSectionTestsH2(TestCase):
    def test_get_sections_from_soup_h2(self):
        soup = BeautifulSoup("<h2>Section 1</h2><p>Section 1 body</p>", "html.parser")
        sections = get_sections_from_soup(soup, top_heading_level="h2")
        self.assertEqual(len(sections), 1)

        section = sections[0]
        self.assertEqual(section.get("name"), "Section 1")
        self.assertEqual(section.get("html_id"), "")
        self.assertEqual(section.get("order"), 1)
        self.assertEqual(str(section.get("body")[0]), "<p>Section 1 body</p>")
        self.assertEqual(section.get("has_section_page"), True)

    def test_get_sections_from_soup_h2_with_h1(self):
        # not throwing an error, just documenting behaviour
        soup = BeautifulSoup("<h1>Section 1</h1><p>Section 1 body</p>", "html.parser")
        sections = get_sections_from_soup(soup, top_heading_level="h2")
        self.assertEqual(len(sections), 0)

    def test_get_sections_from_soup_h2_length_zero(self):
        soup = BeautifulSoup("<p>Section 1 body</p>", "html.parser")
        sections = get_sections_from_soup(soup, top_heading_level="h2")
        self.assertEqual(sections, [])

    def test_get_sections_from_soup_h2_length_two(self):
        soup = BeautifulSoup("<h2>Section 1</h2><h2>Section 2</h2>", "html.parser")
        sections = get_sections_from_soup(soup, top_heading_level="h2")
        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0].get("order"), 1)
        self.assertEqual(sections[1].get("order"), 2)

    def test_get_sections_from_soup_h2_with_html_id(self):
        soup = BeautifulSoup(
            '<h2 id="section-1">Section 1</h2><p>Section 1 body</p>', "html.parser"
        )
        sections = get_sections_from_soup(soup, top_heading_level="h2")
        self.assertEqual(sections[0].get("html_id"), "section-1")

    def test_get_sections_from_soup_no_body(self):
        soup = BeautifulSoup("<h2>Section 1</h2>", "html.parser")
        sections = get_sections_from_soup(soup, top_heading_level="h2")
        self.assertEqual(sections[0].get("body"), [])

    def test_get_sections_from_soup_with_whitespace(self):
        soup = BeautifulSoup(
            '<h2 id="section-1"><span class="c21">Section 1 </span></h2><p>Section 1 body</p>',
            "html.parser",
        )
        sections = get_sections_from_soup(soup, top_heading_level="h2")
        self.assertEqual(sections[0].get("name"), "Section 1")

    def test_get_sections_from_soup_with_no_section_page(self):
        for no_section_page_title in [
            "Appendix",
            "Appendices",
            "Glossary",
            "Endnotes",
            "References",
            "Modifications",
        ]:
            soup = BeautifulSoup(
                '<h2 id="section-1">{}</span></h2><p>Section 1 body</p>'.format(
                    no_section_page_title
                ),
                "html.parser",
            )
            sections = get_sections_from_soup(soup, top_heading_level="h2")
            self.assertEqual(sections[0].get("name"), no_section_page_title)
            self.assertEqual(sections[0].get("has_section_page"), False)


class CalloutBoxTableTests(TestCase):
    def test_single_th(self):
        html = "<table><tr><th>Header</th></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        self.assertTrue(is_callout_box_table(table))

    def test_single_td(self):
        html = "<table><tr><td>Data</td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        self.assertTrue(is_callout_box_table(table))

    def test_multiple_ths(self):
        html = "<table><tr><th>Header 1</th><th>Header 2</th></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        self.assertFalse(is_callout_box_table(table))

    def test_multiple_tds(self):
        html = "<table><tr><td>Data 1</td><td>Data 2</td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        self.assertFalse(is_callout_box_table(table))

    def test_mixed_th_td(self):
        html = "<table><tr><th>Header</th><td>Data</td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        self.assertFalse(is_callout_box_table(table))

    def test_multiple_rows(self):
        html = "<table><tr><th>Header</th></tr><tr><td>Data</td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        self.assertFalse(is_callout_box_table(table))

    def test_empty_table(self):
        html = "<table></table>"
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        self.assertFalse(is_callout_box_table(table))


class HTMLSubsectionTestsH1(TestCase):
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

    def test_get_subsections_from_soup_create_subsection_if_no_headingg(self):
        soup = BeautifulSoup(
            "<h1>Section 1</h1><p>Subsection 1 body</p><h2>Subsection 2</h2><p>Subsection 2 body</p>",
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        subsections = sections[0].get("subsections")
        self.assertEqual(len(subsections), 2)
        # subsection 1
        self.assertEqual(subsections[0].get("name"), "")
        self.assertEqual(
            str(subsections[0].get("body")),
            "[<p>Subsection 1 body</p>]",
        )

        # subsection 2
        self.assertEqual(subsections[1].get("name"), "Subsection 2")
        self.assertEqual(
            str(subsections[1].get("body")),
            "[<p>Subsection 2 body</p>]",
        )

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

    def test_get_subsections_from_soup_section_heading_true_h6(self):
        # starts with h2, so the h6 does not get demoted
        soup = BeautifulSoup(
            '<h2>Section 1</h2><h6 id="subsection-1">Subsection 1</h6><p>Section 1 body</p>',
            "html.parser",
        )
        sections = get_subsections_from_sections(
            get_sections_from_soup(soup, top_heading_level="h2"), top_heading_level="h2"
        )
        subsection = sections[0].get("subsections")[0]
        self.assertEqual(subsection.get("tag"), "h6")

    def test_get_subsections_from_soup_section_heading_h7(self):
        # starts with h2, so the h7 does not get demoted
        soup = BeautifulSoup(
            '<h2>Section 1</h2><div aria-level="7" role="heading">Subsection 1</div><p>Section 1 body</p>',
            "html.parser",
        )
        sections = get_subsections_from_sections(
            get_sections_from_soup(soup, top_heading_level="h2"), top_heading_level="h2"
        )
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


class HTMLSubsectionTestsH2(TestCase):
    def test_get_subsections_from_soup_h2(self):
        soup = BeautifulSoup(
            "<h2>Section 1</h2><h3>Subsection 1</h3><p>Section 1 body</p>",
            "html.parser",
        )
        sections = get_subsections_from_sections(
            get_sections_from_soup(soup, top_heading_level="h2"), top_heading_level="h2"
        )
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

    def test_get_subsections_from_soup_h2_with_h1(self):
        soup = BeautifulSoup(
            "<h1>Section 1</h1><h2>Subsection 1</h2><p>Section 1 body</p>",
            "html.parser",
        )
        sections = get_subsections_from_sections(
            get_sections_from_soup(soup, top_heading_level="h2"), top_heading_level="h2"
        )

        # 1 section
        self.assertEqual(len(sections), 1)

        # assert section values: h1 is ignored and h2 is used
        section = sections[0]
        self.assertEqual(section.get("name"), "Subsection 1")
        self.assertEqual(section.get("html_id"), "")
        self.assertEqual(section.get("order"), 1)

        # 1 subsection but no heading
        self.assertEqual(len(section.get("subsections")), 1)
        subsection = section.get("subsections")[0]
        self.assertEqual(subsection.get("name"), "")
        self.assertEqual(subsection.get("tag"), "")
        self.assertEqual(subsection.get("html_id"), "")
        self.assertEqual(subsection.get("order"), 1)
        self.assertEqual(str(subsection.get("body")[0]), "<p>Section 1 body</p>")

    def test_get_subsections_from_soup_h2_section_heading_not_demoted(self):
        soup = BeautifulSoup(
            '<h2>Section 1</h2><h3 id="subsection--h3">Subsection h3</h3><h4 id="subsection--h4">Subsection h4</h4><h5 id="subsection--h5">Subsection h5</h5><h6 id="subsection--h6">Subsection h6</h6><p>Section 1 body</p>',
            "html.parser",
        )
        sections = get_subsections_from_sections(
            get_sections_from_soup(soup, top_heading_level="h2"), top_heading_level="h2"
        )
        self.assertEqual(len(sections), 1)

        section = sections[0]
        self.assertEqual(section.get("subsections")[0].get("name"), "Subsection h3")
        self.assertEqual(section.get("subsections")[0].get("html_id"), "subsection--h3")

        self.assertEqual(section.get("subsections")[1].get("name"), "Subsection h4")
        self.assertEqual(section.get("subsections")[1].get("html_id"), "subsection--h4")

        self.assertEqual(section.get("subsections")[2].get("name"), "Subsection h5")
        self.assertEqual(section.get("subsections")[2].get("html_id"), "subsection--h5")

        self.assertEqual(section.get("subsections")[3].get("name"), "Subsection h6")
        self.assertEqual(section.get("subsections")[3].get("html_id"), "subsection--h6")

    def test_get_subsections_from_soup_h1_section_headings_demoted(self):
        soup = BeautifulSoup(
            '<h1>Section h1</h1><h2>Subsection h2</h2><h3>Subsection h3</h3><h4>Subsection h4</h4><h5>Subsection h5</h5><h6>Subsection h6</h6>><div role="heading" aria-level="7">Subsection h7</div><p>Section 1 body</p>',
            "html.parser",
        )
        sections = get_subsections_from_sections(
            get_sections_from_soup(soup, top_heading_level="h1"), top_heading_level="h1"
        )
        self.assertEqual(len(sections), 1)

        section = sections[0]
        self.assertEqual(section.get("name"), "Section h1")

        self.assertEqual(len(section.get("subsections")), 6)

        self.assertEqual(section.get("subsections")[0].get("name"), "Subsection h2")
        self.assertEqual(section.get("subsections")[0].get("tag"), "h3")

        self.assertEqual(section.get("subsections")[1].get("name"), "Subsection h3")
        self.assertEqual(section.get("subsections")[1].get("tag"), "h4")

        self.assertEqual(section.get("subsections")[2].get("name"), "Subsection h4")
        self.assertEqual(section.get("subsections")[2].get("tag"), "h5")

        self.assertEqual(section.get("subsections")[3].get("name"), "Subsection h5")
        self.assertEqual(section.get("subsections")[3].get("tag"), "h6")

        self.assertEqual(section.get("subsections")[4].get("name"), "Subsection h6")
        self.assertEqual(section.get("subsections")[4].get("tag"), "h7")

        self.assertEqual(section.get("subsections")[5].get("name"), "Subsection h7")
        self.assertEqual(section.get("subsections")[5].get("tag"), "h7")


class HTMLNofoFileTests(TestCase):
    def setUp(self):
        self.html_filename = "nofos/fixtures/html/nofo.html"
        with open(self.html_filename, "r", encoding="UTF-8") as file:
            self.soup = BeautifulSoup(file, "html.parser")

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
            "opdiv": "Test OpDiv",
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
        nofo = create_nofo("Test Nofo", self.sections, opdiv="Test OpDiv")
        self.assertEqual(nofo.title, "Test Nofo")
        self.assertEqual(nofo.number, "NOFO #999")
        self.assertEqual(nofo.theme, "portrait-hrsa-blue")
        self.assertEqual(len(nofo.sections.all()), 1)
        self.assertEqual(nofo.sections.first().html_class, "")
        self.assertEqual(len(nofo.sections.first().subsections.all()), 2)

    def test_create_nofo_success_duplicate_nofos(self):
        """
        Test creating two duplicate nofo objects successfully
        """
        nofo = create_nofo("Test Nofo", self.sections, opdiv="Test OpDiv")
        nofo2 = create_nofo("Test Nofo", self.sections, opdiv="Test OpDiv")
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
        nofo = create_nofo("Test Nofo", [], opdiv="Test OpDiv")
        self.assertEqual(nofo.title, "Test Nofo")
        self.assertEqual(len(nofo.sections.all()), 0)

    def test_create_nofo_success_no_title(self):
        """
        Test with empty nofo title and empty sections
        """
        nofo = create_nofo("", [], opdiv="Test OpDiv")
        self.assertEqual(nofo.title, "")
        self.assertEqual(len(nofo.sections.all()), 0)

    def test_create_nofo_subsection_body_is_markdown(self):
        """
        Test creating a nofo object with markdown strings (not HTML) as body
        """
        sections = self.sections

        subsection_1_body = [
            "<p>Subsection 1 body with <strong>strong tag</strong></p>"
        ]
        subsection_2_body = [
            "<p>Subsection 2 body with list</p>",
            "<ul><li>Item 1</li><li>Item 2</li></ul>",
        ]

        sections[0]["subsections"][0]["body"] = md(
            "".join(subsection_1_body), escape_misc=False
        )
        sections[0]["subsections"][1]["body"] = md(
            "".join(subsection_2_body), escape_misc=False
        )

        nofo = create_nofo("Test Nofo", self.sections, opdiv="Test OpDiv")
        self.assertEqual(nofo.title, "Test Nofo")
        self.assertEqual(len(nofo.sections.all()), 1)
        self.assertEqual(len(nofo.sections.first().subsections.all()), 2)

        self.assertEqual(
            nofo.sections.first().subsections.all()[0].body,
            "Subsection 1 body with **strong tag**",
        )
        self.assertEqual(
            nofo.sections.first().subsections.all()[1].body,
            "Subsection 2 body with list\n\n* Item 1\n* Item 2",
        )


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
        nofo = create_nofo("Test Nofo", self.sections, opdiv="Test OpDiv")
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
        Test overwriting with a nofo with empty sections is allowed
        """
        nofo = create_nofo("Test Nofo", self.sections, opdiv="Test OpDiv")
        self.assertEqual(nofo.title, "Test Nofo")
        self.assertEqual(nofo.number, "NOFO #999")
        self.assertEqual(nofo.sections.first().name, "Section 1")

        nofo = overwrite_nofo(nofo, [])
        self.assertEqual(len(nofo.sections.all()), 0)  # no sections


class AddFinalSubsectionTests(TestCase):
    def _get_sections_1_2_3(self, section_3_name="Step 3: Prepare Your Application"):
        return [
            {
                "name": "Step 1: Review the Opportunity",
                "order": 1,
                "html_id": "",
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "Subsection 1.1",
                        "order": 1,
                        "tag": "h3",
                        "html_id": "",
                        "body": ["<p>Section 1, subsection 1 body.</p>"],
                    }
                ],
            },
            {
                "name": "Step 2: Get Ready to Apply",
                "order": 2,
                "html_id": "",
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "Subsection 2.1",
                        "order": 1,
                        "tag": "h3",
                        "html_id": "",
                        "body": ["<p>Section 2, subsection 1 body.</p>"],
                    }
                ],
            },
            {
                "name": section_3_name,
                "order": 3,
                "html_id": "",
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "Subsection 3.1",
                        "order": 1,
                        "tag": "h3",
                        "html_id": "",
                        "body": ["<p>Section 3, subsection 1 body.</p>"],
                    }
                ],
            },
        ]

    def test_add_section_to_step_3(self):
        sections = self._get_sections_1_2_3()
        add_final_subsection_to_step_3(sections)

        self.assertEqual(len(sections[0].get("subsections")), 1)
        self.assertEqual(len(sections[1].get("subsections")), 1)
        self.assertEqual(len(sections[2].get("subsections")), 2)

        # get final subsection in final section
        final_subsection = sections[-1].get("subsections", [])[-1]
        self.assertEqual(
            final_subsection.get("name"), PUBLIC_INFORMATION_SUBSECTION.get("name")
        )
        self.assertEqual(
            final_subsection.get("body"), PUBLIC_INFORMATION_SUBSECTION.get("body")
        )
        self.assertEqual(final_subsection.get("tag"), "h5")
        self.assertEqual(
            final_subsection.get("order"), len(sections[2].get("subsections"))
        )  # order is same as length, as it is the last subsection

    def test_add_section_to_step_3_write_your_application(self):
        sections = self._get_sections_1_2_3(
            section_3_name="step 3: write your application"
        )
        add_final_subsection_to_step_3(sections)

        self.assertEqual(len(sections[0].get("subsections")), 1)
        self.assertEqual(len(sections[1].get("subsections")), 1)
        self.assertEqual(len(sections[2].get("subsections")), 2)

        # get final subsection in final section
        final_subsection = sections[-1].get("subsections", [])[-1]
        self.assertEqual(
            final_subsection.get("name"), PUBLIC_INFORMATION_SUBSECTION.get("name")
        )
        self.assertEqual(
            final_subsection.get("body"), PUBLIC_INFORMATION_SUBSECTION.get("body")
        )
        self.assertEqual(final_subsection.get("tag"), "h5")
        self.assertEqual(
            final_subsection.get("order"), len(sections[2].get("subsections"))
        )  # order is same as length, as it is the last subsection

    def test_NO_add_section_to_step_3(self):
        sections = self._get_sections_1_2_3(
            section_3_name="Step 3: Learn about Review and Award"
        )
        add_final_subsection_to_step_3(sections)

        self.assertEqual(len(sections[0].get("subsections")), 1)
        self.assertEqual(len(sections[1].get("subsections")), 1)
        self.assertEqual(len(sections[2].get("subsections")), 1)

        # get final subsection in final section
        final_subsection = sections[-1].get("subsections", [])[-1]
        self.assertEqual(final_subsection.get("name"), "Subsection 3.1")

    def test_NO_add_duplicate_public_information_section(self):
        """
        Test that the public information subsection is not added if it already exists in Step 3.
        """
        sections = self._get_sections_1_2_3()

        # Manually add the public information subsection to Step 3
        sections[2]["subsections"].append(
            {
                "name": PUBLIC_INFORMATION_SUBSECTION["name"],
                "order": 2,
                "tag": "h5",
                "html_id": "",
                "body": PUBLIC_INFORMATION_SUBSECTION["body"],
                "is_callout_box": True,
            }
        )

        # Initial state should have 2 subsections in Step 3
        self.assertEqual(len(sections[2].get("subsections")), 2)

        # Try to add the public information section again
        add_final_subsection_to_step_3(sections)

        # Verify no additional subsection was added
        self.assertEqual(len(sections[0].get("subsections")), 1)  # Step 1 unchanged
        self.assertEqual(len(sections[1].get("subsections")), 1)  # Step 2 unchanged
        self.assertEqual(len(sections[2].get("subsections")), 2)  # Step 3 unchanged

        # Verify the last subsection is still the public information subsection
        final_subsection = sections[2].get("subsections", [])[-1]
        self.assertEqual(
            final_subsection.get("name"), PUBLIC_INFORMATION_SUBSECTION["name"]
        )
        self.assertEqual(
            final_subsection.get("body"), PUBLIC_INFORMATION_SUBSECTION["body"]
        )

    def test_add_public_information_section_after_specific_subsection_titles(self):
        """
        Test that the public information subsection is added _after_ different subsection titles.
        """

        for subsection_name in [
            "Other required forms",
            "Standard forms",
            "Application components",
            "OTHER REQUIRED FORMS",
            "StAnDaRd FoRmS",
            "application components",
        ]:
            with self.subTest(subsection_name=subsection_name):
                sections = self._get_sections_1_2_3()

                # Increment order number of initial subsection in Step 3
                sections[2]["subsections"][0]["order"] = 2

                # Manually add the form subsection to Step 3
                sections[2]["subsections"].insert(
                    0,
                    {
                        "name": subsection_name,
                        "order": 1,
                        "tag": "h5",
                        "html_id": "",
                        "body": "Body content",
                        "is_callout_box": False,
                    },
                )

                # Initial state should have 2 subsections in Step 3
                self.assertEqual(len(sections[2].get("subsections")), 2)

                # Add the public information section
                add_final_subsection_to_step_3(sections)

                # Verify extra subsection in step 3
                self.assertEqual(len(sections[2].get("subsections")), 3)

                # first subsection is the title we specified
                self.assertEqual(sections[2]["subsections"][0]["name"], subsection_name)
                # second subsection is public information one
                self.assertEqual(
                    sections[2]["subsections"][1]["name"],
                    PUBLIC_INFORMATION_SUBSECTION["name"],
                )
                self.assertEqual(
                    sections[2]["subsections"][1]["body"],
                    PUBLIC_INFORMATION_SUBSECTION["body"],
                )
                # last subsection is the initial one
                self.assertEqual(
                    sections[2]["subsections"][2]["name"], "Subsection 3.1"
                )

    def test_add_public_information_section_after_LAST_specific_subsection_title(self):
        """
        Test that the public information subsection is added _after_ the last subsection title matched.
        """
        sections = self._get_sections_1_2_3()

        # Increment order number of initial subsection in Step 3
        sections[2]["subsections"][0]["order"] = 4

        # Manually add "Standard forms" to Step 3
        sections[2]["subsections"].insert(
            0,
            {
                "name": "Standard forms",
                "order": 1,
                "tag": "h5",
                "html_id": "",
                "body": "Body content",
                "is_callout_box": False,
            },
        )

        # Manually add "Other required forms" to Step 3
        sections[2]["subsections"].insert(
            1,
            {
                "name": "Other required forms",
                "order": 2,
                "tag": "h5",
                "html_id": "",
                "body": "Body content",
                "is_callout_box": False,
            },
        )
        # Manually add "Application components" to Step 3
        sections[2]["subsections"].insert(
            2,
            {
                "name": "Application components",
                "order": 3,
                "tag": "h5",
                "html_id": "",
                "body": "Body content",
                "is_callout_box": False,
            },
        )

        # Initial state should have 3 subsections in Step 3
        self.assertEqual(len(sections[2].get("subsections")), 4)

        # Try to add the public information section
        add_final_subsection_to_step_3(sections)

        # Verify extra subsection in step 3
        self.assertEqual(len(sections[2].get("subsections")), 5)

        # first subsection is "Standard forms"
        self.assertEqual(sections[2]["subsections"][0]["name"], "Standard forms")

        # second subsection is "Other required forms"
        self.assertEqual(sections[2]["subsections"][1]["name"], "Other required forms")
        # third subsection is "Application components"
        self.assertEqual(
            sections[2]["subsections"][2]["name"], "Application components"
        )
        # fourth subsection is public information one
        self.assertEqual(
            sections[2]["subsections"][3]["name"],
            PUBLIC_INFORMATION_SUBSECTION["name"],
        )
        self.assertEqual(
            sections[2]["subsections"][3]["body"],
            PUBLIC_INFORMATION_SUBSECTION["body"],
        )
        # last subsection is the initial one
        self.assertEqual(sections[2]["subsections"][4]["name"], "Subsection 3.1")


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

        self.sections_with_overlapping_names = [
            {
                "name": "Program description",
                "order": 1,
                "html_id": "",
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "Eligibility",
                        "order": 1,
                        "tag": "h3",
                        "html_id": "_Eligibility",
                        "body": [
                            "<p>You can apply if you are one of the following:</p>"
                        ],
                    },
                    {
                        "name": "Other eligibility criteria",
                        "order": 2,
                        "tag": "h4",
                        "html_id": "_Other__Eligibility",  # the id before is a subset of this one
                        "body": [
                            "<p>Your application will be deemed incomplete and not considered for funding under this notice</p>"
                        ],
                    },
                    {
                        "name": "Program requirements",
                        "order": 3,
                        "tag": "h3",
                        "html_id": "_Program_requirements",
                        "body": [
                            '<p>You must have MOAs with at least 10 PHCs (as described in the <a href="#_Other__Eligibility">Other Eligibility Criteria</a> section) in your network throughout the period of performance.</p>'
                        ],
                    },
                ],
            }
        ]

        self.sections_with_ampersand_links = [
            {
                "name": "Program description",
                "order": 1,
                "html_id": "",
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "Budget & Budget",
                        "order": 1,
                        "tag": "h3",
                        "html_id": "_budget_&_budget",
                        "body": [
                            '<p>Subsection 1 body to <a href="#_budget_&_budget">Budget & Budget</a>.</p>'
                        ],
                    },
                    {
                        "order": 2,
                        "html_id": "",
                        "body": [
                            '<p>Subsection 2 body to <a href="#_budget_&amp;_budget">Budget & Budget</a>.</p>'
                        ],
                    },
                ],
            }
        ]

        self.sections_with_case_insensitive_links = [
            {
                "name": "Program description",
                "order": 1,
                "html_id": "",
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "Contacts and Support",
                        "order": 1,
                        "tag": "h3",
                        "html_id": "_Contacts_and_support",
                        "body": [
                            '<p>Subsection 1 body to <a href="#_Contacts_and_Support">Contacts and Support</a>.</p>'
                        ],
                    },
                    {
                        "order": 2,
                        "html_id": "",
                        "body": [
                            '<p>Subsection 2 body to <a href="#_CONTACTS_AND_SUPPORT">Contacts and Support</a>.</p>'
                        ],
                    },
                ],
            }
        ]

    def test_add_headings_success(self):
        nofo = create_nofo("Test Nofo", self.sections, opdiv="Test OpDiv")
        self.assertEqual(nofo.title, "Test Nofo")

        section = nofo.sections.first()
        subsection_1 = nofo.sections.first().subsections.all()[0]
        subsection_2 = nofo.sections.first().subsections.all()[1]

        # check section heading has default id
        self.assertEqual(section.html_id, "1--section-1")
        # check first subsection heading has no html_id
        self.assertEqual(subsection_1.html_id, "1--section-1--subsection-1")
        # check second subsection heading has html_id
        self.assertEqual(subsection_2.html_id, "subsection-2")

        ################
        # ADD HEADINGS
        ################
        add_headings_to_document(nofo)
        section = nofo.sections.first()
        subsection_1 = nofo.sections.first().subsections.all()[0]
        subsection_2 = nofo.sections.first().subsections.all()[1]

        # check section heading has new html_id
        self.assertEqual(section.html_id, "section-1")
        # check subsection headings have new html_id
        self.assertEqual(subsection_1.html_id, "1--section-1--subsection-1")
        self.assertEqual(subsection_2.html_id, "2--section-1--subsection-2")

    def test_add_headings_success_replace_link(self):
        nofo = create_nofo("Test Nofo 2", self.sections_with_link, opdiv="Test OpDiv")
        self.assertEqual(nofo.title, "Test Nofo 2")

        section = nofo.sections.first()
        subsection_1 = nofo.sections.first().subsections.all()[0]
        subsection_2 = nofo.sections.first().subsections.all()[1]

        # check section 1 heading has default id
        self.assertEqual(section.html_id, "1--section-1")
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
        add_headings_to_document(nofo)
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
            "Test Nofo 2",
            self.sections_with_really_long_subsection_title,
            opdiv="Test OpDiv",
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

    def test_add_headings_with_really_long_title_replace_link(self):
        nofo = create_nofo(
            "Test Nofo 2", self.sections_with_overlapping_names, opdiv="Test OpDiv"
        )
        self.assertEqual(nofo.title, "Test Nofo 2")

        section = nofo.sections.first()
        subsection_3 = nofo.sections.first().subsections.all()[2]
        self.assertIn(
            "[Other Eligibility Criteria](#_Other__Eligibility)", subsection_3.body
        )

        ################
        # ADD HEADINGS
        ################
        add_headings_to_document(nofo)
        section = nofo.sections.first()
        subsection_1 = nofo.sections.first().subsections.all()[0]
        subsection_2 = nofo.sections.first().subsections.all()[1]
        subsection_3 = nofo.sections.first().subsections.all()[2]

        # check section heading has new html_id
        self.assertEqual(section.html_id, "program-description")

        # check new html_ids
        self.assertEqual(subsection_1.html_id, "1--program-description--eligibility")
        self.assertEqual(
            subsection_2.html_id, "2--program-description--other-eligibility-criteria"
        )
        self.assertEqual(
            subsection_3.html_id, "3--program-description--program-requirements"
        )

        # make sure the link in the body is matching the second id, not the first
        self.assertIn(
            "(as described in the [Other Eligibility Criteria](#2--program-description--other-eligibility-criteria)",
            subsection_3.body,
        )

    def test_add_headings_with_ampersand_links(self):
        nofo = create_nofo(
            "Test Nofo 3", self.sections_with_ampersand_links, opdiv="Test OpDiv"
        )
        self.assertEqual(nofo.title, "Test Nofo 3")

        ################
        # ADD HEADINGS
        ################
        add_headings_to_document(nofo)
        section = nofo.sections.first()
        subsection_1 = nofo.sections.first().subsections.all()[0]
        subsection_2 = nofo.sections.first().subsections.all()[1]

        # check section heading has new html_id
        self.assertEqual(section.html_id, "program-description")

        # check new html_ids
        self.assertEqual(subsection_1.html_id, "1--program-description--budget-budget")
        self.assertEqual(
            subsection_1.body,
            "Subsection 1 body to [Budget & Budget](#1--program-description--budget-budget).\n",
        )
        self.assertEqual(
            subsection_2.body,
            "Subsection 2 body to [Budget & Budget](#1--program-description--budget-budget).\n",
        )

    def test_add_headings_with_case_insensitive_links(self):
        nofo = create_nofo(
            "Test Nofo 4", self.sections_with_case_insensitive_links, opdiv="Test OpDiv"
        )
        self.assertEqual(nofo.title, "Test Nofo 4")

        ################
        # ADD HEADINGS
        ################
        add_headings_to_document(nofo)
        section = nofo.sections.first()
        subsection_1 = nofo.sections.first().subsections.all()[0]
        subsection_2 = nofo.sections.first().subsections.all()[1]

        # check section heading has new html_id
        self.assertEqual(section.html_id, "program-description")

        # check new html_ids
        self.assertEqual(
            subsection_1.html_id, "1--program-description--contacts-and-support"
        )
        self.assertEqual(
            subsection_1.body,
            "Subsection 1 body to [Contacts and Support](#1--program-description--contacts-and-support).\n",
        )
        self.assertEqual(
            subsection_2.body,
            "Subsection 2 body to [Contacts and Support](#1--program-description--contacts-and-support).\n",
        )


class AddPageBreaksToHeadingsTests(TestCase):
    def setUp(self):
        self.nofo = Nofo.objects.create(
            title="Test Nofo AddPageBreaksToHeadingsTests", opdiv="Test opdiv"
        )

    def create_section_with_subsections(self, section_name, subsection_names):
        section = Section.objects.create(nofo=self.nofo, name=section_name)
        subsections = []
        for i, name in enumerate(subsection_names, start=1):
            subsections.append(
                Subsection.objects.create(
                    section=section,
                    name=name,
                    tag="h3",
                    body=f"{name} body",
                    order=i,
                )
            )
        return section, subsections

    def test_no_matches(self):
        # Section name doesn't match rules
        _, subsections = self.create_section_with_subsections(
            "Contacts and Support", ["Eligibility", "Program description"]
        )

        add_page_breaks_to_headings(self.nofo)

        for s in subsections:
            s.refresh_from_db()
            self.assertEqual(s.html_class, "")

    def test_matches_with_section_name(self):
        _, subsections = self.create_section_with_subsections(
            "Step 1: Review the Opportunity",
            ["Basic information", "Eligibility", "Program description"],
        )

        add_page_breaks_to_headings(self.nofo)

        for s in subsections:
            s.refresh_from_db()

        self.assertEqual(subsections[0].html_class, "")  # not in rules
        self.assertEqual(subsections[1].html_class, "page-break-before")  # Eligibility
        self.assertEqual(subsections[2].html_class, "page-break-before")  # Program desc

    def test_wrong_section_name_does_not_match(self):
        _, subsections = self.create_section_with_subsections(
            "Step 2: Get Ready to Apply",
            ["Eligibility", "Application checklist"],
        )

        add_page_breaks_to_headings(self.nofo)

        for s in subsections:
            s.refresh_from_db()
            self.assertEqual(s.html_class, "")  # no match without step 1/5 etc.

    def test_multiple_sections_match(self):
        # Same subsection name should match in 1 but not in 3
        _, subs1 = self.create_section_with_subsections(
            "Step 1: Review the Opportunity", ["Eligibility"]
        )
        _, subs2 = self.create_section_with_subsections(
            "Step 3: Prepare Your Application", ["Eligibility"]
        )

        add_page_breaks_to_headings(self.nofo)

        subs1[0].refresh_from_db()
        subs2[0].refresh_from_db()

        self.assertEqual(subs1[0].html_class, "page-break-before")
        self.assertEqual(subs2[0].html_class, "")


@patch("nofos.nofo.get_image_url_from_s3", return_value=None)
class NofoCoverImageTests(TestCase):

    def setUp(self):
        # Silence the 's3' logger by raising log level to error (below error nothing happens)
        self._s3_logger = logging.getLogger("s3")
        self._original_level = self._s3_logger.level
        self._s3_logger.setLevel(logging.ERROR)

    def tearDown(self):
        # Restore original logging level
        self._s3_logger.setLevel(self._original_level)

    def test_image_path_with_static_prefix(self, _mock_get_image_url_from_s3):
        """Test cover image paths that start with '/static/img/'"""
        nofo = Nofo(cover_image="/static/img/cover1.jpg")
        self.assertEqual(get_cover_image(nofo), "img/cover1.jpg")

    def test_image_path_with_img_prefix(self, _mock_get_image_url_from_s3):
        """Test cover image paths that start with '/img/'"""
        nofo = Nofo(cover_image="/img/cover2.jpg")
        self.assertEqual(get_cover_image(nofo), "img/cover2.jpg")

    def test_image_path_filename_only(self, _mock_get_image_url_from_s3):
        """Test cover image paths that are just filenames"""
        nofo = Nofo(cover_image="cover3.jpg")
        self.assertEqual(get_cover_image(nofo), "img/cover-img/cover3.jpg")

    def test_image_path_full_http_url(self, _mock_get_image_url_from_s3):
        """Test cover image paths that are full URLs"""
        nofo = Nofo(
            cover_image="https://raw.githubusercontent.com/pcraig3/ghog-day/refs/heads/main/public/images/ghogs/buckeye-chuck.jpeg"
        )
        self.assertEqual(
            get_cover_image(nofo),
            "https://raw.githubusercontent.com/pcraig3/ghog-day/refs/heads/main/public/images/ghogs/buckeye-chuck.jpeg",
        )

    def test_image_path_default(self, _mock_get_image_url_from_s3):
        """Test default cover image when no image is set"""
        nofo = Nofo(cover_image="")
        self.assertEqual(get_cover_image(nofo), "img/cover.jpg")

    def test_image_path_returns_unmodified_if_none_of_conditions_met(
        self, _mock_get_image_url_from_s3
    ):
        """Test paths that do not meet any specific condition are returned as is"""
        nofo = Nofo(cover_image="/some/other/path/cover5.jpg")
        self.assertEqual(get_cover_image(nofo), "/some/other/path/cover5.jpg")

    def test_image_path_from_s3_returns_s3_url(self, mock_get_image_url_from_s3):
        """Test that S3 URL is returned when available"""
        s3_url = "https://test-bucket.s3.amazonaws.com/cover-image.jpg?signature=xyz"
        mock_get_image_url_from_s3.return_value = s3_url
        nofo = Nofo(cover_image="cover-image.jpg")
        self.assertEqual(get_cover_image(nofo), s3_url)
        mock_get_image_url_from_s3.assert_called_once_with("cover-image.jpg")


@patch("nofos.nofo.upload_file_to_s3")
class UploadCoverImageToS3Tests(TestCase):
    def setUp(self):
        self.nofo = Nofo.objects.create(
            title="Test NOFO Title",
            short_name="TEST-001",
            number="TEST-001",
            opdiv="Test Agency",
        )

        # Create valid test file
        self.valid_jpg_file = SimpleUploadedFile(
            "test_image.jpg", b"fake image content", content_type="image/jpeg"
        )

    def test_successful_upload_with_jpg(self, mock_upload_to_s3):
        """Test successful upload of JPG file"""
        mock_upload_to_s3.return_value = "img/cover-img/test-001.jpg"

        result = upload_cover_image_to_s3(
            self.nofo, self.valid_jpg_file, "Test alt text"
        )

        self.assertTrue(result)

        # Check NOFO was updated
        self.nofo.refresh_from_db()
        self.assertEqual(self.nofo.cover_image, "img/cover-img/test-001.jpg")
        self.assertEqual(self.nofo.cover_image_alt_text, "Test alt text")

        # Check S3 upload was called with correct parameters
        mock_upload_to_s3.assert_called_once()
        call_args = mock_upload_to_s3.call_args
        uploaded_file = call_args[0][0]
        key_prefix = call_args[1]["key_prefix"]
        self.assertEqual(uploaded_file.name, "test-001.jpg")
        self.assertEqual(key_prefix, "img/cover-img")

    def test_upload_preserves_existing_alt_text_when_none_provided(
        self, mock_upload_to_s3
    ):
        """Test that existing alt text is preserved when none is provided"""
        self.nofo.cover_image_alt_text = "Existing alt text"
        self.nofo.save()

        mock_upload_to_s3.return_value = "img/cover-img/test-001.jpg"

        result = upload_cover_image_to_s3(self.nofo, self.valid_jpg_file, "")

        self.assertTrue(result)

        # Check existing alt text was preserved
        self.nofo.refresh_from_db()
        self.assertEqual(self.nofo.cover_image_alt_text, "Existing alt text")

    def test_file_size_validation_too_large(self, mock_upload_to_s3):
        """Test file size validation fails for files over 5MB"""
        large_file = SimpleUploadedFile(
            "large_image.jpg",
            b"x" * (6 * 1024 * 1024),  # 6MB
            content_type="image/jpeg",
        )

        with self.assertRaises(ValidationError) as context:
            upload_cover_image_to_s3(self.nofo, large_file)

        self.assertIn("exceeds maximum allowed size", str(context.exception))
        mock_upload_to_s3.assert_not_called()

    def test_file_type_validation_invalid_content_type(self, mock_upload_to_s3):
        """Test file type validation fails for invalid content types"""
        invalid_file = SimpleUploadedFile(
            "document.pdf", b"fake pdf content", content_type="application/pdf"
        )

        with self.assertRaises(ValidationError) as context:
            upload_cover_image_to_s3(self.nofo, invalid_file)

        self.assertIn("Invalid file type", str(context.exception))
        mock_upload_to_s3.assert_not_called()

    def test_file_extension_validation_invalid_extension(self, mock_upload_to_s3):
        """Test file extension validation fails for invalid extensions"""
        # Use valid content type but invalid extension
        invalid_file = SimpleUploadedFile(
            "image.gif",
            b"fake gif content",
            content_type="image/jpeg",  # Valid content type but .gif extension
        )

        with self.assertRaises(ValidationError) as context:
            upload_cover_image_to_s3(self.nofo, invalid_file)

        self.assertIn("Invalid file extension", str(context.exception))
        mock_upload_to_s3.assert_not_called()

    def test_s3_upload_exception(self, mock_upload_to_s3):
        """Test handling of S3 upload exception"""
        mock_upload_to_s3.side_effect = Exception("S3 connection failed")

        with self.assertRaises(Exception) as context:
            upload_cover_image_to_s3(self.nofo, self.valid_jpg_file)

        self.assertIn("S3 connection failed", str(context.exception))


@patch("nofos.nofo.remove_file_from_s3")
class RemoveCoverImageFromS3Tests(TestCase):
    def setUp(self):
        self.nofo = Nofo.objects.create(
            title="Test NOFO Title",
            short_name="TEST-001",
            opdiv="Test Agency",
            cover_image="img/cover-img/test-001.jpg",
            cover_image_alt_text="Test alt text",
        )

    def test_remove_cover_image_with_existing_image(self, mock_remove_from_s3):
        """Test removing cover image when one exists"""
        original_cover_image = self.nofo.cover_image

        remove_cover_image_from_s3(self.nofo)

        # Check NOFO fields were cleared
        self.nofo.refresh_from_db()
        self.assertEqual(self.nofo.cover_image, "")
        self.assertEqual(self.nofo.cover_image_alt_text, "")

        # Check S3 removal was called with correct key
        mock_remove_from_s3.assert_called_once_with(original_cover_image)

    def test_remove_cover_image_with_no_existing_image(self, mock_remove_from_s3):
        """Test removing cover image when none exists"""
        self.nofo.cover_image = ""
        self.nofo.cover_image_alt_text = "Some alt text"
        self.nofo.save()

        remove_cover_image_from_s3(self.nofo)

        # Check NOFO fields were cleared
        self.nofo.refresh_from_db()
        self.assertEqual(self.nofo.cover_image, "")
        self.assertEqual(self.nofo.cover_image_alt_text, "")

        # Check S3 removal was not called since there was no image
        mock_remove_from_s3.assert_not_called()

    def test_remove_cover_image_s3_exception_still_clears_nofo(
        self, mock_remove_from_s3
    ):
        """Test that NOFO is cleared even if S3 removal fails"""
        mock_remove_from_s3.side_effect = Exception("S3 removal failed")

        # The function should raise the exception from S3 removal
        with self.assertRaises(Exception) as context:
            remove_cover_image_from_s3(self.nofo)

        self.assertEqual(str(context.exception), "S3 removal failed")

        # Check NOFO fields were still cleared despite S3 failure
        # (because they're cleared before attempting S3 removal)
        self.nofo.refresh_from_db()
        self.assertEqual(self.nofo.cover_image, "")
        self.assertEqual(self.nofo.cover_image_alt_text, "")

        # Check S3 removal was attempted
        mock_remove_from_s3.assert_called_once()


class TestGetAllIdAttrsForNofo(TestCase):
    def setUp(self):
        self.nofo = Nofo.objects.create(title="Test Nofo", opdiv="Test OpDiv")
        section = Section.objects.create(
            nofo=self.nofo, name="Test Section", order=1, html_id="section1"
        )

        Subsection.objects.create(
            section=section,
            name="Basic information",
            tag="h3",
            body="Basic information section with <span id='subsection_1_custom_id'>custom id</span>",
            order=2,
            html_id="subsection1",
        )

        Subsection.objects.create(
            section=section,
            body="Eligibility section with a link to <span id='subsection_2_custom_id'>custom id 2</span> and <a href='fake_id'>a link</a> to some other id",
            order=3,
        )

        Subsection.objects.create(
            section=section,
            name="Section 3",
            tag="h4",
            body="Eligible applicants section mentioning #applicants (not a valid id)",
            order=4,
            html_id="subsection3",
        )

        Subsection.objects.create(
            section=section,
            name="Section 4",
            tag="h3",
            body="ID for this section is autogenerated",
            order=5,
        )

        Subsection.objects.create(
            section=section,
            name="Section 5",
            tag="h3",
            body="Beginning paragraph\n\nI am adding an id manually\n{ #my-custom-id }\n\nEnd paragraph",
            order=6,
            html_id="subsection5",
        )

    def test_find_all_ids(self):
        expected_ids = {
            "#section1",
            "#subsection1",
            "#subsection_1_custom_id",
            "#subsection_2_custom_id",
            "#subsection3",
            "#5--test-section--section-4",
            "#subsection5",
            "#my-custom-id",
        }
        result = get_all_id_attrs_for_nofo(self.nofo)
        self.assertEqual(result, expected_ids)


###########################################################
######### FIND THINGS IN THE NOFO DOCUMENT TESTS ##########
###########################################################


class GetStep2SectionTests(TestCase):
    def setUp(self):
        """Set up a Nofo instance and create sections for testing."""
        self.nofo = Nofo.objects.create(title="Test NOFO", opdiv="Test Opdiv")

    def test_find_section_by_name(self):
        """Test that the function finds a section with 'Step 2' in the name."""
        Section.objects.create(nofo=self.nofo, name="Step 1: Review", order=1)

        step_2_section = Section.objects.create(
            nofo=self.nofo, name="Step 2: Apply", order=2
        )

        Section.objects.create(
            nofo=self.nofo, name="Step 3: Prepare", order=3
        )  # This section should not be returned

        result = get_step_2_section(self.nofo)
        self.assertEqual(result, step_2_section)

    def test_falls_back_to_order_2(self):
        """Test that if no 'Step 2' section exists, the function falls back to order=2."""
        order_2_section = Section.objects.create(
            nofo=self.nofo, name="General Info", order=2
        )
        Section.objects.create(
            nofo=self.nofo, name="Unrelated Section", order=5
        )  # This section should not be returned

        result = get_step_2_section(self.nofo)
        self.assertEqual(result, order_2_section)

    def test_prefers_step_2_name_over_order_2(self):
        """Test that the function prefers a 'Step 2' section over a section with order=2."""
        step_2_section = Section.objects.create(
            nofo=self.nofo, name="Step 2: Write Application", order=4
        )
        Section.objects.create(
            nofo=self.nofo, name="Eligibility Requirements", order=2
        )  # This section should not be returned

        result = get_step_2_section(self.nofo)
        self.assertEqual(result, step_2_section)

    def test_returns_none_if_no_match(self):
        """Test that the function returns None if no matching sections exist."""
        Section.objects.create(nofo=self.nofo, name="Unrelated Section", order=1)
        Section.objects.create(nofo=self.nofo, name="Another Unrelated", order=5)

        result = get_step_2_section(self.nofo)
        self.assertIsNone(result)

    def test_multiple_step_2_sections_returns_first(self):
        """Test that the function returns the first 'Step 2' section if multiple exist."""
        step_2a = Section.objects.create(
            nofo=self.nofo, name="Step 2: Prepare", order=1
        )
        Section.objects.create(
            nofo=self.nofo, name="Step 2: Write Application", order=3
        )  # Second section

        result = get_step_2_section(self.nofo)
        self.assertEqual(result, step_2a)


class TestFindSameOrHigherHeadingLevelsConsecutive(TestCase):
    def test_find_same_or_higher_heading_levels_consecutive_h3s(self):
        nofo_obj = [
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
                        "body": [""],
                    },
                    {
                        "name": "Subsection 2",
                        "order": 2,
                        "tag": "h3",
                        "body": [""],
                    },
                ],
            }
        ]

        nofo = create_nofo("Test Nofo", nofo_obj, opdiv="Test OpDiv")
        first_section = nofo.sections.first()

        error_messages = find_same_or_higher_heading_levels_consecutive(nofo)
        self.assertEqual(
            error_messages,
            [
                {
                    "subsection": first_section.subsections.all().order_by("order")[1],
                    "name": "Subsection 2",
                    "error": "Repeated heading level: two h3 headings in a row.",
                }
            ],
        )

    def test_find_same_or_higher_heading_levels_consecutive_h3s_trailing_body(self):
        nofo_obj = [
            {
                "name": "Section 1",
                "order": 1,
                "html_id": "",
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "Subsection 1",
                        "order": 1,
                        "tag": "h4",
                        "body": [""],
                    },
                    {
                        "name": "Subsection 2",
                        "order": 2,
                        "tag": "h4",
                        "body": ["<p>Hello, Subsection 2</p>"],
                    },
                ],
            }
        ]

        nofo = create_nofo("Test Nofo", nofo_obj, opdiv="Test OpDiv")
        first_section = nofo.sections.first()

        error_messages = find_same_or_higher_heading_levels_consecutive(nofo)
        self.assertEqual(
            error_messages,
            [
                {
                    "subsection": first_section.subsections.all().order_by("order")[1],
                    "name": "Subsection 2",
                    "error": "Repeated heading level: two h4 headings in a row.",
                }
            ],
        )

    def test_find_lower_heading_level_followed_by_higher_heading_level(self):
        # error with subsection 3 since subsection 2 has no body and immediately is followed by a higher heading level
        nofo_obj = [
            {
                "name": "Section 1",
                "order": 1,
                "html_id": "",
                "opdiv": "Test OpDiv",
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "Subsection 1",
                        "order": 1,
                        "tag": "h3",
                        "body": [""],
                    },
                    {
                        "name": "Subsection 2",
                        "order": 2,
                        "tag": "h4",
                        "body": [""],
                    },
                    {
                        "name": "Subsection 3",
                        "order": 3,
                        "tag": "h3",
                        "body": [""],
                    },
                ],
            }
        ]

        nofo = create_nofo("Test Nofo", nofo_obj, opdiv="Test OpDiv")
        first_section = nofo.sections.first()

        error_messages = find_same_or_higher_heading_levels_consecutive(nofo)
        self.assertEqual(
            error_messages,
            [
                {
                    "subsection": first_section.subsections.all().order_by("order")[2],
                    "name": "Subsection 3",
                    "error": "Incorrectly nested heading level: h4 immediately followed by a larger h3.",
                }
            ],
        )

    def test_find_lower_heading_level_with_body_followed_by_higher_heading_level(self):
        # since subsection 2 has a body, there is no problem.
        nofo_obj = [
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
                        "body": [""],
                    },
                    {
                        "name": "Subsection 2",
                        "order": 2,
                        "tag": "h4",
                        "body": ["<p>Hello</p>"],
                    },
                    {
                        "name": "Subsection 3",
                        "order": 3,
                        "tag": "h3",
                        "body": [""],
                    },
                ],
            }
        ]

        nofo = create_nofo("Test Nofo", nofo_obj, opdiv="Test OpDiv")

        error_messages = find_same_or_higher_heading_levels_consecutive(nofo)
        self.assertEqual(error_messages, [])

    def test_find_same_heading_levels_with_body(self):
        nofo_obj = [
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
                        "body": ["<p>Hello, Subsection 1</p>"],
                    },
                    {
                        "name": "Subsection 2",
                        "order": 2,
                        "tag": "h3",
                        "body": [""],
                    },
                ],
            }
        ]

        nofo = create_nofo("Test Nofo", nofo_obj, opdiv="Test OpDiv")
        error_messages = find_same_or_higher_heading_levels_consecutive(nofo)
        self.assertEqual(error_messages, [])

    def test_find_same_heading_levels_subsections_in_sections(self):
        nofo_obj = [
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
                        "body": [""],
                    }
                ],
            },
            {
                "name": "Section 2",
                "order": 2,
                "html_id": "",
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "Subsection 2",
                        "order": 1,
                        "tag": "h3",
                        "body": [""],
                    },
                ],
            },
        ]

        nofo = create_nofo("Test Nofo", nofo_obj, opdiv="Test OpDiv")
        error_messages = find_same_or_higher_heading_levels_consecutive(nofo)
        self.assertEqual(error_messages, [])

    def test_find_same_heading_levels_empty_sections(self):
        nofo_obj = [
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
                        "body": "",
                        "callout_box": False,
                    }
                ],
            },
            {
                "name": "Section 2",
                "order": 2,
                "html_id": "",
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "Subsection 2",
                        "order": 1,
                        "tag": "h3",
                        "html_id": "",
                        "body": "",
                        "callout_box": False,
                    }
                ],
            },
        ]

        nofo = create_nofo("Test Nofo", nofo_obj, opdiv="Test OpDiv")
        error_messages = find_same_or_higher_heading_levels_consecutive(nofo)
        self.assertEqual(error_messages, [])

    def test_find_same_heading_levels_section_and_subsection(self):
        # even though the subsection is an h2, this does NOT find it
        nofo_obj = [
            {
                "name": "Section 1",
                "order": 1,
                "html_id": "",
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "Subsection 2",
                        "order": 1,
                        "tag": "h2",
                        "body": [""],
                    },
                ],
            }
        ]

        nofo = create_nofo("Test Nofo", nofo_obj, opdiv="Test OpDiv")
        error_messages = find_same_or_higher_heading_levels_consecutive(nofo)
        self.assertEqual(error_messages, [])

    def test_find_same_heading_levels_with_incorrectly_nested_levels(self):
        nofo_obj = [
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
                        "body": [""],
                    },
                    {
                        "name": "Subsection 2",
                        "order": 2,
                        "tag": "h6",
                        "body": [""],
                    },
                ],
            }
        ]

        nofo = create_nofo("Test Nofo", nofo_obj, opdiv="Test OpDiv")
        error_messages = find_same_or_higher_heading_levels_consecutive(nofo)
        self.assertEqual(error_messages, [])


class TestFindIncorrectlyNestedHeadingLevels(TestCase):
    def test_find_incorrectly_nested_heading_levels(self):

        # Tuple of tag pairs to test
        tag_pairs = [
            ("h3", "h5"),
            ("h3", "h6"),
            ("h3", "h7"),
            ("h4", "h6"),
            ("h4", "h7"),
            ("h5", "h7"),
        ]

        for parent_tag, child_tag in tag_pairs:
            with self.subTest(parent_tag=parent_tag, child_tag=child_tag):
                nofo_obj = [
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
                                "body": [""],
                            },
                            {
                                "name": "Subsection 2",
                                "order": 2,
                                "tag": "h4",
                                "body": [""],
                            },
                            {
                                "name": "Subsection 3",
                                "order": 3,
                                "tag": parent_tag,
                                "body": [""],
                            },
                            {
                                "name": "Subsection 4",
                                "order": 4,
                                "tag": child_tag,
                                "body": [""],
                            },
                        ],
                    }
                ]

                nofo = create_nofo("Test Nofo", nofo_obj, opdiv="Test OpDiv")
                first_section = nofo.sections.first()

                error_messages = find_incorrectly_nested_heading_levels(nofo)
                self.assertEqual(
                    error_messages,
                    [
                        {
                            "subsection": first_section.subsections.all().order_by(
                                "order"
                            )[3],
                            "name": "Subsection 4",
                            "error": "Incorrectly nested heading level: {} followed by an {}.".format(
                                parent_tag, child_tag
                            ),
                        }
                    ],
                )

    def test_find_incorrectly_nested_heading_levels_section_subsection(self):
        # sections are always h2, so h4 should throw an error
        nofo_obj = [
            {
                "name": "Section 1",
                "order": 1,
                "html_id": "",
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "Subsection 1",
                        "order": 1,
                        "tag": "h4",
                        "body": [""],
                    }
                ],
            }
        ]

        nofo = create_nofo("Test Nofo", nofo_obj, opdiv="Test OpDiv")
        first_section = nofo.sections.first()

        error_messages = find_incorrectly_nested_heading_levels(nofo)
        self.assertEqual(
            error_messages,
            [
                {
                    "subsection": first_section.subsections.all().order_by("order")[0],
                    "name": "Subsection 1",
                    "error": "Incorrectly nested heading level: h2 (Section 1) followed by an h4.",
                }
            ],
        )

    def test_find_incorrectly_nested_heading_levels_callout_box_in_between_subsections(
        self,
    ):
        # sections are always h2, so h4 should throw an error
        nofo_obj = [
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
                        "body": [""],
                    },
                    {
                        "name": "",
                        "order": 2,
                        "tag": "",
                        "html_id": "callout-box",
                        "callout_box": True,
                        "body": ["<p>Callout box</p>"],
                    },
                    {
                        "name": "Subsection 3",
                        "order": 3,
                        "tag": "h5",
                        "body": [""],
                    },
                ],
            }
        ]

        nofo = create_nofo("Test Nofo", nofo_obj, opdiv="Test OpDiv")
        first_section = nofo.sections.first()

        error_messages = find_incorrectly_nested_heading_levels(nofo)
        self.assertEqual(
            error_messages,
            [
                {
                    "subsection": first_section.subsections.all().order_by("order")[2],
                    "name": "Subsection 3",
                    "error": "Incorrectly nested heading level: h3 followed by an h5.",
                }
            ],
        )

    def test_find_incorrectly_nested_heading_levels_all_levels(self):
        nofo_obj = [
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
                        "body": [""],
                    },
                    {
                        "name": "Subsection 2",
                        "order": 2,
                        "tag": "h4",
                        "body": [""],
                    },
                    {
                        "name": "Subsection 3",
                        "order": 3,
                        "tag": "h5",
                        "body": [""],
                    },
                    {
                        "name": "Subsection 4",
                        "order": 4,
                        "tag": "h6",
                        "body": [""],
                    },
                    {
                        "name": "Subsection 5",
                        "order": 5,
                        "tag": "h7",
                        "body": [""],
                    },
                ],
            }
        ]

        nofo = create_nofo("Test Nofo", nofo_obj, opdiv="Test OpDiv")

        error_messages = find_incorrectly_nested_heading_levels(nofo)
        self.assertEqual(error_messages, [])

    def test_find_incorrectly_nested_heading_levels_empty_sections(self):
        nofo_obj = [
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
                        "body": "",
                        "callout_box": False,
                    }
                ],
            },
            {
                "name": "Section 2",
                "order": 2,
                "html_id": "",
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "Subsection 2",
                        "order": 1,
                        "tag": "h3",
                        "html_id": "",
                        "body": "",
                        "callout_box": False,
                    }
                ],
            },
        ]

        nofo = create_nofo("Test Nofo", nofo_obj, opdiv="Test OpDiv")
        error_messages = find_incorrectly_nested_heading_levels(nofo)
        self.assertEqual(error_messages, [])

    def test_find_incorrectly_nested_heading_levels_consecutive_h3s(self):
        nofo_obj = [
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
                        "body": [""],
                    },
                    {
                        "name": "Subsection 2",
                        "order": 2,
                        "tag": "h3",
                        "body": [""],
                    },
                ],
            }
        ]

        nofo = create_nofo("Test Nofo", nofo_obj, opdiv="Test OpDiv")

        error_messages = find_incorrectly_nested_heading_levels(nofo)
        self.assertEqual(error_messages, [])


class TestBuildNofoActionLinks(TestCase):
    def setUp(self):
        # Create a minimal NOFO; add required fields if your model needs them.
        self.nofo = Nofo.objects.create(
            title="Test Nofo Action Links",
            opdiv="Test OpDiv",
            status="draft",
        )

    def _assert_link(self, link, key, label, url_name, danger=False, external=False):
        self.assertEqual(link["key"], key)
        self.assertEqual(link["label"], label)
        expected_href = reverse(url_name, args=[self.nofo.pk])
        self.assertEqual(str(link["href"]), expected_href)

        if danger:
            self.assertTrue(link.get("danger") is True)
        else:
            self.assertFalse(link.get("danger", False))

        if external:
            self.assertTrue(link.get("external") is True)
        else:
            self.assertFalse(link.get("external", False))

    def test_draft_has_reimport_delete_findreplace_in_order_with_count(self):
        self.nofo.status = "draft"
        self.nofo.save()

        links = get_nofo_action_links(self.nofo)
        self.assertEqual(
            [l["key"] for l in links],
            ["find-replace", "compare", "duplicate", "reimport", "delete"],
        )

        self._assert_link(
            links[0],
            key="find-replace",
            label="Find & Replace",
            url_name="nofos:nofo_find_replace",
        )
        self._assert_link(
            links[1],
            key="compare",
            label="Compare NOFO",
            url_name="compare:compare_duplicate",
            external=True,
        )
        self._assert_link(
            links[2],
            key="duplicate",
            label="Duplicate NOFO",
            url_name="nofos:nofo_duplicate",
        )
        self._assert_link(
            links[3],
            key="reimport",
            label="Re-import NOFO",
            url_name="nofos:nofo_import_overwrite",
        )
        self._assert_link(
            links[4],
            key="delete",
            label="Delete NOFO",
            url_name="nofos:nofo_archive",
            danger=True,
        )

    def test_active_has_findreplace_compare_reimport(self):
        self.nofo.status = "active"
        self.nofo.save()

        links = get_nofo_action_links(self.nofo)
        self.assertEqual(
            [l["key"] for l in links],
            ["find-replace", "compare", "duplicate", "reimport"],
        )

    def test_ready_for_qa_has_findreplace_compare_reimport(self):
        self.nofo.status = "ready-for-qa"
        self.nofo.save()

        links = get_nofo_action_links(self.nofo)
        self.assertEqual(
            [l["key"] for l in links],
            ["find-replace", "compare", "duplicate", "reimport"],
        )

    def test_review_has_findreplace_compare(self):
        self.nofo.status = "review"
        self.nofo.save()

        links = get_nofo_action_links(self.nofo)
        self.assertEqual(
            [l["key"] for l in links], ["find-replace", "compare", "duplicate"]
        )

    def test_doge_has_findreplace_compare(self):
        self.nofo.status = "doge"
        self.nofo.save()

        links = get_nofo_action_links(self.nofo)
        self.assertEqual(
            [l["key"] for l in links], ["find-replace", "compare", "duplicate"]
        )

    def test_published_has_no_actions(self):
        self.nofo.status = "published"
        self.nofo.save()

        links = get_nofo_action_links(self.nofo)
        self.assertEqual(links, [])

    def test_paused_has_findreplace_compare(self):
        self.nofo.status = "paused"
        self.nofo.save()

        links = get_nofo_action_links(self.nofo)
        self.assertEqual(
            [l["key"] for l in links], ["find-replace", "compare", "duplicate"]
        )

    def test_cancelled_has_no_actions(self):
        self.nofo.status = "cancelled"
        self.nofo.save()

        links = get_nofo_action_links(self.nofo)
        self.assertEqual(links, [])


class TestFindExternalLinks(TestCase):
    def setUp(self):
        self.sections = _get_sections_dict()

    def test_find_external_links_with_one_link_in_subsections(self):
        self_sections = self.sections
        # add external links to subsections
        self_sections[0]["subsections"][0]["body"] = [
            '<p>Section 1 body with link to <a href="https://groundhog-day.com">Groundhog Day</a></p>'
        ]

        nofo = create_nofo("Test Nofo", self_sections, opdiv="Test OpDiv")
        links = find_external_links(nofo, with_status=False)

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["url"], "https://groundhog-day.com")
        self.assertEqual(links[0]["link_text"], "Groundhog Day")

    def test_find_external_links_ignore_nofo_rodeo(self):
        self_sections = self.sections
        # add external links to subsections
        self_sections[0]["subsections"][0]["body"] = [
            '<p>Section 1 body with link to <a href="https://nofo.rodeo/nofos/">All Nofos</a></p>'
        ]

        nofo = create_nofo("Test Nofo", self_sections, opdiv="Test OpDiv")
        links = find_external_links(nofo, with_status=False)
        self.assertEqual(len(links), 0)

    def test_find_external_links_with_two_links_in_subsections(self):
        self_sections = self.sections
        # add external links to subsections
        self_sections[0]["subsections"][0]["body"] = [
            '<p>Section 1 body with link to <a href="https://groundhog-day.com">Groundhog Day</a></p>'
        ]
        self_sections[0]["subsections"][1]["body"] = [
            '<p>Section 2 body with link to <a href="https://canada-holidays.ca">Canada Holidays</a></p>'
        ]

        nofo = create_nofo("Test Nofo", self_sections, opdiv="Test OpDiv")
        links = find_external_links(nofo, with_status=False)

        self.assertEqual(len(links), 2)
        self.assertEqual(links[0]["url"], "https://groundhog-day.com")
        self.assertEqual(links[0]["link_text"], "Groundhog Day")

        self.assertEqual(links[1]["url"], "https://canada-holidays.ca")
        self.assertEqual(links[1]["link_text"], "Canada Holidays")

    def test_find_external_links_no_link_in_subsection(self):
        # no links in the original subsections
        nofo = create_nofo("Test Nofo", self.sections, opdiv="Test OpDiv")
        links = find_external_links(nofo, with_status=False)

        self.assertEqual(len(links), 0)


class TestFindBrokenLinks(TestCase):
    def setUp(self):
        # Set up a Nofo instance and related Sections and Subsections
        nofo = Nofo.objects.create(
            title="Test Nofo TestFindBrokenLinks", opdiv="test opdiv"
        )
        section = Section.objects.create(nofo=nofo, name="Test Section", order=1)

        Subsection.objects.create(
            section=section,
            name="Subsection with an #h Link",
            tag="h3",
            body="This is a test [broken link](#h.broken-link) in markdown.",
            order=2,
        )

        # Subsection without a broken link
        Subsection.objects.create(
            section=section,
            name="Subsection without Broken Link",
            tag="h3",
            body="This is a test with a [valid link](https://example.com).",
            order=3,
        )

        Subsection.objects.create(
            section=section,
            name="Subsection with an #id link",
            tag="h3",
            body="This is a second [broken link](#id.broken-link) in markdown.",
            order=4,
        )

        Subsection.objects.create(
            section=section,
            name='Subsection with a slash ("/") link',
            tag="h3",
            body="This is a [link that assumes a root domain](/contacts) in markdown.",
            order=5,
        )

        Subsection.objects.create(
            section=section,
            name="Subsection with a Google Docs link",
            tag="h3",
            body="This is a [Google Docs link](https://docs.google.com/document/d/some-document) in markdown.",
            order=6,
        )

        Subsection.objects.create(
            section=section,
            name="Subsection with a Blank link",
            tag="h3",
            body="This is an [About:Blank link](about:blank) in markdown.",
            order=7,
        )

        Subsection.objects.create(
            section=section,
            name="Subsection with an underscore link",
            tag="h3",
            body="This is an [Underscore link](#_Paper_Submissions) in markdown.",
            order=8,
        )

        Subsection.objects.create(
            section=section,
            name="Subsection with real id and fake id",
            tag="h3",
            body="This is an [link](#link), and this is [fake](#fake). <span id='link'>Link links here</span>.",
            order=9,
        )

        Subsection.objects.create(
            section=section,
            name="Subsection with a Bookmark link",
            tag="h3",
            body='This is a <a href="bookmark://_Collaborations">Collaborations</a> bookmark link.',
            order=10,
        )

        Subsection.objects.create(
            section=section,
            name="Subsection with a File link",
            tag="h3",
            body='This is a <a href="file:///C:\\Users\\pcraig3\\Downloads\\HYPERLINK#_Attachment_5:_Data">Attachment 5: Data</a> file link.',
            order=11,
        )

    def test_find_broken_links_identifies_broken_links(self):
        nofo = Nofo.objects.get(title="Test Nofo TestFindBrokenLinks")
        broken_links = find_broken_links(nofo)
        self.assertEqual(len(broken_links), 9)
        self.assertEqual(broken_links[1]["link_href"], "#id.broken-link")
        self.assertEqual(broken_links[2]["link_href"], "/contacts")
        self.assertEqual(
            broken_links[3]["link_href"],
            "https://docs.google.com/document/d/some-document",
        )
        self.assertEqual(
            broken_links[4]["link_href"],
            "about:blank",
        )
        self.assertEqual(
            broken_links[5]["link_href"],
            "#_Paper_Submissions",
        )
        self.assertEqual(
            broken_links[6]["link_href"],
            "#fake",
        )
        self.assertEqual(
            broken_links[7]["link_href"],
            "bookmark://_Collaborations",
        )
        self.assertEqual(
            broken_links[8]["link_href"],
            "file:///C:\\Users\\pcraig3\\Downloads\\HYPERLINK#_Attachment_5:_Data",
        )

    def test_find_broken_links_ignores_valid_links(self):
        nofo = Nofo.objects.get(title="Test Nofo TestFindBrokenLinks")
        broken_links = find_broken_links(nofo)
        valid_links = [
            link
            for link in broken_links
            if not (
                link["link_href"].startswith("#h.")
                or link["link_href"].startswith("#id.")
                or link["link_href"].startswith("/")
                or link["link_href"].startswith("https://docs.google.com")
                or link["link_href"].startswith("about:blank")
                or link["link_href"].startswith("#_")
                or link["link_href"].startswith("#fake")
                or link["link_href"].startswith("bookmark")
                or link["link_href"].startswith("file:///")
            )
        ]
        self.assertEqual(len(valid_links), 0)


class TestFindH7Headers(TestCase):
    def setUp(self):
        self.sections = [
            {
                "name": "New Section H7",
                "order": 1,
                "html_id": "",
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "New Subsection H7",
                        "order": 1,
                        "tag": "h7",
                        "html_id": "1--new-section-h7--new-subsection-h7",
                        "body": ["<p>New Section H7 body</p>"],
                    },
                    {
                        "name": "New Subsection H6",
                        "order": 2,
                        "tag": "h6",
                        "html_id": "1--new-section-h7--new-subsection-h6",
                        "body": ["<p>New Section H6 body</p>"],
                    },
                    {
                        "name": "New Subsection H5",
                        "order": 3,
                        "tag": "h5",
                        "html_id": "1--new-section-h7--new-subsection-h5",
                        "body": [
                            "<p>New Section H5 body</p><h7>This h7 will not be recognized</h7>"
                        ],
                    },
                    {
                        "name": "New Subsection H4",
                        "order": 4,
                        "tag": "h4",
                        "html_id": "1--new-section-h7--new-subsection-h4",
                        "body": [
                            '<p>New Section H4 body</p><div role="heading" aria-level="7">This shimmed h7 will be recognized</div>'
                        ],
                    },
                ],
            }
        ]


class TestGetSideNavLinks(TestCase):
    def setUp(self):
        self.sections = [
            {
                "name": "Section 1",
                "order": 1,
                "html_id": "section-1",
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "Subsection 1",
                        "order": 1,
                        "tag": "h3",
                        "html_id": "subsection-1",
                        "body": ["<p>Section 1 body</p>"],
                    }
                ],
            },
            {
                "name": "Section 2",
                "order": 2,
                "html_id": "section-2",
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "Subsection 2",
                        "order": 1,
                        "tag": "h3",
                        "html_id": "subsection-2",
                        "body": ["<p>Section 2 body</p>"],
                    }
                ],
            },
            {
                "name": "Section 3",
                "order": 3,
                "html_id": "section-3",
                "has_section_page": True,
                "subsections": [],
            },
        ]

    def test_get_side_nav_links_with_sections(self):
        """Test that get_side_nav_links returns correct structure with sections"""
        nofo = create_nofo("Test NOFO", self.sections, opdiv="Test OpDiv")

        result = get_side_nav_links(nofo)

        # Should have summary plus 3 sections
        self.assertEqual(len(result), 4)

        # First item should always be the summary
        self.assertEqual(result[0]["id"], "summary-box-key-information")
        self.assertEqual(result[0]["name"], "NOFO Summary")

        # Check section data
        self.assertEqual(result[1]["id"], "section-1")
        self.assertEqual(result[1]["name"], "Section 1")

        self.assertEqual(result[2]["id"], "section-2")
        self.assertEqual(result[2]["name"], "Section 2")

        self.assertEqual(result[3]["id"], "section-3")
        self.assertEqual(result[3]["name"], "Section 3")

    def test_get_side_nav_links_with_no_sections(self):
        """Test that get_side_nav_links returns only summary when no sections exist"""
        nofo = create_nofo("Empty NOFO", [], opdiv="Test OpDiv")

        result = get_side_nav_links(nofo)

        # Should only have the summary
        self.assertEqual(len(result), 0)


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

    @patch("nofos.nofo.requests.head")
    @patch("nofos.nofo.requests.get")
    def test_status_code_500_retries_with_get(self, mock_get, mock_head):
        # First request (HEAD) returns 500
        mock_head_response = MagicMock()
        mock_head_response.status_code = 500
        mock_head_response.history = []
        mock_head.return_value = mock_head_response

        # Second request (GET) returns 200
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.history = []
        mock_get.return_value = mock_get_response

        all_links = [{"url": "https://example.com", "status": ""}]
        update_link_statuses(all_links)

        # Verify HEAD was called first
        mock_head.assert_called_once_with(
            "https://example.com",
            timeout=5,
            allow_redirects=True,
            headers=REQUEST_HEADERS,
        )

        # Verify GET was called after HEAD returned 500
        mock_get.assert_called_once_with(
            "https://example.com",
            timeout=5,
            allow_redirects=True,
            headers=REQUEST_HEADERS,
        )

        # Verify we got the 200 status from the GET request
        self.assertEqual(all_links[0]["status"], 200)

    @patch("nofos.nofo.requests.head")
    @patch("nofos.nofo.requests.get")
    def test_status_code_500_get_also_fails(self, mock_get, mock_head):
        # First request (HEAD) returns 500
        mock_head_response = MagicMock()
        mock_head_response.status_code = 500
        mock_head_response.history = []
        mock_head.return_value = mock_head_response

        # GET request fails
        mock_get.side_effect = requests.RequestException("GET failed")

        all_links = [{"url": "https://example.com", "status": ""}]
        update_link_statuses(all_links)

        # Verify HEAD was called first
        mock_head.assert_called_once_with(
            "https://example.com",
            timeout=5,
            allow_redirects=True,
            headers=REQUEST_HEADERS,
        )

        # Verify GET was attempted
        mock_get.assert_called_once_with(
            "https://example.com",
            timeout=5,
            allow_redirects=True,
            headers=REQUEST_HEADERS,
        )

        # Verify we kept the 500 status from HEAD since GET failed
        self.assertEqual(all_links[0]["status"], 500)

    @patch("nofos.nofo.requests.head")
    @patch("nofos.nofo.requests.get")
    def test_status_code_403_retries_with_get(self, mock_get, mock_head):
        # First request (HEAD) returns 403
        mock_head_response = MagicMock()
        mock_head_response.status_code = 403
        mock_head_response.history = []
        mock_head.return_value = mock_head_response

        # Second request (GET) returns 200
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.history = []
        mock_get.return_value = mock_get_response

        all_links = [{"url": "https://example.com", "status": ""}]
        update_link_statuses(all_links)

        # Verify HEAD was called first
        mock_head.assert_called_once_with(
            "https://example.com",
            timeout=5,
            allow_redirects=True,
            headers=REQUEST_HEADERS,
        )

        # Verify GET was called after HEAD returned 403
        mock_get.assert_called_once_with(
            "https://example.com",
            timeout=5,
            allow_redirects=True,
            headers=REQUEST_HEADERS,
        )

        # Verify we got the 200 status from the GET request
        self.assertEqual(all_links[0]["status"], 200)

    @patch("nofos.nofo.requests.head")
    @patch("nofos.nofo.requests.get")
    def test_status_code_405_retries_with_get(self, mock_get, mock_head):
        # First request (HEAD) returns 405
        mock_head_response = MagicMock()
        mock_head_response.status_code = 405
        mock_head_response.history = []
        mock_head.return_value = mock_head_response

        # Second request (GET) returns 200
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.history = []
        mock_get.return_value = mock_get_response

        all_links = [{"url": "https://example.com", "status": ""}]
        update_link_statuses(all_links)

        # Verify HEAD was called first
        mock_head.assert_called_once_with(
            "https://example.com",
            timeout=5,
            allow_redirects=True,
            headers=REQUEST_HEADERS,
        )

        # Verify GET was called after HEAD returned 405
        mock_get.assert_called_once_with(
            "https://example.com",
            timeout=5,
            allow_redirects=True,
            headers=REQUEST_HEADERS,
        )

        # Verify we got the 200 status from the GET request
        self.assertEqual(all_links[0]["status"], 200)


#########################################################
#################### SUGGEST X TESTS ####################
#########################################################


class HTMLSuggestTitleTests(TestCase):
    def setUp(self):
        self.nofo_title = "Primary Care Training and Enhancement: Physician Assistant Rural Training in Mental and Behavioral Health (PCTE-PARM) Program"
        self.html_filename = "nofos/fixtures/html/nofo.html"
        with open(self.html_filename, "r", encoding="UTF-8") as file:
            self.soup = BeautifulSoup(file, "html.parser")

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
        with open(self.html_filename, "r", encoding="UTF-8") as file:
            self.soup = BeautifulSoup(file, "html.parser")

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


class HTMLSuggestDeadlineTests(TestCase):
    def setUp(self):
        self.html_filename = "nofos/fixtures/html/nofo.html"
        with open(self.html_filename, "r", encoding="UTF-8") as file:
            self.soup = BeautifulSoup(file, "html.parser")

    def test_suggest_nofo_application_deadline_returns_correct_deadline(self):
        self.assertEqual(suggest_nofo_application_deadline(self.soup), "[ ]")

    def test_suggest_nofo_application_deadline_returns_default_for_bad_html(self):
        default_deadline = "[WEEKDAY, MONTH DAY, YEAR]"
        self.assertEqual(
            suggest_nofo_application_deadline(
                BeautifulSoup(
                    "<html><title>NOFO</title><body><h1>NOFO</h1></body></html>",
                    "html.parser",
                )
            ),
            default_deadline,
        )

    def test_suggest_nofo_application_deadline_returns_correct_deadline_for_p_span(
        self,
    ):
        deadline = "April 17, 1917"
        self.assertEqual(
            suggest_nofo_application_deadline(
                BeautifulSoup(
                    '<html><title>THESES</title><body><h1>THESES</h1><p class="c0"><span class="c3">Application Deadline: April 17, 1917</span></p></body></html>',
                    "html.parser",
                )
            ),
            deadline,
        )

    def test_suggest_nofo_application_deadline_returns_correct_deadline_for_p_span_span(
        self,
    ):
        deadline = "April 17, 1917"
        self.assertEqual(
            suggest_nofo_application_deadline(
                BeautifulSoup(
                    '<html><title>THESES</title><body><h1>THESES</h1><p class="c0"><span class="c180">Application Deadline: </span><span class="c7">April 17, 1917</span><span class="c53 c7 c192">&nbsp;</span></p></body></html>',
                    "html.parser",
                )
            ),
            deadline,
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
        nofo_theme = "portrait-acf-white"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_acl_returns_acl_theme(self):
        nofo_number = "HHS-2024-ACL-NIDILRR-REGE-0078"
        nofo_theme = "portrait-acl-white"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_ihs_returns_ihs_theme(self):
        nofo_number = "HHS-2024-IHS-INMED-0001"
        nofo_theme = "portrait-ihs-white"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_cms_returns_cms_theme(self):
        nofo_number = "CMS-1W1-24-001"
        nofo_theme = "portrait-cms-white"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_rfa_returns_cdc_theme(self):
        nofo_number = "RFA-CK-26-104"
        nofo_theme = "portrait-cdc-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_ihs_and_rfa_returns_ihs_theme(self):
        nofo_number = "IHS-RFA-CK-26-104"
        nofo_theme = "portrait-ihs-white"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_no_match_returns_hrsa_theme(self):
        nofo_number = "abc-def-ghi"
        nofo_theme = "portrait-hrsa-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_empty_returns_hrsa_theme(self):
        nofo_number = ""
        nofo_theme = "portrait-hrsa-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)


class HTMLSuggestCoverTests(TestCase):
    def test_suggest_nofo_cover_cdc_returns_medium(self):
        nofo_cover = "nofo--cover-page--medium"
        self.assertEqual(suggest_nofo_cover("portrait-cdc-blue"), nofo_cover)

    def test_suggest_nofo_cover_cms_returns_medium(self):
        nofo_cover = "nofo--cover-page--medium"
        self.assertEqual(suggest_nofo_cover("portrait-cms-white"), nofo_cover)

    def test_suggest_nofo_cover_ihs_returns_medium(self):
        nofo_cover = "nofo--cover-page--medium"
        self.assertEqual(suggest_nofo_cover("portrait-ihs-white"), nofo_cover)

    def test_suggest_nofo_cover_hrsa_returns_text(self):
        nofo_cover = "nofo--cover-page--text"
        self.assertEqual(suggest_nofo_cover("portrait-hrsa-blue"), nofo_cover)

    def test_suggest_nofo_cover_acf_returns_text(self):
        nofo_cover = "nofo--cover-page--text"
        self.assertEqual(suggest_nofo_cover("portrait-acf-white"), nofo_cover)

    def test_suggest_nofo_cover_acl_returns_text(self):
        nofo_cover = "nofo--cover-page--text"
        self.assertEqual(suggest_nofo_cover("portrait-acl-white"), nofo_cover)

    def test_suggest_nofo_cover_empty_string_returns_medium(self):
        nofo_cover = "nofo--cover-page--medium"
        self.assertEqual(suggest_nofo_cover(""), nofo_cover)


class SuggestNofoOpDivTests(TestCase):
    def test_opdiv_present_in_paragraph(self):
        html = "<div><p>Opdiv: Center for Awesome NOFOs</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_opdiv(soup), "Center for Awesome NOFOs")

    def test_opdiv_present_not_in_paragraph(self):
        html = "<div><span>Opdiv: Center for Awesome NOFOs</span></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_opdiv(soup), "Center for Awesome NOFOs")

    def test_opdiv_present_with_predecing_whitespace(self):
        html = "<div><p>  Opdiv: Center for Awesome NOFOs</p></div>"
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


class SuggestNofoFieldsTests(TestCase):
    def setUp(self):
        # Add required fields
        self.nofo = Nofo.objects.create(title="Test NOFO", opdiv="Test OpDiv")

        # Create a section and subsection
        self.section = Section.objects.create(
            nofo=self.nofo, name="Test Section", order=1
        )

        self.subsection = Subsection.objects.create(
            section=self.section,
            name="Test Subsection",
            order=2,
            tag="h2",  # Required when name is present
        )

        # Sample HTML content
        self.html_content = """
            <html>
                <body>
                    <p>Opportunity Name: Cowpolk Training 2024-2025</p>
                    <p>Opportunity Number: HRSA-2024-YEEHAW-001</p>
                    <p>OpDiv: Department of Wild Western Affairs (DWWA)</p>
                    <p>Agency: Bureau of Cowpolk Initiatives (BCI)</p>
                    <p>Subagency: Cowpolk Training and Development</p>
                    <p>Subagency2: Wild-West Expansion Projects</p>
                    <p>Tagline: This program aims to promote economic development in rural towns by providing training and resources for new cattle ranching projects.</p>
                    <p>Application Deadline: 2024-05-31</p>
                    <p>Metadata Author: Sheriff Adam</p>
                    <p>Metadata Subject: Cowpolk Training and Economic Development</p>
                    <p>Metadata Keywords: cowpolk, wild west, economic development, training, cattle ranching</p>
                </body>
            </html>
        """
        self.soup = BeautifulSoup(self.html_content, "html.parser")

    def test_suggest_all_nofo_fields(self):
        suggest_all_nofo_fields(self.nofo, self.soup)
        self.nofo.save()

        self.assertEqual(self.nofo.title, "Cowpolk Training 2024-2025")
        self.assertEqual(self.nofo.number, "HRSA-2024-YEEHAW-001")
        self.assertEqual(self.nofo.application_deadline, "2024-05-31")
        self.assertEqual(self.nofo.opdiv, "Department of Wild Western Affairs (DWWA)")
        self.assertEqual(self.nofo.agency, "Bureau of Cowpolk Initiatives (BCI)")
        self.assertEqual(self.nofo.subagency, "Cowpolk Training and Development")
        self.assertEqual(self.nofo.subagency2, "Wild-West Expansion Projects")
        self.assertEqual(
            self.nofo.tagline,
            "This program aims to promote economic development in rural towns by providing training and resources for new cattle ranching projects.",
        )
        self.assertEqual(self.nofo.author, "Sheriff Adam")
        self.assertEqual(self.nofo.subject, "Cowpolk Training and Economic Development")
        self.assertEqual(
            self.nofo.keywords,
            "cowpolk, wild west, economic development, training, cattle ranching",
        )
        self.assertEqual(self.nofo.theme, "portrait-hrsa-blue")
        self.assertEqual(self.nofo.cover, "nofo--cover-page--text")

    def test_suggest_all_nofo_fields_with_missing_data(self):
        # HTML content with some missing fields
        html_content_missing_data = """
            <html>
                <body>
                    <p>Opportunity Number: HRSA-2024-YEEHAW-001</p>
                    <p>OpDiv: Department of Wild Western Affairs (DWWA)</p>
                </body>
            </html>
        """
        soup_missing_data = BeautifulSoup(html_content_missing_data, "html.parser")
        suggest_all_nofo_fields(self.nofo, soup_missing_data)
        self.nofo.save()

        self.assertEqual(self.nofo.title, "Test NOFO")  # Title should remain unchanged
        self.assertEqual(self.nofo.number, "HRSA-2024-YEEHAW-001")
        self.assertEqual(self.nofo.application_deadline, "[WEEKDAY, MONTH DAY, YEAR]")
        self.assertEqual(self.nofo.opdiv, "Department of Wild Western Affairs (DWWA)")
        self.assertEqual(self.nofo.agency, "")
        self.assertEqual(self.nofo.subagency, "")
        self.assertEqual(self.nofo.subagency2, "")
        self.assertEqual(self.nofo.tagline, "")
        self.assertEqual(self.nofo.author, "")
        self.assertEqual(self.nofo.subject, "")
        self.assertEqual(self.nofo.keywords, "")

        # still get set
        self.assertEqual(self.nofo.theme, "portrait-hrsa-blue")
        self.assertEqual(self.nofo.cover, "nofo--cover-page--text")

    def test_suggest_all_nofo_fields_overwrite_empty_fields(self):
        suggest_all_nofo_fields(self.nofo, self.soup)
        self.nofo.save()

        # First time, normal
        self.assertEqual(self.nofo.title, "Cowpolk Training 2024-2025")
        self.assertEqual(self.nofo.number, "HRSA-2024-YEEHAW-001")
        self.assertEqual(self.nofo.application_deadline, "2024-05-31")
        self.assertEqual(self.nofo.opdiv, "Department of Wild Western Affairs (DWWA)")
        self.assertEqual(self.nofo.agency, "Bureau of Cowpolk Initiatives (BCI)")
        self.assertEqual(self.nofo.subagency, "Cowpolk Training and Development")
        self.assertEqual(self.nofo.subagency2, "Wild-West Expansion Projects")
        self.assertEqual(
            self.nofo.tagline,
            "This program aims to promote economic development in rural towns by providing training and resources for new cattle ranching projects.",
        )
        self.assertEqual(self.nofo.author, "Sheriff Adam")
        self.assertEqual(self.nofo.subject, "Cowpolk Training and Economic Development")
        self.assertEqual(
            self.nofo.keywords,
            "cowpolk, wild west, economic development, training, cattle ranching",
        )

        # Second time, change or overwrite values
        # HTML content with some missing fields
        html_content_missing_data = """
            <html>
                <body>
                    <p>Opportunity Name: Ranch Grants 2024-2025</p>             <!-- changed -->
                    <p>Opportunity Number: HRSA-2024-HOLLER-001</p>             <!-- changed -->
                    <p>Application Deadline: 2025-01-01</p>                     <!-- changed -->
                    <p>OpDiv: Department of Hootin’ Tootin’ Affairs (DHTA)</p>  <!-- changed -->
                    <p>Agency: Bureau of Cowpolk Expansion (BCE)</p>            <!-- changed -->
                    <p>Subagency: </p>                                          <!-- empty -->
                    <p>Subagency2: </p>                                         <!-- empty -->
                    <p>Tagline: This program aims to promote economic development in rural towns by providing training and resources for new cattle ranching projects.</p>
                    <p>Metadata Author: Sheriff Adam</p>
                    <p>Metadata Subject: Cowpolk Training and Ukpskilling</p>   <!-- changed -->
                    <p>Metadata Keywords:</p>                                   <!-- empty -->
                </body>
            </html>
        """
        soup_missing_data = BeautifulSoup(html_content_missing_data, "html.parser")
        suggest_all_nofo_fields(self.nofo, soup_missing_data)
        self.nofo.save()

        self.assertEqual(self.nofo.title, "Ranch Grants 2024-2025")
        self.assertEqual(self.nofo.number, "HRSA-2024-HOLLER-001")
        self.assertEqual(self.nofo.application_deadline, "2025-01-01")
        self.assertEqual(
            self.nofo.opdiv, "Department of Hootin’ Tootin’ Affairs (DHTA)"
        )
        self.assertEqual(self.nofo.agency, "Bureau of Cowpolk Expansion (BCE)")
        self.assertEqual(self.nofo.subagency, "")
        self.assertEqual(self.nofo.subagency2, "")
        self.assertEqual(
            self.nofo.tagline,
            "This program aims to promote economic development in rural towns by providing training and resources for new cattle ranching projects.",
        )
        self.assertEqual(self.nofo.author, "Sheriff Adam")
        self.assertEqual(self.nofo.subject, "Cowpolk Training and Ukpskilling")
        self.assertEqual(self.nofo.keywords, "")

    def test_suggest_all_nofo_fields_overwrite_missing_fields(self):
        suggest_all_nofo_fields(self.nofo, self.soup)
        self.nofo.save()

        # First time, normal
        self.assertEqual(self.nofo.title, "Cowpolk Training 2024-2025")
        self.assertEqual(self.nofo.number, "HRSA-2024-YEEHAW-001")
        self.assertEqual(self.nofo.application_deadline, "2024-05-31")
        self.assertEqual(self.nofo.opdiv, "Department of Wild Western Affairs (DWWA)")
        self.assertEqual(self.nofo.agency, "Bureau of Cowpolk Initiatives (BCI)")
        self.assertEqual(self.nofo.subagency, "Cowpolk Training and Development")
        self.assertEqual(self.nofo.subagency2, "Wild-West Expansion Projects")
        self.assertEqual(
            self.nofo.tagline,
            "This program aims to promote economic development in rural towns by providing training and resources for new cattle ranching projects.",
        )
        self.assertEqual(self.nofo.author, "Sheriff Adam")
        self.assertEqual(self.nofo.subject, "Cowpolk Training and Economic Development")
        self.assertEqual(
            self.nofo.keywords,
            "cowpolk, wild west, economic development, training, cattle ranching",
        )

        # Second time, change or overwrite values
        # HTML content with some missing fields
        html_content_missing_data = """
            <html>
                <body>
                    <p>Opportunity Name: Tarnation Appropriation 2024-2025</p>
                    <p>Opportunity Number: HRSA-2024-HOLLER-001</p>
                    <p>Application Deadline: 2025-01-01</p>
                    <p>OpDiv: Department of Hootin' Tootin' Affairs (DHTA)</p>
                    <!-- everything below here is missing -->
                </body>
            </html>
        """
        soup_missing_data = BeautifulSoup(html_content_missing_data, "html.parser")
        suggest_all_nofo_fields(self.nofo, soup_missing_data)
        self.nofo.save()

        self.assertEqual(self.nofo.title, "Tarnation Appropriation 2024-2025")
        self.assertEqual(self.nofo.number, "HRSA-2024-HOLLER-001")
        self.assertEqual(self.nofo.application_deadline, "2025-01-01")
        self.assertEqual(
            self.nofo.opdiv, "Department of Hootin' Tootin' Affairs (DHTA)"
        )
        self.assertEqual(self.nofo.agency, "")
        self.assertEqual(self.nofo.subagency, "")
        self.assertEqual(self.nofo.subagency2, "")
        self.assertEqual(self.nofo.tagline, "")
        self.assertEqual(self.nofo.author, "")
        self.assertEqual(self.nofo.subject, "")
        self.assertEqual(self.nofo.keywords, "")

    def test_title_doesnt_reset_if_empty(self):
        html_content = """
            <html>
                <body>
                    <p>Opportunity Name: My Awesome NOFO</p>
                    <p>OpDiv: Test OpDiv</p>
                </body>
            </html>
        """
        suggest_all_nofo_fields(self.nofo, BeautifulSoup(html_content, "html.parser"))
        self.nofo.save()

        self.assertEqual(self.nofo.title, "My Awesome NOFO")

        new_html_content = """
            <html>
                <body>
                    <p>Opportunity Name:</p> <!-- empty -->
                    <p>OpDiv: Test OpDiv</p>
                </body>
            </html>
        """
        suggest_all_nofo_fields(
            self.nofo, BeautifulSoup(new_html_content, "html.parser")
        )
        self.nofo.save()

        self.assertEqual(self.nofo.title, "My Awesome NOFO")

    def test_title_doesnt_reset_if_missing(self):
        html_content = """
            <html>
                <body>
                    <p>Opportunity Name: My Awesome NOFO</p>
                    <p>OpDiv: Test OpDiv</p>
                </body>
            </html>
        """
        suggest_all_nofo_fields(self.nofo, BeautifulSoup(html_content, "html.parser"))
        self.nofo.save()

        self.assertEqual(self.nofo.title, "My Awesome NOFO")

        new_html_content = """
            <html>
                <body>
                    <!-- No opportunity name -->
                    <p>Opportunity Number: 123</p>
                    <p>OpDiv: Test OpDiv</p>
                </body>
            </html>
        """
        suggest_all_nofo_fields(
            self.nofo, BeautifulSoup(new_html_content, "html.parser")
        )
        self.nofo.save()

        self.assertEqual(self.nofo.title, "My Awesome NOFO")

    def test_theme_and_cover_not_changed_once_set(self):
        nofo = Nofo.objects.create(
            title="Test NOFO",
            opdiv="Test OpDiv",
            number="HRSA-2024-001",
            theme="portrait-hrsa-blue",
            cover="nofo--cover-page--text",
        )

        Section.objects.create(nofo=nofo, name="Test Section", order=1)

        html_content = """
            <html>
                <body>
                    <p>Opportunity Number: CDC-2024-1234</p>
                    <p>OpDiv: Test OpDiv</p>
                </body>
            </html>
        """

        suggest_all_nofo_fields(nofo, BeautifulSoup(html_content, "html.parser"))
        nofo.save()

        self.assertEqual(nofo.number, "CDC-2024-1234")
        self.assertEqual(nofo.theme, "portrait-hrsa-blue")
        self.assertEqual(nofo.cover, "nofo--cover-page--text")

        new_content = """
            <html>
                <body>
                    <p>Opportunity Number: HRSA-2024-1234</p>
                    <p>OpDiv: Test OpDiv</p>
                </body>
            </html>
        """
        suggest_all_nofo_fields(nofo, BeautifulSoup(new_content, "html.parser"))
        nofo.save()

        self.assertEqual(nofo.number, "HRSA-2024-1234")
        self.assertEqual(nofo.theme, "portrait-hrsa-blue")
        self.assertEqual(nofo.cover, "nofo--cover-page--text")


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

    def test_both_links_href_empty(self):
        html = '<p>See <a id="t.123"></a><a id="t.123"></a></p>'
        soup = BeautifulSoup(html, "html.parser")
        combine_consecutive_links(soup)
        self.assertEqual(str(soup), '<p>See <a id="t.123"></a></p>')

    def test_first_link_href_empty(self):
        html = '<p>See <a id="t.123"></a><a id="t.123">Second link</a></p>'
        soup = BeautifulSoup(html, "html.parser")
        combine_consecutive_links(soup)
        self.assertEqual(str(soup), '<p>See <a id="t.123">Second link</a></p>')

    def test_second_link_href_empty(self):
        html = '<p>See <a id="t.123">First link</a><a id="t.123"></a></p>'
        soup = BeautifulSoup(html, "html.parser")
        combine_consecutive_links(soup)
        self.assertEqual(str(soup), '<p>See <a id="t.123">First link</a></p>')

    def test_second_unmatched_link_is_dropped(self):
        html = '<p>See <a id="t.111"></a><a id="t.999"></a></p>'
        soup = BeautifulSoup(html, "html.parser")
        combine_consecutive_links(soup)
        self.assertEqual(str(soup), '<p>See <a id="t.111"></a></p>')

    def test_consecutive_links_wrapped_in_spans_merged(self):
        html = '<p>See <span><a href="#h.ggohvukufhrn">30% cost-sharing</a></span><a href="#h.ggohvukufhrn"> </a><span><a class="c6" href="#h.ggohvukufhrn">requirement</a></span></p>'
        expected_html = (
            '<p>See <a href="#h.ggohvukufhrn">30% cost-sharing requirement</a></p>'
        )
        soup = BeautifulSoup(html, "html.parser")
        combine_consecutive_links(soup)
        self.assertEqual(str(soup), expected_html)


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

    def test_remove_empty_nested_tags_with_href(self):
        html = "<body><div><p><a href='#'></a></p></div><div><span>Hello</span></div></body>"
        soup = BeautifulSoup(html, "html.parser")
        decompose_empty_tags(soup)
        # first div is removed because everything is empty
        self.assertEqual(len(soup.find_all("div")), 1)
        self.assertEqual(len(soup.find_all("a")), 0)

    def test_keep_empty_nested_tags_if_parent_tag_is_not_empty(self):
        html = "<body><div><a href='#'></a><span>Hello</span></div><div><span>Hello</span></div></body>"
        soup = BeautifulSoup(html, "html.parser")
        decompose_empty_tags(soup)
        # first div is kept because span in first div is not empty
        self.assertEqual(len(soup.find_all("div")), 2)
        # empty anchor tag is kept
        self.assertEqual(len(soup.find_all("a")), 1)

    def test_keep_remove_nested_p_tags_if_parent_tag_is_not_empty(self):
        html = "<body><div><p></p><span>Hello</span></div><div><span>Hello</span></div></body>"
        soup = BeautifulSoup(html, "html.parser")
        decompose_empty_tags(soup)
        # first div is kept because span in first div is not empty
        self.assertEqual(len(soup.find_all("div")), 2)
        self.assertEqual(len(soup.find_all("span")), 2)
        # empty anchor tag is kept
        self.assertEqual(len(soup.find_all("p")), 0)

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


class UnwrapEmptyElementsTests(TestCase):
    def test_unwrap_empty_span(self):
        html = "<div><span> </span>text</div>"
        soup = BeautifulSoup(html, "html.parser")
        unwrap_empty_elements(soup)
        self.assertEqual(str(soup), "<div> text</div>")

    def test_unwrap_empty_strong(self):
        html = "<div><strong> </strong>text</div>"
        soup = BeautifulSoup(html, "html.parser")
        unwrap_empty_elements(soup)
        self.assertEqual(str(soup), "<div> text</div>")

    def test_unwrap_empty_sup(self):
        html = "<p>At a minimum,<sup> </sup>HVAs must:</p>"
        soup = BeautifulSoup(html, "html.parser")
        unwrap_empty_elements(soup)
        self.assertEqual(str(soup), "<p>At a minimum, HVAs must:</p>")

    def test_unwrap_empty_em(self):
        html = "<p>At a minimum,<em> </em>HVAs must:</p>"
        soup = BeautifulSoup(html, "html.parser")
        unwrap_empty_elements(soup)
        self.assertEqual(str(soup), "<p>At a minimum, HVAs must:</p>")

    def test_not_unwrap_non_empty_span(self):
        html = "<div><span>Not empty</span></div>"
        soup = BeautifulSoup(html, "html.parser")
        unwrap_empty_elements(soup)
        self.assertEqual(str(soup), "<div><span>Not empty</span></div>")

    def test_not_unwrap_non_empty_strong(self):
        html = "<div><strong>Not empty</strong></div>"
        soup = BeautifulSoup(html, "html.parser")
        unwrap_empty_elements(soup)
        self.assertEqual(str(soup), "<div><strong>Not empty</strong></div>")

    def test_not_unwrap_non_empty_sup(self):
        html = '<p>complete this activity or create your own.<sup><a href="#footnote-16" id="footnote-ref-16">[17]</a></sup> Your HCC(s) must share</p>'
        soup = BeautifulSoup(html, "html.parser")
        unwrap_empty_elements(soup)
        self.assertEqual(str(soup), html)

    def test_not_unwrap_non_empty_em(self):
        html = '<p>complete this activity or create your own.<em><a href="#footnote-16" id="footnote-ref-16">[17]</a></em> Your HCC(s) must share</p>'
        soup = BeautifulSoup(html, "html.parser")
        unwrap_empty_elements(soup)
        self.assertEqual(str(soup), html)

    def test_unwrap_nested_empty_elements(self):
        html = "<div><span><strong> </strong></span></div>"
        soup = BeautifulSoup(html, "html.parser")
        unwrap_empty_elements(soup)
        self.assertEqual(str(soup), "<div> </div>")

    def test_mixed_empty_and_non_empty_elements(self):
        html = "<div><span> </span><strong>Text</strong><span>More text</span><strong> </strong></div>"
        soup = BeautifulSoup(html, "html.parser")
        unwrap_empty_elements(soup)
        self.assertEqual(
            str(soup), "<div> <strong>Text</strong><span>More text</span> </div>"
        )

    def test_unwrap_strong_wrapping_image(self):
        html = '<p><strong><img alt="example" src="img.png"></strong></p>'
        soup = BeautifulSoup(html, "html.parser")
        unwrap_empty_elements(soup)
        self.assertEqual(
            str(soup),
            '<p><img alt="example" src="img.png"/></p>',
        )

    def test_unwrap_strong_em_wrapping_image(self):
        html = '<p><strong><em><img alt="example" src="img.png"></em></strong></p>'
        soup = BeautifulSoup(html, "html.parser")
        unwrap_empty_elements(soup)
        self.assertEqual(
            str(soup),
            '<p><img alt="example" src="img.png"/></p>',
        )

    def test_not_unwrap_em_with_image_and_text(self):
        html = '<p><em><img alt="example" src="img.png"> Caption</em></p>'
        soup = BeautifulSoup(html, "html.parser")
        unwrap_empty_elements(soup)
        # same as html but with a backslash "/" in img tag
        self.assertEqual(
            str(soup),
            '<p><em><img alt="example" src="img.png"/> Caption</em></p>',
        )

    def test_unwrap_span_wrapping_image(self):
        html = '<p><span><img alt="example" src="img.png"></span></p>'
        soup = BeautifulSoup(html, "html.parser")
        unwrap_empty_elements(soup)
        self.assertEqual(
            str(soup),
            '<p><img alt="example" src="img.png"/></p>',
        )


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

    @patch("nofos.nofo.suggest_nofo_opportunity_number")
    def test_ignore_img_with_a_data_url(self, mock_suggest_nofo):
        mock_suggest_nofo.return_value = "hrsa-24-017"
        html = "<img src='data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2Q==' />"
        soup = BeautifulSoup(html, "html.parser")

        replace_src_for_inline_images(soup)
        self.assertEqual(
            soup.find("img")["src"],
            "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2Q==",
        )


class TestAddEndnotesHeaderIfExists(TestCase):
    def test_basic_with_hr_without_style(self):
        html_content = "<div><hr></div>"
        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup)
        self.assertEqual(
            str(soup),
            "<div><h1>Endnotes</h1></div>",
        )

    def test_basic_ol_with_h1_heading_creates_h1(self):
        html_content = '<div><h1>Step 1: Review the opportunity</h1><p>Review it</p><ol><li id="footnote-10">Item 1</li></ol></div>'
        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup)
        self.assertEqual(
            str(soup),
            '<div><h1>Step 1: Review the opportunity</h1><p>Review it</p><h1>Endnotes</h1><ol><li id="footnote-10">Item 1</li></ol></div>',
        )

    def test_basic_ol_with_h2_heading_creates_h2(self):
        html_content = '<div><h2>Step 1: Review the opportunity</h2><p>Review it</p><ol><li id="footnote-10">Item 1</li></ol></div>'
        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup, top_heading_level="h2")
        self.assertEqual(
            str(soup),
            '<div><h2>Step 1: Review the opportunity</h2><p>Review it</p><h2>Endnotes</h2><ol><li id="footnote-10">Item 1</li></ol></div>',
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
            "<div><hr/><h1>Endnotes</h1></div>",
        )

    def test_basic_ol_with_footnote_li(self):
        html_content = '<div><ol><li id="footnote-10">Item 1</li></ol></div>'
        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup)
        self.assertEqual(
            str(soup),
            '<div><h1>Endnotes</h1><ol><li id="footnote-10">Item 1</li></ol></div>',
        )

    def test_basic_ol_with_endnote_li(self):
        html_content = '<div><ol><li id="endnote-2">Item 1</li></ol></div>'
        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup)
        self.assertEqual(
            str(soup),
            '<div><h1>Endnotes</h1><ol><li id="endnote-2">Item 1</li></ol></div>',
        )

    def test_basic_ol_with_li_no_id(self):
        html_content = "<div><ol><li>Item 1</li></ol></div>"
        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup)
        self.assertEqual(str(soup), html_content)

    def test_basic_ol_with_li_not_starts_with_footnote(self):
        html_content = (
            '<div><ol><li id="not-startswith-footnote">Item 1</li></ol></div>'
        )
        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup)
        self.assertEqual(
            str(soup),
            html_content,
        )

    def test_basic_ol_with_footnote_li_but_NOT_last_ol(self):
        html_content = '<div><ol><li id="footnote-0">Item 1.1</li></ol><ol><li>Item 2.1</li></ol></div>'
        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup)
        self.assertEqual(str(soup), html_content)

    # only convert the hr
    def test_basic_with_hr_without_style_AND_basic_ol_with_footnote_li(self):
        html_content = '<div><hr><ol><li id="footnote-0">Item 1</li></ol></div>'
        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup)
        self.assertEqual(
            str(soup),
            '<div><h1>Endnotes</h1><ol><li id="footnote-0">Item 1</li></ol></div>',
        )

    # only convert the hr, even though it is after the ol
    def test_basic_ol_with_footnote_li_AND_basic_with_hr_without_style(self):
        html_content = '<div><ol><li id="footnote-0">Item 1</li></ol><hr></div>'
        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup)
        self.assertEqual(
            str(soup),
            '<div><ol><li id="footnote-0">Item 1</li></ol><h1>Endnotes</h1></div>',
        )

    def test_multiple_ols_with_footnote_li(self):
        html_content = '<div><ol><li id="footnote-0">Item 1.1</li></ol><ol><li id="footnote-0">Item 2.1</li></ol></div>'
        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup)
        self.assertEqual(
            str(soup),
            '<div><ol><li id="footnote-0">Item 1.1</li></ol><h1>Endnotes</h1><ol><li id="footnote-0">Item 2.1</li></ol></div>',
        )

    def test_basic_ol_with_footnote_li_and_other_stuff(self):
        html_content = '<div><ol><li id="footnote-0">Item 1</li></ol><h1>Step 8: Play Northgard</h1><p>Northgard is a fun way to spend time while waiting for the results of your appliation</p></div>'
        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup)
        self.assertEqual(
            str(soup),
            '<div><h1>Endnotes</h1><ol><li id="footnote-0">Item 1</li></ol><h1>Step 8: Play Northgard</h1><p>Northgard is a fun way to spend time while waiting for the results of your appliation</p></div>',
        )

    def test_endnotes_h1_already_exists_with_basic_ol_with_footnote_li_AND_basic_with_hr_without_style(
        self,
    ):
        html_content = (
            '<div><ol><li id="footnote-0">Item 1</li></ol><hr><h1>Endnotes</h1></div>'
        )
        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup)
        self.assertEqual(
            str(soup),
            '<div><ol><li id="footnote-0">Item 1</li></ol><hr/><h1>Endnotes</h1></div>',
        )

    def test_endnotes_h2_already_exists_with_basic_ol_with_footnote_li_AND_basic_with_hr_without_style(
        self,
    ):
        html_content = (
            '<div><ol><li id="footnote-0">Item 1</li></ol><hr><h2>Endnotes</h2></div>'
        )
        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup)
        self.assertEqual(
            str(soup),
            '<div><ol><li id="footnote-0">Item 1</li></ol><hr/><h2>Endnotes</h2></div>',
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


class TestAddEmToDeMinimis(TestCase):
    def test_transforms_de_minimis_spans_to_em(self):
        html = "<p>Some text <span>de minimis</span> rate and <span>De Minimis</span> threshold.</p>"
        expected_html = "<p>Some text <span><em>de minimis</em></span> rate and <span><em>De Minimis</em></span> threshold.</p>"
        soup = BeautifulSoup(html, "html.parser")
        soup = add_em_to_de_minimis(soup)
        self.assertEqual(str(soup), expected_html)

    def test_ignores_non_matching_spans(self):
        html = "<p><span>not de minimis</span> example <span>DE MINIMUS</span>.</p>"
        expected_html = "<p><span>not <em>de minimis</em></span> example <span>DE MINIMUS</span>.</p>"
        soup = BeautifulSoup(html, "html.parser")
        soup = add_em_to_de_minimis(soup)
        self.assertEqual(str(soup), expected_html)

    def test_handles_empty_spans(self):
        html = "<p><span></span> <span>De Minimis</span></p>"
        expected_html = "<p><span></span> <span><em>De Minimis</em></span></p>"
        soup = BeautifulSoup(html, "html.parser")
        soup = add_em_to_de_minimis(soup)
        self.assertEqual(str(soup), expected_html)

    def test_case_insensitive_matching(self):
        html = "<p><span>de minimis</span> <span>De Minimis</span> <span>dE mInImIs</span></p>"
        expected_html = "<p><span><em>de minimis</em></span> <span><em>De Minimis</em></span> <span><em>dE mInImIs</em></span></p>"
        soup = BeautifulSoup(html, "html.parser")
        soup = add_em_to_de_minimis(soup)
        self.assertEqual(str(soup), expected_html)

    def test_classnames_are_preserved(self):
        html = '<p><strong><span class="c7">Method 2—</span></strong><strong><span class="c7 c67">De minimis</span></strong><strong><span class="c7"> rate.</span></strong><span> Per </span><a class="c6" href="https://www.ecfr.gov/current/title-45/part-75#p-75.414(f)">45 CFR 75.414(f)</a><span>, if you have never received a negotiated indirect cost rate, you may elect to charge a </span><span class="c67">de minimis</span><span> rate. If you are awaiting approval of an indirect cost proposal, you may also use the </span><span class="c67">de minimis</span><span class="c0"> rate. If you choose this method, costs included in the indirect cost pool must not be charged as direct costs. </span>I am <em>an emphasized element</em></p>'
        expected_html = '<p><strong><span class="c7">Method 2—</span></strong><strong><span class="c7 c67"><em>De minimis</em></span></strong><strong><span class="c7"> rate.</span></strong><span> Per </span><a class="c6" href="https://www.ecfr.gov/current/title-45/part-75#p-75.414(f)">45 CFR 75.414(f)</a><span>, if you have never received a negotiated indirect cost rate, you may elect to charge a </span><span class="c67"><em>de minimis</em></span><span> rate. If you are awaiting approval of an indirect cost proposal, you may also use the </span><span class="c67"><em>de minimis</em></span><span class="c0"> rate. If you choose this method, costs included in the indirect cost pool must not be charged as direct costs. </span>I am <em>an emphasized element</em></p>'
        soup = BeautifulSoup(html, "html.parser")
        soup = add_em_to_de_minimis(soup)
        self.assertEqual(str(soup), expected_html)

    def test_doesnt_double_wrap_em_tags(self):
        html = '<p><strong>Method 2 — <em>De minimis</em> rate</strong>. Per <a href="https://www.ecfr.gov/current/title-45/part-75#p-75.414(f)">45 CFR 75.414(f)</a>, if you have never received a negotiated indirect cost rate, you may elect to charge a de minimis rate. If you are awaiting approval of an indirect cost proposal, you may also use the <strong>de minimis</strong> rate. If you choose this method, costs included in the indirect cost pool must not be charged as direct costs.</p>'
        expected_html = '<p><strong>Method 2 — <em>De minimis</em> rate</strong>. Per <a href="https://www.ecfr.gov/current/title-45/part-75#p-75.414(f)">45 CFR 75.414(f)</a>, if you have never received a negotiated indirect cost rate, you may elect to charge a <em>de minimis</em> rate. If you are awaiting approval of an indirect cost proposal, you may also use the <strong><em>de minimis</em></strong> rate. If you choose this method, costs included in the indirect cost pool must not be charged as direct costs.</p>'
        soup = BeautifulSoup(html, "html.parser")
        soup = add_em_to_de_minimis(soup)
        self.assertEqual(str(soup), expected_html)


class CleanHeadingsTestCase(TestCase):
    def test_clean_heading_tags_with_various_headings(self):
        html = """
        <h1>   Heading with    <span>spans</span> and &nbsp;spaces&nbsp;   </h1>
        <h2>Another&nbsp;heading</h2>
        <h3> Normal heading </h3>
        <h4>Heading with <span>multiple</span> <span>spans</span></h4>
        """
        soup = BeautifulSoup(html, "html.parser")
        clean_heading_tags(soup)

        self.assertEqual(soup.find("h1").get_text(), "Heading with spans and spaces")
        self.assertEqual(soup.find("h2").get_text(), "Another heading")
        self.assertEqual(soup.find("h3").get_text(), "Normal heading")
        self.assertEqual(soup.find("h4").get_text(), "Heading with multiple spans")

    def test_clean_heading_tags_with_nbsp_in_a_span(self):
        html = '<h1 class="c110"><span>Step</span><span class="c95 c141">&nbsp;</span><span class="c12 c9">1: Review the Opportunity</span></h1>'
        soup = BeautifulSoup(html, "html.parser")
        clean_heading_tags(soup)
        self.assertEqual(soup.find("h1").get_text(), "Step 1: Review the Opportunity")

    def test_clean_heading_tags_with_empty_heading(self):
        html = "<h1> </h1>"
        soup = BeautifulSoup(html, "html.parser")
        clean_heading_tags(soup)
        self.assertEqual(soup.find("h1").get_text(), "")

    def test_clean_heading_tags_with_no_change_needed(self):
        html = "<h1>Perfect Heading</h1>"
        soup = BeautifulSoup(html, "html.parser")
        clean_heading_tags(soup)
        self.assertEqual(soup.find("h1").get_text(), "Perfect Heading")


class PreserveBookmarkLinksTest(TestCase):
    def test_empty_anchor_with_matching_link_followed_by_paragraph(self):
        html = '<p><a href="#bookmark=id.2xcytpi">Bookmark link</a>.</p><a id="bookmark=id.2xcytpi"></a><p>Table 1: FFE state funding allocations</p>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_links(soup)
        expected = '<p><a href="#bookmark=id.2xcytpi">Bookmark link</a>.</p><p class="bookmark" id="bookmark=id.2xcytpi">Table 1: FFE state funding allocations</p>'
        self.assertEqual(str(soup), expected)

    def test_empty_anchor_with_matching_link_followed_by_paragraph_heading_3(self):
        html = '<h2>Title 2</h2><p><a href="#bookmark=id.2xcytpi">Bookmark link</a>.</p><a id="bookmark=id.2xcytpi"></a><p>Table 1: FFE state funding allocations</p>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_links(soup)
        expected = '<h2>Title 2</h2><p><a href="#bookmark=id.2xcytpi">Bookmark link</a>.</p><p class="bookmark-level-3" id="bookmark=id.2xcytpi">Table 1: FFE state funding allocations</p>'
        self.assertEqual(str(soup), expected)

    def test_empty_anchor_with_matching_link_followed_by_paragraph_heading_3(self):
        html = '<h6>Title 6</h6><p><a href="#bookmark=id.2xcytpi">Bookmark link</a>.</p><a id="bookmark=id.2xcytpi"></a><p>Table 1: FFE state funding allocations</p>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_links(soup)
        expected = '<h6>Title 6</h6><p><a href="#bookmark=id.2xcytpi">Bookmark link</a>.</p><p class="bookmark-level-7" id="bookmark=id.2xcytpi">Table 1: FFE state funding allocations</p>'
        self.assertEqual(str(soup), expected)

    def test_empty_anchor_with_matching_link_followed_by_paragraph_wipes_out_existing_id(
        self,
    ):
        html = '<p><a href="#bookmark=id.2xcytpi">Bookmark link</a>.</p><a id="bookmark=id.2xcytpi"></a><p id="table-1">Table 1: FFE state funding allocations</p>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_links(soup)
        expected = '<p><a href="#bookmark=id.2xcytpi">Bookmark link</a>.</p><p class="bookmark" id="bookmark=id.2xcytpi">Table 1: FFE state funding allocations</p>'
        self.assertEqual(str(soup), expected)

    def test_empty_anchor_with_matching_link_followed_by_paragraph_wipes_out_existing_id_but_changes_old_href(
        self,
    ):
        html = '<div><p><a href="#bookmark=id.2xcytpi">Bookmark link</a>.</p><a id="bookmark=id.2xcytpi"></a><p id="table-1">Table 1: FFE state funding allocations</p><p><a href="#table-1">Link to table</a></p></div>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_links(soup)
        expected = '<div><p><a href="#bookmark=id.2xcytpi">Bookmark link</a>.</p><p class="bookmark" id="bookmark=id.2xcytpi">Table 1: FFE state funding allocations</p><p><a href="#bookmark=id.2xcytpi">Link to table</a></p></div>'
        self.assertEqual(str(soup), expected)

    def test_empty_anchor_with_name_attr_with_matching_link_followed_by_paragraph_NOT_used(
        self,
    ):
        html = '<p><a href="#bookmark=id.2xcytpi">Bookmark link</a>.</p><a name="bookmark=id.2xcytpi"></a><p id="table-1">Table 1: FFE state funding allocations</p>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_links(soup)
        expected = '<p><a href="#__bookmark=id.2xcytpi">Bookmark link</a>.</p><a name="bookmark=id.2xcytpi"></a><p id="table-1">Table 1: FFE state funding allocations</p>'
        self.assertEqual(str(soup), expected)

    def test_empty_anchor_with_matching_link_followed_by_paragraph_keeps_existing_class(
        self,
    ):
        html = '<p><a href="#bookmark=id.2xcytpi">Bookmark link</a>.</p><a id="bookmark=id.2xcytpi"></a><p class="table-caption" id="table-1">Table 1: FFE state funding allocations</p>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_links(soup)
        expected = '<p><a href="#bookmark=id.2xcytpi">Bookmark link</a>.</p><p class="table-caption bookmark" id="bookmark=id.2xcytpi">Table 1: FFE state funding allocations</p>'
        self.assertEqual(str(soup), expected)

    def test_empty_anchor_with_matching_link_followed_by_a_SPAN(self):
        html = '<p><a href="#bookmark=id.2xcytpi">Bookmark link</a>.</p><a id="bookmark=id.2xcytpi"></a><span>Table 1: FFE state funding allocations</span>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_links(soup)
        self.assertEqual(str(soup), html)

    def test_empty_anchor_WITHOUT_matching_link_followed_by_a_paragraph(self):
        html = '<p><a href="#bookmark=id.abc123">Bookmark link</a>.</p><a id="bookmark=id.2xcytpi"></a><p>Table 1: FFE state funding allocations</p>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_links(soup)
        expected = '<p><a href="#__bookmark=id.abc123">Bookmark link</a>.</p><a id="bookmark=id.2xcytpi"></a><p>Table 1: FFE state funding allocations</p>'
        self.assertEqual(str(soup), expected)

    def test_empty_anchor_with_matching_link_with_NO_subsequent_element(self):
        html = '<p><a href="#bookmark=id.2xcytpi">Bookmark link</a>.</p><a id="bookmark=id.2xcytpi"></a>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_links(soup)
        self.assertEqual(str(soup), html)

    def test_empty_anchor_with_matching_link_followed_by_paragraph_NO_BOOKMARK(self):
        html = '<p><a href="#id.2xcytpi">Bookmark link</a>.</p><a id="id.2xcytpi"></a><p>Table 1: FFE state funding allocations</p>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_links(soup)
        self.assertEqual(str(soup), html)

    def test_NONempty_anchor_with_matching_link_followed_by_paragraph(self):
        html = '<p><a href="#bookmark=id.2xcytpi">Bookmark link</a>.</p><a id="bookmark=id.2xcytpi">Bookmark</a><p>Table 1: FFE state funding allocations</p>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_links(soup)
        self.assertEqual(str(soup), html)


class PreserveBookmarkTargetsTest(TestCase):
    def test_empty_anchor_with_id_transfers_to_parent(self):
        html = '<p>This is a paragraph with an empty <a id="bookmark1"></a> link.</p>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_targets(soup)
        expected = (
            '<p id="nb_bookmark_bookmark1">This is a paragraph with an empty  link.</p>'
        )
        self.assertEqual(str(soup), expected)

    def test_empty_anchor_with_id_and_whitespace_transfers_to_parent(self):
        html = '<p>This is a paragraph with an empty <a id="bookmark1"> </a> link.</p>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_targets(soup)
        expected = (
            '<p id="nb_bookmark_bookmark1">This is a paragraph with an empty  link.</p>'
        )
        self.assertEqual(str(soup), expected)

    def test_empty_anchor_with_matching_href(self):
        html = '<p>Some text and a <a id="bookmark1"></a> link.</p><a href="#bookmark1">Reference link</a>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_targets(soup)
        expected = '<p id="nb_bookmark_bookmark1">Some text and a  link.</p><a href="#nb_bookmark_bookmark1">Reference link</a>'
        self.assertEqual(str(soup), expected)

    def test_ignore_anchor_with_underscore_prefix(self):
        html = '<p>Paragraph with <a id="_internal"></a> internal bookmark.</p>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_targets(soup)
        # No changes expected since the id starts with an underscore
        expected = '<p>Paragraph with <a id="_internal"></a> internal bookmark.</p>'
        self.assertEqual(str(soup), expected)

    def test_parent_already_has_id(self):
        html = '<p id="existing-id">Paragraph with <a id="bookmark2"></a> an empty link.</p>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_targets(soup)
        # Expect that the id is not copied to the parent, and the <a> tag is removed
        expected = '<p id="existing-id">Paragraph with <a id="nb_bookmark_bookmark2"></a> an empty link.</p>'
        self.assertEqual(str(soup), expected)

    def test_parent_already_has_id_but_links_are_changed(self):
        html = '<p>Text with a <a href="#bookmark2">reference link</a>.</p><p id="existing-id">Paragraph with <a id="bookmark2"></a> an empty link.</p>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_targets(soup)
        # Expect that the href changes as does the original id, but the id of the parent p element does not change
        expected = '<p>Text with a <a href="#nb_bookmark_bookmark2">reference link</a>.</p><p id="existing-id">Paragraph with <a id="nb_bookmark_bookmark2"></a> an empty link.</p>'
        self.assertEqual(str(soup), expected)

    def test_multiple_empty_anchors(self):
        html = '<p><a id="bookmark1"></a> First bookmark.</p><p><a id="bookmark2"></a> Second bookmark.</p>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_targets(soup)
        expected = '<p id="nb_bookmark_bookmark1"> First bookmark.</p><p id="nb_bookmark_bookmark2"> Second bookmark.</p>'
        self.assertEqual(str(soup), expected)


class PreserveHeadingLinksTest(TestCase):
    def test_empty_anchor_with_heading_id(self):
        html = '<h4><a id="_heading=h.3rdcrjn"></a>About priority populations</h4>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = '<h4 id="_heading=h.3rdcrjn">About priority populations</h4>'
        self.assertEqual(result, expected)

    def test_empty_anchor_with_heading_id_wipes_out_existing_id(self):
        html = '<h4 id="about-priority-populations"><a id="_heading=h.3rdcrjn"></a>About priority populations</h4>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = '<h4 id="_heading=h.3rdcrjn">About priority populations</h4>'
        self.assertEqual(result, expected)

    def test_empty_anchor_with_heading_id_wipes_out_existing_id_but_changes_old_href(
        self,
    ):
        html = '<div><h4 id="about-priority-populations"><a id="_heading=h.3rdcrjn"></a>About priority populations</h4><p>Learn <a href="#about-priority-populations">about them</a></p></div>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = '<div><h4 id="_heading=h.3rdcrjn">About priority populations</h4><p>Learn <a href="#_heading=h.3rdcrjn">about them</a></p></div>'
        self.assertEqual(result, expected)

    def test_empty_anchor_with_name_does_not_change_heading_id(
        self,
    ):
        html = '<h4><a name="_heading=h.3rdcrjn"></a>About priority populations</h4>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = (
            '<h4><a name="_heading=h.3rdcrjn"></a>About priority populations</h4>'
        )
        self.assertEqual(result, expected)

    def test_non_empty_anchor_with_heading_id(self):
        html = '<h4><a id="_heading=h.3rdcrjn">Link text</a>About priority populations</h4>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = '<h4><a id="_heading=h.3rdcrjn">Link text</a>About priority populations</h4>'
        self.assertEqual(result, expected)

    def test_empty_anchor_without_underscore_id(self):
        html = '<h4><a id="other_id"></a>About priority populations</h4>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = '<h4 id="other_id">About priority populations</h4>'
        self.assertEqual(result, expected)

    def test_empty_anchor_inside_of_a_non_header(self):
        html = '<p><a id="_heading=about_priority_populations"></a>About priority populations</p>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        self.assertEqual(result, html)

    def test_no_anchor_tag(self):
        html = "<h4>About priority populations</h4>"
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = "<h4>About priority populations</h4>"
        self.assertEqual(result, expected)

    def test_multiple_empty_anchors_with_heading_id(self):
        html = """
        <h4><a id="_heading=h.1"></a>Heading 1</h4>\n<h4><a id="_heading=h.2"></a>Heading 2</h4>
        """
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = """
        <h4 id="_heading=h.1">Heading 1</h4>\n<h4 id="_heading=h.2">Heading 2</h4>
        """
        self.assertEqual(result.strip(), expected.strip())

    def test_mixed_anchors_with_heading_id(self):
        html = """
        <h4><a id="_heading=h.1"></a>Heading 1</h4>\n<h4><a id="_heading=h.2">Link text</a>Heading 2</h4>
        """
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = """
        <h4 id="_heading=h.1">Heading 1</h4>\n<h4><a id="_heading=h.2">Link text</a>Heading 2</h4>
        """
        self.assertEqual(result.strip(), expected.strip())

    def test_empty_anchor_preceding_heading_id(self):
        html = '<a id="_About_Priority_Populations"></a><h4>About priority populations</h4>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = (
            '<h4 id="_About_Priority_Populations">About priority populations</h4>'
        )
        self.assertEqual(result, expected)

    def test_empty_anchor_preceding_heading_id_wipes_out_existing_id(self):
        html = '<a id="_About_Priority_Populations"></a><h4 id="h4_heading">About priority populations</h4>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = (
            '<h4 id="_About_Priority_Populations">About priority populations</h4>'
        )
        self.assertEqual(result, expected)

    def test_empty_anchor_preceding_heading_id_wipes_out_existing_id_but_keeps_old_href(
        self,
    ):
        html = '<a id="_About_Priority_Populations"></a><h4 id="h4_heading">About priority populations</h4><a href="#h4_heading">Link to h4</a>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = '<h4 id="_About_Priority_Populations">About priority populations</h4><a href="#_About_Priority_Populations">Link to h4</a>'
        self.assertEqual(result, expected)

    def test_empty_anchor_with_name_preceding_heading_id_does_not_change_heading_id(
        self,
    ):
        html = '<a name="_About_Priority_Populations"></a><h4>About priority populations</h4>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        self.assertEqual(result, html)

    def test_non_empty_anchor_preceding_heading_id_does_not_change_heading_id(
        self,
    ):
        html = '<a id="_About_Priority_Populations">Title: </a><h4>About priority populations</h4>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        self.assertEqual(result, html)

    def test_empty_anchor_not_preceding_heading_id(self):
        html = '<a id="_About_Priority_Populations"></a><p>Hello</p><h4>About priority populations</h4>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        self.assertEqual(result, html)

    def test_two_empty_anchors_preceding_heading_id(
        self,
    ):
        html = '<a id="_About_Priority_Populations_1"></a><a id="_About_Priority_Populations_2"></a><h4>About priority populations</h4><p><a href="#_About_Priority_Populations_1">About 1</a></p><p><a href="#_About_Priority_Populations_2">About 2</a></p>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = '<h4 id="_About_Priority_Populations_2">About priority populations</h4><p><a href="#_About_Priority_Populations_2">About 1</a></p><p><a href="#_About_Priority_Populations_2">About 2</a></p>'
        self.assertEqual(result, expected)

    def test_three_empty_anchors_preceding_heading_id(
        self,
    ):
        html = '<a id="_About_Priority_Populations_1"></a><a id="_About_Priority_Populations_2"></a><a id="_About_Priority_Populations_3"></a><h4>About priority populations</h4><p><a href="#_About_Priority_Populations_1">About 1</a></p><p><a href="#_About_Priority_Populations_2">About 2</a></p><p><a href="#_About_Priority_Populations_3">About 3</a></p>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = '<h4 id="_About_Priority_Populations_3">About priority populations</h4><p><a href="#_About_Priority_Populations_3">About 1</a></p><p><a href="#_About_Priority_Populations_3">About 2</a></p><p><a href="#_About_Priority_Populations_3">About 3</a></p>'
        self.assertEqual(result, expected)

    def test_empty_anchor_preceding_heading_id_and_inside_heading_only_uses_inside(
        self,
    ):
        html = '<a id="_About_Priority_Populations_preceding"></a><h4><a id="_About_Priority_Populations_inside"></a>About priority populations</h4>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = '<h4 id="_About_Priority_Populations_inside">About priority populations</h4>'
        self.assertEqual(result, expected)

    def test_empty_anchor_preceding_heading_id_and_inside_heading_only_uses_inside_all_links_preserved(
        self,
    ):
        html = '<a id="_About_Priority_Populations_preceding"></a><h4 id="_About_Priority_Populations_h4"><a id="_About_Priority_Populations_inside"></a>About priority populations</h4><a href="#_About_Priority_Populations_h4">Link to h4</a><a href="#_About_Priority_Populations_preceding">Link to preceding</a><a href="#_About_Priority_Populations_inside">Link to inside</a>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = '<h4 id="_About_Priority_Populations_inside">About priority populations</h4><a href="#_About_Priority_Populations_inside">Link to h4</a><a href="#_About_Priority_Populations_inside">Link to preceding</a><a href="#_About_Priority_Populations_inside">Link to inside</a>'
        self.assertEqual(result, expected)

    def test_h7_with_direct_child_anchor_transfers_id_and_removes_anchor(
        self,
    ):
        """H7 heading with a direct child anchor should get the anchor's ID and remove the anchor."""
        html = '<div role="heading" aria-level="7"><a id="h7-direct-link"></a>Some H7 Heading Text</div>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = '<div aria-level="7" id="h7-direct-link" role="heading">Some H7 Heading Text</div>'
        self.assertEqual(result, expected)

    def test_h7_with_preceding_anchor_transfers_id_and_removes_anchor(
        self,
    ):
        """H7 heading with a preceding anchor should get the anchor's ID and remove the anchor."""
        html = '<a id="h7-preceding-link"></a><div role="heading" aria-level="7">Some H7 Heading Text</div>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = '<div aria-level="7" id="h7-preceding-link" role="heading">Some H7 Heading Text</div>'
        self.assertEqual(result, expected)

    def test_regular_div_ignores_preceding_anchor(
        self,
    ):
        """Regular div without heading role should not get ID from preceding anchor."""
        html = '<a id="some-link"></a><div>Regular div content</div>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = '<a id="some-link"></a><div>Regular div content</div>'
        self.assertEqual(result, expected)


class PreserveTableHeadingLinksTest(TestCase):
    def test_empty_anchor_with_table_heading_id(self):
        html = '<p><a id="Table5"></a>About priority populations</p><table></table>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_table_heading_links(soup)
        result = str(soup)
        expected = '<p id="table-heading--Table5">About priority populations</p><table></table>'
        self.assertEqual(result, expected)

    def test_empty_anchor_with_whitespace_with_table_heading_id(self):
        html = '<p><a id="Table5"> </a>About priority populations</p><table></table>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_table_heading_links(soup)
        result = str(soup)
        expected = '<p id="table-heading--Table5">About priority populations</p><table></table>'
        self.assertEqual(result, expected)

    def test_empty_anchor_with_table_heading_id_wipes_out_existing_id(self):
        html = '<p id="priority-populations"><a id="Table5"></a>About priority populations</p><table></table>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_table_heading_links(soup)
        result = str(soup)
        expected = '<p id="table-heading--Table5">About priority populations</p><table></table>'
        self.assertEqual(result, expected)

    def test_empty_anchor_with_paragraph_id_wipes_out_existing_id_and_changes_old_href(
        self,
    ):
        html = '<p id="priority-populations"><a id="Table5"></a>About priority populations</p><table></table><a href="#priority-populations">Some other heading</a>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_table_heading_links(soup)
        result = str(soup)
        expected = '<p id="table-heading--Table5">About priority populations</p><table></table><a href="#table-heading--Table5">Some other heading</a>'
        self.assertEqual(result, expected)

    def test_empty_anchor_with_table_heading_id_changes_existing_link_href(self):
        html = '<p id="priority-populations"><a id="Table5"></a>About priority populations</p><table></table><a href="#Table5">Table 5: About priority populations</a>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_table_heading_links(soup)
        result = str(soup)
        expected = '<p id="table-heading--Table5">About priority populations</p><table></table><a href="#table-heading--Table5">Table 5: About priority populations</a>'
        self.assertEqual(result, expected)

    def test_empty_anchor_with_name_does_not_become_table_heading_id(self):
        html = '<p><a name="Table5"></a>About priority populations</p><table></table>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_table_heading_links(soup)
        result = str(soup)
        self.assertEqual(result, html)

    def test_non_empty_anchor_IS_NOT_table_heading_id(self):
        html = (
            '<p><a id="Table5">Table: </a>About priority populations</p><table></table>'
        )
        soup = BeautifulSoup(html, "html.parser")
        preserve_table_heading_links(soup)
        result = str(soup)
        self.assertEqual(result, html)

    def test_empty_anchor_no_table(self):
        html = '<p><a id="Table5"></a>About priority populations</p>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_table_heading_links(soup)
        result = str(soup)
        self.assertEqual(result, html)

    def test_empty_anchor_not_before_a_table(self):
        html = '<p><a id="Table5"></a>About priority populations</p><p>Other paragraph</p><table></table>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_table_heading_links(soup)
        result = str(soup)
        self.assertEqual(result, html)

    def test_no_table_heading_id(self):
        html = "<p>About priority populations</p><table></table>"
        soup = BeautifulSoup(html, "html.parser")
        preserve_table_heading_links(soup)
        result = str(soup)
        self.assertEqual(result, html)

    def test_multiple_empty_anchors_with_table_heading_id(self):
        html = '<p><a id="Table5"></a><a id="Table6"></a><a id="Table7"></a>About priority populations</p><table></table>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_table_heading_links(soup)
        result = str(soup)
        expected = '<p id="table-heading--Table7">About priority populations</p><table></table>'
        self.assertEqual(result, expected)

    def test_multiple_empty_anchors_with_table_heading_id_preserves_existing_links(
        self,
    ):
        html = '<p><a id="Table5"></a><a id="Table6"></a><a id="Table7"></a>About priority populations</p><table></table><a href="#Table5">Table 5: About priority populations</a><a href="#Table6">Table 6: About priority populations</a><a href="#Table7">Table 7: About priority populations</a>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_table_heading_links(soup)
        result = str(soup)
        expected = '<p id="table-heading--Table7">About priority populations</p><table></table><a href="#table-heading--Table7">Table 5: About priority populations</a><a href="#table-heading--Table7">Table 6: About priority populations</a><a href="#table-heading--Table7">Table 7: About priority populations</a>'
        self.assertEqual(result, expected)

    # Test <a> tags wrapped in paragraphs
    def test_empty_anchor_wrapped_in_p_becomes_heading_id(self):
        html = '<p><a id="_About_Priority_Populations"></a></p><h4>About priority populations</h4>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = '<p></p><h4 id="_About_Priority_Populations">About priority populations</h4>'
        self.assertEqual(result, expected)

    def test_empty_anchor_within_paragraph_preceding_heading(self):
        # first ID is the one we keep
        html = """
        <p><a id="_Paper_Submissions"></a><a id="_Exemptions_for_Paper"></a></p>
        <h4>About priority populations</h4>
        """
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = """
        <p></p>\n<h4 id="_Paper_Submissions">About priority populations</h4>
        """
        self.assertEqual(result.strip(), expected.strip())

    def test_empty_anchor_in_paragraph_with_non_empty_anchor_preceding_heading_does_NOT_become_heading_id(
        self,
    ):
        html = """
        <p><a id="_Valid_ID"></a><a id="_Invalid_ID">Not empty</a></p><h4>About priority populations</h4>
        """
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        # Since one of the <a> tags is non-empty, the <p> is ignored
        self.assertEqual(result.strip(), html.strip())

    def test_multiple_paragraphs_with_empty_anchors_preceding_heading(self):
        html = """
        <p><a id="_First_ID"></a></p>
        <p><a id="_Second_ID"></a></p>
        <h4>About priority populations</h4>
        """
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        # Only the last valid <a> tag's ID is used
        expected = (
            '<p></p>\n<p></p>\n<h4 id="_Second_ID">About priority populations</h4>'
        )

        self.assertEqual(result.strip(), expected.strip())

    def test_complex_case_with_paragraph_and_multiple_anchors(self):
        html = """
        <p><a id="_Third_ID"></a><span>Other content</span></p>
        <p><a id="_First_ID"></a><a id="_Second_ID"></a></p>
        <h4><a id="_Inside_ID"></a>About priority populations</h4>
        <a href="#_First_ID">Link 1</a>
        <a href="#_Third_ID">Link 2</a>
        <a href="#_Inside_ID">Link 3</a>
        """
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        # ID inside the heading takes precedence, links should update
        # Note that the "_Third_ID" href doesn't change because the <a> tag for it is not in an empty <p>
        expected = """
        <p><a id="_Third_ID"></a><span>Other content</span></p>\n<p></p>\n<h4 id="_Inside_ID">About priority populations</h4>\n<a href="#_Inside_ID">Link 1</a>\n<a href="#_Third_ID">Link 2</a>\n<a href="#_Inside_ID">Link 3</a>
        """
        self.assertEqual(result.strip(), expected.strip())


class UnwrapNestedListsTest(TestCase):
    def test_simple_nested_list(self):
        html_content = "<ul><li><ul><li>My list</li></ul></li></ul>"
        soup = BeautifulSoup(html_content, "html.parser")
        unwrap_nested_lists(soup)
        expected_output = "<ul><li>My list</li></ul>"
        self.assertEqual(str(soup).strip(), expected_output.strip())

    def test_complex_nested_list(self):
        html_content = "<ul><li><ul><li><ul><li><ul><li>My item 1</li><li>My item 2</li></ul></li></ul></li></ul></li></ul>"
        soup = BeautifulSoup(html_content, "html.parser")
        unwrap_nested_lists(soup)
        expected_output = "<ul><li>My item 1</li><li>My item 2</li></ul>"
        self.assertEqual(str(soup).strip(), expected_output.strip())

    def test_mixed_content_li_list(self):
        html_content = "<ul><li>Address at least one of the following priority areas:<ul><li>Built environment and housing instability</li><li>Community-clinical linkages</li><li>Food and nutrition security</li></ul></li></ul>"
        soup = BeautifulSoup(html_content, "html.parser")
        unwrap_nested_lists(soup)
        expected_output = "<ul><li>My item 1</li><li>My item 2</li></ul>"
        self.assertEqual(str(soup).strip(), html_content.strip())

    def test_multiple_nested_lists(self):
        html_content = "<ul><li><ul><li><ul><li>Item 1</li></ul></li></ul></li><li>List 2:<ul><li><ul><li>Item 2.1</li></ul></li></ul></li><li><ul><li><ul><li>Item 3</li></ul></li></ul></li></ul>"
        soup = BeautifulSoup(html_content, "html.parser")
        unwrap_nested_lists(soup)
        expected_output = "<ul><li>Item 1</li><li>List 2:<ul><li>Item 2.1</li></ul></li><li>Item 3</li></ul>"
        self.assertEqual(str(soup).strip(), expected_output.strip())


###########################################################
################### NESTED LIST TESTS #####################
###########################################################


class NestedListTestsULandOL(TestCase):
    def setUp(self):
        # ol > ul > ul
        # ol > ul > ol

        self.html_ul_ol = """
            <h6 class="c27" id="h.3rdcrjn"><span class="c77 c54">Strategy 1A – Health education (HED)</span></h6>
            <p class="c9"><span class="c4">You will implement a technical assistance plan and provide professional development to support the delivery of quality health education through the following activities:</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">HED1. Develop, implement, and review a technical assistance plan. Its goal is to support and improve teacher and school staff’s knowledge, comfort, and skills for delivering health education to students in secondary grades (6 to 12). This includes sexual and mental health education.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HED2. Each year, provide professional development for teachers and school staff delivering health education instructional programs to students in secondary grades (6 to 12). This includes sexual health and mental health education. Prioritize instructional competencies needed for culturally responsive and inclusive education.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HED3. Each year, implement a health education instructional program for students in grades K to 12. Health education instructional programs should: </span></li>
            </ul>
            <ol class="c7 lst-kix_ve93wcml2fgp-1 start" start="1">
                <li class="c33 li-bullet-0"><span class="c2 c0">If previous program recipient, does the application clearly articulate how previously funded program activities and outcomes impacted the state dementia-capable system and the need for additional resources?</span></li>
            </ol>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

        self.html_ul_ol_ol = """
            <h6 class="c27" id="h.3rdcrjn"><span class="c77 c54">Strategy 1A – Health education (HED)</span></h6>
            <p class="c9"><span class="c4">You will implement a technical assistance plan and provide professional development to support the delivery of quality health education through the following activities:</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">HED1. Develop, implement, and review a technical assistance plan. Its goal is to support and improve teacher and school staff’s knowledge, comfort, and skills for delivering health education to students in secondary grades (6 to 12). This includes sexual and mental health education.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HED2. Each year, provide professional development for teachers and school staff delivering health education instructional programs to students in secondary grades (6 to 12). This includes sexual health and mental health education. Prioritize instructional competencies needed for culturally responsive and inclusive education.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HED3. Each year, implement a health education instructional program for students in grades K to 12. Health education instructional programs should: </span></li>
            </ul>
            <ol class="c7 lst-kix_ve93wcml2fgp-1 start" start="1">
                <li class="c33 li-bullet-0"><span class="c2 c0">If previous program recipient, does the application clearly articulate how previously funded program activities and outcomes impacted the state dementia-capable system and the need for additional resources?</span></li>
            </ol>
            <ol class="c7 lst-kix_l7y75dh7i3nd-2 start" start="1">
                <li class="c36 c77 li-bullet-0"><span class="c2 c0">If a previously funded recipient, does the applicant describe the targeted population before and after the earlier funding, as well as the present-day population in the community? </span></li>
            </ol>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

        self.html_ul_ol_ul = """
            <h6 class="c27" id="h.3rdcrjn"><span class="c77 c54">Strategy 1A – Health education (HED)</span></h6>
            <p class="c9"><span class="c4">You will implement a technical assistance plan and provide professional development to support the delivery of quality health education through the following activities:</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">HED1. Develop, implement, and review a technical assistance plan. Its goal is to support and improve teacher and school staff’s knowledge, comfort, and skills for delivering health education to students in secondary grades (6 to 12). This includes sexual and mental health education.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HED2. Each year, provide professional development for teachers and school staff delivering health education instructional programs to students in secondary grades (6 to 12). This includes sexual health and mental health education. Prioritize instructional competencies needed for culturally responsive and inclusive education.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HED3. Each year, implement a health education instructional program for students in grades K to 12. Health education instructional programs should: </span></li>
            </ul>
            <ol class="c7 lst-kix_ve93wcml2fgp-1 start" start="1">
                <li class="c33 li-bullet-0"><span class="c2 c0">If previous program recipient, does the application clearly articulate how previously funded program activities and outcomes impacted the state dementia-capable system and the need for additional resources?</span></li>
            </ol>
            <ul class="c34 lst-kix_list_22-0 start">
                <li class="c9 c80 li-bullet-0"><span class="c4">Staff who provide health services, and </span></li>
                <li class="c9 c80 li-bullet-0"><span class="c4">Other school staff</span></li>
            </ul>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

        self.html_ol_ul = """
            <h6 class="c27" id="h.3rdcrjn"><span class="c77 c54">Strategy 1A – Health education (HED)</span></h6>
            <p class="c9"><span class="c4">You will implement a technical assistance plan and provide professional development to support the delivery of quality health education through the following activities:</span></p>
            <ol class="c7 lst-kix_ve93wcml2fgp-0 start" start="1">
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant demonstrate capacity to deliver and enhance person-centered, strengths-based services for people of all ages with dementia?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear description of the need for dementia-capability in the state system for the population it serves?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear understanding of the dementia capability of the system within which they are operating?</span></li>
            </ol>
            <ul class="c34 lst-kix_list_22-0 start">
                <li class="c9 c80 li-bullet-0"><span class="c4">Staff who provide health services, and </span></li>
                <li class="c9 c80 li-bullet-0"><span class="c4">Other school staff</span></li>
            </ul>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

        self.html_ol_ul_ul = """
            <h6 class="c27" id="h.3rdcrjn"><span class="c77 c54">Strategy 1A – Health education (HED)</span></h6>
            <p class="c9"><span class="c4">You will implement a technical assistance plan and provide professional development to support the delivery of quality health education through the following activities:</span></p>
            <ol class="c7 lst-kix_ve93wcml2fgp-0 start" start="1">
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant demonstrate capacity to deliver and enhance person-centered, strengths-based services for people of all ages with dementia?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear description of the need for dementia-capability in the state system for the population it serves?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear understanding of the dementia capability of the system within which they are operating?</span></li>
            </ol>
            <ul class="c34 lst-kix_list_22-0 start">
                <li class="c9 c80 li-bullet-0"><span class="c4">Staff who provide health services, and </span></li>
                <li class="c9 c80 li-bullet-0"><span class="c4">Other school staff</span></li>
            </ul>
            <ul class="c34 lst-kix_list_13-1 start">
                <li class="c91 c143 li-bullet-0"><span class="c4">Setting positive behavioral expectations for students</span></li>
            </ul>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

        self.html_ol_ul_ol = """
            <h6 class="c27" id="h.3rdcrjn"><span class="c77 c54">Strategy 1A – Health education (HED)</span></h6>
            <p class="c9"><span class="c4">You will implement a technical assistance plan and provide professional development to support the delivery of quality health education through the following activities:</span></p>
            <ol class="c7 lst-kix_ve93wcml2fgp-0 start" start="1">
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant demonstrate capacity to deliver and enhance person-centered, strengths-based services for people of all ages with dementia?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear description of the need for dementia-capability in the state system for the population it serves?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear understanding of the dementia capability of the system within which they are operating?</span></li>
            </ol>
            <ul class="c34 lst-kix_list_22-0 start">
                <li class="c9 c80 li-bullet-0"><span class="c4">Staff who provide health services, and </span></li>
                <li class="c9 c80 li-bullet-0"><span class="c4">Other school staff</span></li>
            </ul>
            <ol class="c7 lst-kix_l7y75dh7i3nd-2 start" start="1">
                <li class="c36 c77 li-bullet-0"><span class="c2 c0">If a previously funded recipient, does the applicant describe the targeted population before and after the earlier funding, as well as the present-day population in the community? </span></li>
            </ol>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

    def test_ul_ol(self):
        soup = join_nested_lists(BeautifulSoup(self.html_ul_ol, "html.parser"))
        self.assertEqual(len(soup.select("ul")), 1)

        # ol is nested list
        self.assertEqual(len(soup.select("ul > li > ol")), 1)

        # last li of first list HAS a nested ol
        last_li = soup.find("ul").find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ol")), 1)

    def test_ul_ol_ol(self):
        soup = join_nested_lists(BeautifulSoup(self.html_ul_ol_ol, "html.parser"))
        self.assertEqual(len(soup.select("ul")), 1)

        # ol is nested list
        self.assertEqual(len(soup.select("ul > li > ol")), 1)

        # 2nd ol is nested list
        self.assertEqual(len(soup.select("ul > li > ol > li > ol")), 1)

        # last li of first list HAS 2 nested ols
        last_li = soup.find("ul").find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ol")), 2)

    def test_ul_ol_ul(self):
        soup = join_nested_lists(BeautifulSoup(self.html_ul_ol_ul, "html.parser"))
        self.assertEqual(len(soup.select("ul")), 2)

        # ol is nested list
        self.assertEqual(len(soup.select("ul > li > ol")), 1)

        # 2nd ol is nested list
        self.assertEqual(len(soup.select("ul > li > ol > li > ul")), 1)

        # last li of first list HAS 1 nested ol and 1 nested ul
        last_li = soup.find("ul").find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ol")), 1)
        self.assertEqual(len(last_li.find_all("ul")), 1)

    def test_ol_ul(self):
        soup = join_nested_lists(BeautifulSoup(self.html_ol_ul, "html.parser"))
        self.assertEqual(len(soup.select("ol")), 1)

        # ul is nested list
        self.assertEqual(len(soup.select("ol > li > ul")), 1)

        # last li of first list HAS a nested ul
        last_li = soup.find("ol").find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ul")), 1)

    def test_ol_ul_ul(self):
        soup = join_nested_lists(BeautifulSoup(self.html_ol_ul_ul, "html.parser"))
        self.assertEqual(len(soup.select("ol")), 1)

        # ul is nested list
        self.assertEqual(len(soup.select("ol > li > ul")), 1)

        # 2nd ul is nested list
        self.assertEqual(len(soup.select("ol > li > ul > li > ul")), 1)

        # last li of first list HAS 2 nested uls
        last_li = soup.find("ol").find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ul")), 2)

    def test_ol_ul_ol(self):
        soup = join_nested_lists(BeautifulSoup(self.html_ol_ul_ol, "html.parser"))
        self.assertEqual(len(soup.select("ol")), 2)

        # ul is nested list
        self.assertEqual(len(soup.select("ol > li > ul")), 1)

        # 2nd ol is nested list
        self.assertEqual(len(soup.select("ol > li > ul > li > ol")), 1)

        # last li of first list HAS a nested ul and nested ol
        last_li = soup.find("ol").find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ul")), 1)
        self.assertEqual(len(last_li.find_all("ol")), 1)


class NestedListTestsUL(TestCase):
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


class NestedListTestsOL(TestCase):
    def setUp(self):
        self.html_single_list_ol = """
            <h6 class="c102" id="h.qsh70q"><span class="c10 c95">Option A (State)</span></h6>
            <ol class="c7 lst-kix_ve93wcml2fgp-0 start" start="1">
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant demonstrate capacity to deliver and enhance person-centered, strengths-based services for people of all ages with dementia?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear description of the need for dementia-capability in the state system for the population it serves?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear understanding of the dementia capability of the system within which they are operating?</span></li>
            </ol>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

        self.html_nested_list_ol = """
            <h6 class="c102" id="h.qsh70q"><span class="c10 c95">Option A (State)</span></h6>
            <ol class="c7 lst-kix_ve93wcml2fgp-0 start" start="1">
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant demonstrate capacity to deliver and enhance person-centered, strengths-based services for people of all ages with dementia?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear description of the need for dementia-capability in the state system for the population it serves?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear understanding of the dementia capability of the system within which they are operating?</span></li>
            </ol>
            <ol class="c7 lst-kix_ve93wcml2fgp-1 start" start="1">
                <li class="c33 li-bullet-0"><span class="c2 c0">If previous program recipient, does the application clearly articulate how previously funded program activities and outcomes impacted the state dementia-capable system and the need for additional resources?</span></li>
            </ol>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

        self.html_nested_list_ol_followed_by_li = """
            <h6 class="c102" id="h.qsh70q"><span class="c10 c95">Option A (State)</span></h6>
            <ol class="c7 lst-kix_ve93wcml2fgp-0 start" start="1">
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant demonstrate capacity to deliver and enhance person-centered, strengths-based services for people of all ages with dementia?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear description of the need for dementia-capability in the state system for the population it serves?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear understanding of the dementia capability of the system within which they are operating?</span></li>
            </ol>
            <ol class="c7 lst-kix_ve93wcml2fgp-1 start" start="1">
                <li class="c33 li-bullet-0"><span class="c2 c0">If previous program recipient, does the application clearly articulate how previously funded program activities and outcomes impacted the state dementia-capable system and the need for additional resources?</span></li>
            </ol>
            <ol class="c7 lst-kix_ve93wcml2fgp-0" start="4">
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the proposed project clearly and adequately identify the relevance of the priority areas, as described in this NOFO, in relation to current state/community needs?</span></li>
            </ol>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

        self.html_2_nested_lists_ol = """
            <h6 class="c102" id="h.qsh70q"><span class="c10 c95">Option A (State)</span></h6>
            <ol class="c7 lst-kix_ve93wcml2fgp-0 start" start="1">
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant demonstrate capacity to deliver and enhance person-centered, strengths-based services for people of all ages with dementia?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear description of the need for dementia-capability in the state system for the population it serves?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear understanding of the dementia capability of the system within which they are operating?</span></li>
            </ol>
            <ol class="c7 lst-kix_ve93wcml2fgp-1 start" start="1">
                <li class="c33 li-bullet-0"><span class="c2 c0">If previous program recipient, does the application clearly articulate how previously funded program activities and outcomes impacted the state dementia-capable system and the need for additional resources?</span></li>
            </ol>
            <ol class="c7 lst-kix_ve93wcml2fgp-0" start="4">
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the proposed project clearly and adequately identify the relevance of the priority areas, as described in this NOFO, in relation to current state/community needs?</span></li>
            </ol>
            <ol class="c7 lst-kix_ve93wcml2fgp-1 start" start="1">
                <li class="c33 li-bullet-0"><span class="c2 c0">If previous program recipient, does the applicant clearly articulate how previously funded program activities and outcomes impacted the priority areas and the current state of the priority areas?</span></li>
            </ol>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

        self.html_2_nested_lists_ol_followed_by_li = """
            <h6 class="c102" id="h.qsh70q"><span class="c10 c95">Option A (State)</span></h6>
            <ol class="c7 lst-kix_ve93wcml2fgp-0 start" start="1">
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant demonstrate capacity to deliver and enhance person-centered, strengths-based services for people of all ages with dementia?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear description of the need for dementia-capability in the state system for the population it serves?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear understanding of the dementia capability of the system within which they are operating?</span></li>
            </ol>
            <ol class="c7 lst-kix_ve93wcml2fgp-1 start" start="1">
                <li class="c33 li-bullet-0"><span class="c2 c0">If previous program recipient, does the application clearly articulate how previously funded program activities and outcomes impacted the state dementia-capable system and the need for additional resources?</span></li>
            </ol>
            <ol class="c7 lst-kix_ve93wcml2fgp-0" start="4">
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the proposed project clearly and adequately identify the relevance of the priority areas, as described in this NOFO, in relation to current state/community needs?</span></li>
            </ol>
            <ol class="c7 lst-kix_ve93wcml2fgp-1 start" start="1">
                <li class="c33 li-bullet-0"><span class="c2 c0">If previous program recipient, does the applicant clearly articulate how previously funded program activities and outcomes impacted the priority areas and the current state of the priority areas?</span></li>
            </ol>
            <ol class="c7 lst-kix_ve93wcml2fgp-0" start="5">
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant adequately and appropriately describe and document the key problem(s)/condition(s) relevant to the applicant’s purpose/need?</span></li>
            </ol>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

        self.html_double_nested_list_ol = """
            <h6 class="c102" id="h.qsh70q"><span class="c10 c95">Option A (State)</span></h6>
            <ol class="c7 lst-kix_ve93wcml2fgp-0 start" start="1">
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant demonstrate capacity to deliver and enhance person-centered, strengths-based services for people of all ages with dementia?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear description of the need for dementia-capability in the state system for the population it serves?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear understanding of the dementia capability of the system within which they are operating?</span></li>
            </ol>
            <ol class="c7 lst-kix_ve93wcml2fgp-1 start" start="1">
                <li class="c33 li-bullet-0"><span class="c2 c0">If previous program recipient, does the application clearly articulate how previously funded program activities and outcomes impacted the state dementia-capable system and the need for additional resources?</span></li>
            </ol>
            <ol class="c7 lst-kix_l7y75dh7i3nd-2 start" start="1">
                <li class="c36 c77 li-bullet-0"><span class="c2 c0">If a previously funded recipient, does the applicant describe the targeted population before and after the earlier funding, as well as the present-day population in the community? </span></li>
            </ol>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

        self.html_double_nested_list_ol_followed_by_li = """
            <h6 class="c102" id="h.qsh70q"><span class="c10 c95">Option A (State)</span></h6>
            <ol class="c7 lst-kix_ve93wcml2fgp-0 start" start="1">
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant demonstrate capacity to deliver and enhance person-centered, strengths-based services for people of all ages with dementia?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear description of the need for dementia-capability in the state system for the population it serves?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear understanding of the dementia capability of the system within which they are operating?</span></li>
            </ol>
            <ol class="c7 lst-kix_ve93wcml2fgp-1 start" start="1">
                <li class="c33 li-bullet-0"><span class="c2 c0">If previous program recipient, does the application clearly articulate how previously funded program activities and outcomes impacted the state dementia-capable system and the need for additional resources?</span></li>
            </ol>
            <ol class="c7 lst-kix_l7y75dh7i3nd-2 start" start="1">
                <li class="c36 c77 li-bullet-0"><span class="c2 c0">If a previously funded recipient, does the applicant describe the targeted population before and after the earlier funding, as well as the present-day population in the community? </span></li>
            </ol>
            <ol class="c7 lst-kix_ve93wcml2fgp-0" start="5">
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant adequately and appropriately describe and document the key problem(s)/condition(s) relevant to the applicant’s purpose/need?</span></li>
            </ol>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

        self.html_2_lists_ol_to_join = """
            <h6 class="c102" id="h.qsh70q"><span class="c10 c95">Option A (State)</span></h6>
            <ol class="c7 lst-kix_ve93wcml2fgp-0 start" start="1">
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant demonstrate capacity to deliver and enhance person-centered, strengths-based services for people of all ages with dementia?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear description of the need for dementia-capability in the state system for the population it serves?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear understanding of the dementia capability of the system within which they are operating?</span></li>
            </ol>
            <ol class="c7 lst-kix_ve93wcml2fgp-0" start="4">
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the proposed project clearly and adequately identify the relevance of the priority areas, as described in this NOFO, in relation to current state/community needs?</span></li>
            </ol>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

        self.html_2_nested_lists_ol_to_join = """
            <h6 class="c102" id="h.qsh70q"><span class="c10 c95">Option A (State)</span></h6>
            <ol class="c7 lst-kix_ve93wcml2fgp-0 start" start="1">
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant demonstrate capacity to deliver and enhance person-centered, strengths-based services for people of all ages with dementia?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear description of the need for dementia-capability in the state system for the population it serves?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear understanding of the dementia capability of the system within which they are operating?</span></li>
            </ol>
            <ol class="c7 lst-kix_ve93wcml2fgp-1 start" start="1">
                <li class="c33 li-bullet-0"><span class="c2 c0">If previous program recipient, does the application clearly articulate how previously funded program activities and outcomes impacted the state dementia-capable system and the need for additional resources?</span></li>
            </ol>
            <ol class="c7 lst-kix_ve93wcml2fgp-1 start" start="2">
                <li class="c33 li-bullet-0"><span class="c2 c0">If previous program recipient, does the applicant clearly articulate how previously funded program activities and outcomes impacted the priority areas and the current state of the priority areas?</span></li>
            </ol>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

        self.html_2_nested_lists_ol_to_join_after_double_nested_list = """
            <h6 class="c102" id="h.qsh70q"><span class="c10 c95">Option A (State)</span></h6>
            <ol class="c7 lst-kix_ve93wcml2fgp-0 start" start="1">
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant demonstrate capacity to deliver and enhance person-centered, strengths-based services for people of all ages with dementia?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear description of the need for dementia-capability in the state system for the population it serves?</span></li>
                <li class="c5 li-bullet-0"><span class="c2 c0">Does the applicant provide a clear understanding of the dementia capability of the system within which they are operating?</span></li>
            </ol>
            <ol class="c7 lst-kix_ve93wcml2fgp-1 start" start="1">
                <li class="c33 li-bullet-0"><span class="c2 c0">If previous program recipient, does the application clearly articulate how previously funded program activities and outcomes impacted the state dementia-capable system and the need for additional resources?</span></li>
            </ol>
            <ol class="c7 lst-kix_l7y75dh7i3nd-2 start" start="1">
                <li class="c36 c77 li-bullet-0"><span class="c2 c0">If a previously funded recipient, does the applicant describe the targeted population before and after the earlier funding, as well as the present-day population in the community? </span></li>
            </ol>
            <ol class="c7 lst-kix_ve93wcml2fgp-1 start" start="2">
                <li class="c33 li-bullet-0"><span class="c2 c0">If previous program recipient, does the applicant clearly articulate how previously funded program activities and outcomes impacted the priority areas and the current state of the priority areas?</span></li>
            </ol>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

    def test_single_list_nothing_happens(self):
        soup = join_nested_lists(BeautifulSoup(self.html_single_list_ol, "html.parser"))
        self.assertEqual(len(soup.select("ol")), 1)

        # last li of first list DOES NOT HAVE a nested ul
        last_li = soup.find("ol").find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ol")), 0)

    def test_nested_list_becomes_nested(self):
        soup = join_nested_lists(BeautifulSoup(self.html_nested_list_ol, "html.parser"))
        # two uls
        self.assertEqual(len(soup.select("ol")), 2)
        # one nested list
        self.assertEqual(len(soup.select("ol > li > ol")), 1)
        # no uls are siblings
        self.assertEqual(len(soup.select("ol + ol")), 0)

        # last li of first list HAS a nested ul
        last_li = soup.find("ol").find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ol")), 1)

    def test_nested_list_becomes_nested_and_last_item_added_to_first_list(self):
        soup = join_nested_lists(
            BeautifulSoup(self.html_nested_list_ol_followed_by_li, "html.parser")
        )

        # two uls
        self.assertEqual(len(soup.select("ol")), 2)
        # one nested list
        self.assertEqual(len(soup.select("ol > li > ol")), 1)
        # no uls are siblings
        self.assertEqual(len(soup.select("ol + ol")), 0)

        # first ol has 4 li children
        first_ol = soup.find("ol")
        self.assertEqual(len(first_ol.find_all("li", recursive=False)), 4)

    def test_2_nested_lists_become_nested(self):
        soup = join_nested_lists(
            BeautifulSoup(self.html_2_nested_lists_ol, "html.parser")
        )
        # three uls
        self.assertEqual(len(soup.select("ol")), 3)
        # two nested lists
        self.assertEqual(len(soup.select("ol > li > ol")), 2)
        # no ols are siblings
        self.assertEqual(len(soup.select("ol + ol")), 0)

        # first ol has 4 li children
        first_ol = soup.find("ol")
        self.assertEqual(len(first_ol.find_all("li", recursive=False)), 4)

        # last li of first list HAS a nested ol
        last_li = first_ol.find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ol")), 1)

    def test_2_nested_lists_becomes_nested_and_last_item_added_to_first_list(self):
        soup = join_nested_lists(
            BeautifulSoup(self.html_2_nested_lists_ol_followed_by_li, "html.parser")
        )
        # three ols
        self.assertEqual(len(soup.select("ol")), 3)
        # two nested lists
        self.assertEqual(len(soup.select("ol > li > ol")), 2)
        # no ols are siblings
        self.assertEqual(len(soup.select("ol + ol")), 0)

        # first ol has 5 li children
        first_ol = soup.find("ol")
        self.assertEqual(len(first_ol.find_all("li", recursive=False)), 5)

        # last li of first list DOES NOT HAVE a nested ol
        last_li = first_ol.find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ol")), 0)

    def test_double_nested_list_becomes_nested(self):
        soup = join_nested_lists(
            BeautifulSoup(self.html_double_nested_list_ol, "html.parser")
        )
        # three ols
        self.assertEqual(len(soup.select("ol")), 3)
        # two single nested lists
        self.assertEqual(len(soup.select("ol > li > ol")), 2)
        # one double nested list
        self.assertEqual(len(soup.select("ol > li > ol > li > ol")), 1)
        # no ols are siblings
        self.assertEqual(len(soup.select("ol + ol")), 0)

        # first ol has 3 li children
        first_ol = soup.find("ol")
        self.assertEqual(len(first_ol.find_all("li", recursive=False)), 3)

        # last li of first list HAS 2 ols
        last_li = first_ol.find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ol")), 2)

    def test_double_nested_list_becomes_nested_and_last_item_added_to_first_list(self):
        soup = join_nested_lists(
            BeautifulSoup(self.html_double_nested_list_ol_followed_by_li, "html.parser")
        )
        # three ols
        self.assertEqual(len(soup.select("ol")), 3)
        # two single nested lists
        self.assertEqual(len(soup.select("ol > li > ol")), 2)
        # one double nested list
        self.assertEqual(len(soup.select("ol > li > ol > li > ol")), 1)
        # no ols are siblings
        self.assertEqual(len(soup.select("ol + ol")), 0)

        # first ol has 4 li children
        first_ol = soup.find("ol")
        self.assertEqual(len(first_ol.find_all("li", recursive=False)), 4)

        # last li of first list DOES NOT HAVE ols
        last_li = first_ol.find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ol")), 0)

    def test_join_2_lists_with_same_classname(self):
        soup = join_nested_lists(
            BeautifulSoup(self.html_2_lists_ol_to_join, "html.parser")
        )
        # two ols
        self.assertEqual(len(soup.select("ol")), 1)
        # one nested list
        self.assertEqual(len(soup.select("ol > li > ol")), 0)
        # no ols are siblings
        self.assertEqual(len(soup.select("ol + ol")), 0)

        # first ol has 4 li children
        first_ol = soup.find("ol")
        self.assertEqual(len(first_ol.find_all("li", recursive=False)), 4)

    def test_join_2_nested_lists_with_same_classname(self):
        soup = join_nested_lists(
            BeautifulSoup(self.html_2_nested_lists_ol_to_join, "html.parser")
        )
        # two ols
        self.assertEqual(len(soup.select("ol")), 2)
        # one nested list
        self.assertEqual(len(soup.select("ol > li > ol")), 1)
        # no ols are siblings
        self.assertEqual(len(soup.select("ol + ol")), 0)

        # last li of first list HAS a nested ol
        last_li = soup.find("ol").find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ol")), 1)
        # nested ol has 2 lis
        self.assertEqual(len(last_li.find("ol").find_all("li")), 2)

    def test_join_2_nested_lists_with_same_classname_after_a_double_nested_list(self):
        soup = join_nested_lists(
            BeautifulSoup(
                self.html_2_nested_lists_ol_to_join_after_double_nested_list,
                "html.parser",
            )
        )
        # three ols
        self.assertEqual(len(soup.select("ol")), 3)
        # two nested lists
        self.assertEqual(len(soup.select("ol > li > ol")), 2)
        # one double nested list
        self.assertEqual(len(soup.select("ol > li > ol > li > ol")), 1)
        # no ols are siblings
        self.assertEqual(len(soup.select("ol + ol")), 0)

        # last li of first list HAS a nested ol
        last_li = soup.find("ol").find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ol")), 2)
        # nested ol has 4 lis
        self.assertEqual(len(last_li.find("ol").find_all("li", recursive=False)), 2)


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
        with open(html_filename, "r", encoding="UTF-8") as file:
            soup = BeautifulSoup(file, "html.parser")
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


class DecomposeInstructionsTablesTest(TestCase):
    def test_removes_correct_tables(self):
        """Test that tables with specific instructional text are removed."""
        html_content = """
        <html>
            <body>
                <table><tr><td><span>Instructions for NOFO writers</span><p>This table should be removed</p></td></tr></table>
                <table><tr><td>Another table that should remain.</td></tr></table>
            </body>
        </html>
        """
        soup = BeautifulSoup(html_content, "html.parser")
        decompose_instructions_tables(soup)
        remaining_tables = soup.find_all("table")
        self.assertEqual(len(remaining_tables), 1)
        self.assertNotIn(
            "Instructions for NOFO writers", remaining_tables[0].get_text()
        )

    def test_removes_correct_tables_nofo_team(self):
        """Test that tables with specific instructional text are removed."""
        html_content = """
        <html>
            <body>
                <table><tr><td><strong class="instruction-box-heading"><span>INSTRUCTIONS FOR NEW NOFO TEAM</span></strong><span>DGHP New NOFO Team: Below are three metadata fields.</span></td></tr></table>
                <table><tr><td>Another table that should remain.</td></tr></table>
            </body>
        </html>
        """
        soup = BeautifulSoup(html_content, "html.parser")
        decompose_instructions_tables(soup)
        remaining_tables = soup.find_all("table")
        self.assertEqual(len(remaining_tables), 1)
        self.assertNotIn(
            "INSTRUCTIONS FOR NEW NOFO TEAM", remaining_tables[0].get_text()
        )

    def test_removes_correct_tables_instructions_1(self):
        """Test that tables with specific instructional text are removed."""
        html_content = """
        <html>
            <body>
                <table><tr><td>DGHT-SPECIFIC INSTRUCTIONS: This table should be removed.</td></tr></table>
                <table><tr><td>PAUL-SPECIFIC INSTRUCTIONS: This table should be removed.</td></tr></table>
                <table><tr><td>SPECIFIC INSTRUCTIONS: This table should remain.</td></tr></table>
            </body>
        </html>
        """
        soup = BeautifulSoup(html_content, "html.parser")
        decompose_instructions_tables(soup)
        remaining_tables = soup.find_all("table")
        self.assertEqual(len(remaining_tables), 1)
        self.assertNotIn("-SPECIFIC INSTRUCTIONS:", remaining_tables[0].get_text())
        self.assertIn("SPECIFIC INSTRUCTIONS:", remaining_tables[0].get_text())

    def test_ignores_tables_with_2_cells(self):
        """Test that tables with specific instructional text are removed."""
        html_content = """
        <html>
            <body>
                <table><tr><td>DGHT-SPECIFIC INSTRUCTIONS: This table should not be removed.</td><td>Because it has 2 cells</td></tr></table>
                <table><tr><td>Instructions for NOFO writers: This table should be removed.</td></tr><tr><td>Because it has 2 rows and 2 cells</td></tr></table>
            </body>
        </html>
        """
        soup = BeautifulSoup(html_content, "html.parser")
        decompose_instructions_tables(soup)
        remaining_tables = soup.find_all("table")
        self.assertEqual(len(remaining_tables), 2)
        self.assertIn("-SPECIFIC INSTRUCTIONS:", remaining_tables[0].get_text())
        self.assertIn("Instructions for NOFO writers:", remaining_tables[1].get_text())

    def test_ignores_tables_without_instruction_text(self):
        """Test that tables without the specific instructional text are not removed."""
        html_content = """
        <html>
            <body>
                <table><tr><td>Some information.</td></tr></table>
                <table><tr><td>More data here.</td></tr></table>
            </body>
        </html>
        """
        soup = BeautifulSoup(html_content, "html.parser")
        decompose_instructions_tables(soup)
        remaining_tables = soup.find_all("table")
        self.assertEqual(len(remaining_tables), 2)
        self.assertIn("Some information.", remaining_tables[0].get_text())
        self.assertIn("More data here.", remaining_tables[1].get_text())

    def test_returns_removed_tables(self):
        """Test that the function returns the removed tables."""
        html_content = """
        <html>
            <body>
                <table><tr><td><span>Instructions for NOFO writers</span><p>This table should be removed</p></td></tr></table>
                <table><tr><td>Another table that should remain.</td></tr></table>
            </body>
        </html>
        """
        soup = BeautifulSoup(html_content, "html.parser")
        removed_tables = decompose_instructions_tables(soup)
        self.assertEqual(len(removed_tables), 1)
        self.assertIn("Instructions for NOFO writers", removed_tables[0].get_text())


class AddInstructionsToSubsectionsTests(TestCase):
    def test_add_instructions_to_subsections(self):
        sections = [
            {
                "subsections": [
                    {
                        "name": "Section A",
                        "body": BeautifulSoup("<p>Content A</p>", "html.parser").p,
                    },
                    {
                        "name": "Section B",
                        "body": BeautifulSoup("<p>Content B</p>", "html.parser").p,
                    },
                ]
            }
        ]

        instructions = [
            BeautifulSoup(
                "<table><tr><td><div>Instructions for NOFO writers: Section A</div><div>Do this!</div></td></tr></table>",
                "html.parser",
            ).table,
            BeautifulSoup(
                "<table><tr><td><div>Instructions for NOFO writers: Section B</div></td></tr></table>",
                "html.parser",
            ).table,
        ]

        add_instructions_to_subsections(sections, instructions)

        assert sections[0]["subsections"][0]["instructions"] == BeautifulSoup(
            "<div>Instructions for NOFO writers: Section A</div><div>Do this!</div>",
            "html.parser",
        )
        assert sections[0]["subsections"][1]["instructions"] == BeautifulSoup(
            "<div>Instructions for NOFO writers: Section B</div>", "html.parser"
        )

    def test_add_instructions_to_subsections_matches_instructions_once(self):
        sections = [
            {
                "subsections": [
                    {
                        "name": "Section A",
                        "body": BeautifulSoup("<p>Content A</p>", "html.parser").p,
                    },
                    {
                        "name": "Section A",
                        "body": BeautifulSoup("<p>Another A</p>", "html.parser").p,
                    },
                ]
            }
        ]

        instructions = [
            BeautifulSoup(
                "<table><tr><td><p>Instructions for NOFO writers: Section A</p></td></tr></table>",
                "html.parser",
            ).table
        ]

        add_instructions_to_subsections(sections, instructions)

        assert "instructions" in sections[0]["subsections"][0]
        assert "instructions" not in sections[0]["subsections"][1]

    def test_add_instructions_to_subsections_matches_subsequent_duplicates(self):
        sections = [
            {
                "subsections": [
                    {
                        "name": "Section A",
                        "body": BeautifulSoup("<p>Content A</p>", "html.parser").p,
                    },
                    {
                        "name": "Section B",
                        "body": BeautifulSoup("<p>Content B</p>", "html.parser").p,
                    },
                    {
                        "name": "Section A",
                        "body": BeautifulSoup("<p>Another A</p>", "html.parser").p,
                    },
                ]
            }
        ]

        instructions = [
            BeautifulSoup(
                "<table><tr><td>Instructions for NOFO writers: Section A</td></tr></table>",
                "html.parser",
            ).table,
            BeautifulSoup(
                "<table><tr><td>Instructions for NOFO writers: Section A</td></tr></table>",
                "html.parser",
            ),
            BeautifulSoup(
                "<table><tr><td>Instructions for NOFO writers: Section B</td></tr></table>",
                "html.parser",
            ).table,
        ]

        add_instructions_to_subsections(sections, instructions)

        assert "Section A" in sections[0]["subsections"][0]["instructions"].get_text()
        assert "Section B" in sections[0]["subsections"][1]["instructions"].get_text()
        assert "Section A" in sections[0]["subsections"][2]["instructions"].get_text()

    def test_add_instructions_to_subsections_matches_body_if_no_name(self):
        sections = [
            {
                "subsections": [
                    {
                        "name": "",
                        "body": BeautifulSoup("<p>Content A</p>", "html.parser").p,
                    },
                ]
            }
        ]

        instructions = [
            BeautifulSoup(
                "<table><tr><td>Instructions for NOFO writers: Content A</td></tr></table>",
                "html.parser",
            ).table
        ]

        add_instructions_to_subsections(sections, instructions)

        assert (
            "Instructions for NOFO writers: Content A"
            in sections[0]["subsections"][0]["instructions"].get_text()
        )


class NormalizeWhitespaceImgAltTextTests(TestCase):
    def test_replaces_double_newlines_with_single(self):
        """Ensure double newlines in img alt text are replaced with a single newline."""
        html = '<img src="turtle.jpg" alt="A turtle in a tank\n\nAI-generated content may be incorrect.">'
        soup = BeautifulSoup(html, "html.parser")

        normalize_whitespace_img_alt_text(soup)

        self.assertEqual(
            soup.find("img")["alt"],
            "A turtle in a tank\nAI-generated content may be incorrect.",
        )

    def test_does_not_modify_single_newline(self):
        """Ensure single newlines remain unchanged in img alt text."""
        html = '<img src="fish.jpg" alt="A fish in a pond\nLooking for food.">'
        soup = BeautifulSoup(html, "html.parser")

        normalize_whitespace_img_alt_text(soup)

        self.assertEqual(soup.find("img")["alt"], "A fish in a pond\nLooking for food.")

    def test_ignores_images_without_alt_text(self):
        """Ensure images without alt text remain unchanged."""
        html = '<img src="no-alt.jpg">'
        soup = BeautifulSoup(html, "html.parser")

        normalize_whitespace_img_alt_text(soup)

        self.assertIsNone(soup.find("img").get("alt"))

    def test_handles_multiple_images(self):
        """Ensure function correctly processes multiple img tags in a document."""
        html = """
        <img src="img1.jpg" alt="First image\n\nExtra info.">
        <img src="img2.jpg" alt="Second image\n\nDetails here.">
        """
        soup = BeautifulSoup(html, "html.parser")

        normalize_whitespace_img_alt_text(soup)

        img_tags = soup.find_all("img")
        self.assertEqual(img_tags[0]["alt"], "First image\nExtra info.")
        self.assertEqual(img_tags[1]["alt"], "Second image\nDetails here.")

    def test_no_images_in_html(self):
        """Ensure function does not raise errors when there are no img tags."""
        html = "<p>No images here!</p>"
        soup = BeautifulSoup(html, "html.parser")

        normalize_whitespace_img_alt_text(soup)

        self.assertEqual(str(soup), html)


class UpdateAnnouncementTextTests(TestCase):
    def setUp(self):
        """Set up test NOFO, sections, and subsections."""
        self.nofo = Nofo.objects.create(title="Test NOFO", opdiv="Test OpDiv")

        self.section = Section.objects.create(nofo=self.nofo, name="Section 1", order=1)

        self.subsection1 = Subsection.objects.create(
            section=self.section,
            name="Subsection 1",
            tag="h3",
            order=1,
            body="This is an example.\nAnnouncement version: New",
        )

        self.subsection2 = Subsection.objects.create(
            section=self.section,
            name="Subsection 2",
            tag="h3",
            order=2,
            body="Announcement type: New\nMore content here.",
        )

        self.subsection3 = Subsection.objects.create(
            section=self.section,
            name="Subsection 3",
            tag="h3",
            order=3,
            body="No announcement text here.",
        )

        self.subsection4 = Subsection.objects.create(
            section=self.section,
            name="Subsection 4",
            tag="h3",
            order=4,
            body="Announcement type: INITIAL\nMore content afterwards.",
        )

    def test_updates_announcement_text(self):
        """Test that the function updates 'New' to 'Modified' in subsections."""
        modifications_update_announcement_text(self.nofo)

        # Refresh from DB to check changes
        self.subsection1.refresh_from_db()
        self.subsection2.refresh_from_db()
        self.subsection3.refresh_from_db()
        self.subsection4.refresh_from_db()

        self.assertEqual(
            self.subsection1.body, "This is an example.\nAnnouncement version: Modified"
        )  # Changed
        self.assertEqual(
            self.subsection2.body, "Announcement type: Modified\nMore content here."
        )  # Changed
        self.assertEqual(
            self.subsection3.body, "No announcement text here."
        )  # Unchanged
        self.assertEqual(
            self.subsection4.body,
            "Announcement type: Modified\nMore content afterwards.",
        )  # Changed

    def test_does_nothing_if_no_matches(self):
        """Test that the function makes no changes when no matching text is present."""
        self.subsection1.body = "No relevant announcement here."
        self.subsection2.body = "Completely unrelated content."
        self.subsection1.save()
        self.subsection2.save()

        modifications_update_announcement_text(self.nofo)

        # Refresh from DB
        self.subsection1.refresh_from_db()
        self.subsection2.refresh_from_db()

        self.assertEqual(self.subsection1.body, "No relevant announcement here.")
        self.assertEqual(self.subsection2.body, "Completely unrelated content.")

    def test_case_insensitivity(self):
        """Test that the function correctly updates text regardless of casing."""
        self.subsection1.body = "ANNOUNCEMENT VERSION: new"
        self.subsection2.body = "Announcement Type: NEW"
        self.subsection1.save()
        self.subsection2.save()

        modifications_update_announcement_text(self.nofo)

        self.subsection1.refresh_from_db()
        self.subsection2.refresh_from_db()

        self.assertEqual(self.subsection1.body, "Announcement version: Modified")
        self.assertEqual(self.subsection2.body, "Announcement type: Modified")


class FindSubsectionsWithFieldValueTests(TestCase):
    def setUp(self):
        self.nofo = Nofo.objects.create(
            title="Test NOFO", opdiv="AHA", application_deadline="July 15, 2025"
        )
        self.section = Section.objects.create(
            nofo=self.nofo, name="Important Dates", order=1
        )

        self.matching_subsection = Subsection.objects.create(
            section=self.section,
            name="Deadline Details",
            order=1,
            tag="h3",
            body="All applications are due by July 15, 2025. Late submissions will not be accepted.",
        )

        self.non_matching_subsection = Subsection.objects.create(
            section=self.section,
            name="Other Info",
            order=2,
            tag="h3",
            body="This section does not mention any deadlines.",
        )

    def test_returns_match_with_highlight(self):
        results = find_subsections_with_nofo_field_value(
            self.nofo, "application_deadline"
        )
        self.assertEqual(len(results), 1)
        match = results[0]
        self.assertIn(
            '<strong><mark class="bg-yellow">July 15, 2025</mark></strong>',
            match["subsection_body_highlight"],
        )
        self.assertIn("Deadline Details", match["subsection"].name)
        self.assertEqual(self.section, match["section"])
        self.assertEqual(self.matching_subsection.id, match["subsection"].id)
        self.assertEqual(match["subsection"].body, self.matching_subsection.body)

    def test_ignores_match_if_basic_information(self):
        self.matching_subsection.name = "Basic information"
        self.matching_subsection.save()
        results = find_subsections_with_nofo_field_value(
            self.nofo, "application_deadline"
        )
        self.assertEqual(len(results), 0)

    def test_returns_match_with_basic_information_if_order_is_not_1(self):
        self.matching_subsection.name = "Basic information"
        self.matching_subsection.order = 3
        self.matching_subsection.save()
        results = find_subsections_with_nofo_field_value(
            self.nofo, "application_deadline"
        )
        self.assertEqual(len(results), 1)
        match = results[0]
        self.assertIn(
            '<strong><mark class="bg-yellow">July 15, 2025</mark></strong>',
            match["subsection_body_highlight"],
        )
        self.assertIn("Basic information", match["subsection"].name)
        self.assertEqual(self.section, match["section"])
        self.assertEqual(self.matching_subsection.id, match["subsection"].id)
        self.assertEqual(match["subsection"].body, self.matching_subsection.body)

    def test_ignores_subsections_without_match(self):
        results = find_subsections_with_nofo_field_value(
            self.nofo, "application_deadline"
        )
        self.assertNotIn("Other Info", [r["subsection"].name for r in results])

    def test_case_insensitive_matching(self):
        self.matching_subsection.body = "all applications due by JULY 15, 2025"
        self.matching_subsection.save()
        results = find_subsections_with_nofo_field_value(
            self.nofo, "application_deadline"
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(self.section, results[0]["section"])
        self.assertEqual(self.matching_subsection.id, results[0]["subsection"].id)
        self.assertIn(
            '<strong><mark class="bg-yellow">JULY 15, 2025</mark></strong>',
            results[0]["subsection_body_highlight"],
        )

    def test_returns_empty_list_when_no_value(self):
        self.nofo.application_deadline = ""
        self.nofo.save()
        results = find_subsections_with_nofo_field_value(
            self.nofo, "application_deadline"
        )
        self.assertEqual(results, [])

    def test_returns_empty_list_when_no_subsection_matches(self):
        self.matching_subsection.body = "No dates mentioned here."
        self.matching_subsection.save()
        results = find_subsections_with_nofo_field_value(
            self.nofo, "application_deadline"
        )
        self.assertEqual(results, [])

    def test_returns_match_for_title(self):
        self.matching_subsection.body = "This NOFO is titled Test NOFO"
        self.matching_subsection.save()
        results = find_subsections_with_nofo_field_value(self.nofo, "title")
        self.assertEqual(len(results), 1)
        match = results[0]
        self.assertIn(
            '<strong><mark class="bg-yellow">Test NOFO</mark></strong>',
            match["subsection_body_highlight"],
        )
        self.assertEqual(self.section, match["section"])
        self.assertEqual(self.matching_subsection.id, match["subsection"].id)

    def test_returns_empty_list_when_no_title_matches(self):
        self.matching_subsection.body = "No title mentioned here."
        self.matching_subsection.save()
        results = find_subsections_with_nofo_field_value(self.nofo, "title")
        self.assertEqual(results, [])

    def test_returns_match_for_number(self):
        self.nofo.number = "HRSA-24-019"
        self.nofo.save()
        self.matching_subsection.body = "The NOFO number is HRSA-24-019"
        self.matching_subsection.save()
        results = find_subsections_with_nofo_field_value(self.nofo, "number")
        self.assertEqual(len(results), 1)
        match = results[0]
        self.assertIn(
            '<strong><mark class="bg-yellow">HRSA-24-019</mark></strong>',
            match["subsection_body_highlight"],
        )
        self.assertEqual(self.section, match["section"])
        self.assertEqual(self.matching_subsection.id, match["subsection"].id)

    def test_returns_empty_list_when_no_number_matches(self):
        self.nofo.number = "HRSA-24-019"
        self.nofo.save()
        self.matching_subsection.body = "No number mentioned here."
        self.matching_subsection.save()
        results = find_subsections_with_nofo_field_value(self.nofo, "number")
        self.assertEqual(results, [])

    # Additional tests for title field
    def test_case_insensitive_title_matching(self):
        self.matching_subsection.body = (
            "The NOFO is called TEST NOFO and it's important"
        )
        self.matching_subsection.save()
        results = find_subsections_with_nofo_field_value(self.nofo, "title")
        self.assertEqual(len(results), 1)
        match = results[0]
        self.assertIn(
            '<strong><mark class="bg-yellow">TEST NOFO</mark></strong>',
            match["subsection_body_highlight"],
        )
        self.assertEqual(self.matching_subsection.id, match["subsection"].id)

    def test_ignores_title_match_if_basic_information(self):
        self.matching_subsection.name = "Basic information"
        self.matching_subsection.body = "This NOFO is titled Test NOFO"
        self.matching_subsection.save()
        results = find_subsections_with_nofo_field_value(self.nofo, "title")
        self.assertEqual(len(results), 0)

    def test_returns_title_match_with_basic_information_if_order_is_not_1(self):
        self.matching_subsection.name = "Basic information"
        self.matching_subsection.order = 3
        self.matching_subsection.body = "This NOFO is titled Test NOFO"
        self.matching_subsection.save()
        results = find_subsections_with_nofo_field_value(self.nofo, "title")
        self.assertEqual(len(results), 1)
        match = results[0]
        self.assertIn(
            '<strong><mark class="bg-yellow">Test NOFO</mark></strong>',
            match["subsection_body_highlight"],
        )
        self.assertEqual(self.matching_subsection.id, match["subsection"].id)

    # Additional tests for number field
    def test_case_insensitive_number_matching(self):
        self.nofo.number = "HRSA-24-019"
        self.nofo.save()
        self.matching_subsection.body = "The NOFO number is hrsa-24-019"
        self.matching_subsection.save()
        results = find_subsections_with_nofo_field_value(self.nofo, "number")
        self.assertEqual(len(results), 1)
        match = results[0]
        self.assertIn(
            '<strong><mark class="bg-yellow">hrsa-24-019</mark></strong>',
            match["subsection_body_highlight"],
        )
        self.assertEqual(self.matching_subsection.id, match["subsection"].id)

    def test_ignores_number_match_if_basic_information(self):
        self.nofo.number = "HRSA-24-019"
        self.nofo.save()
        self.matching_subsection.name = "Basic information"
        self.matching_subsection.body = "The NOFO number is HRSA-24-019"
        self.matching_subsection.save()
        results = find_subsections_with_nofo_field_value(self.nofo, "number")
        self.assertEqual(len(results), 0)

    def test_returns_number_match_with_basic_information_if_order_is_not_1(self):
        self.nofo.number = "HRSA-24-019"
        self.nofo.save()
        self.matching_subsection.name = "Basic information"
        self.matching_subsection.order = 3
        self.matching_subsection.body = "The NOFO number is HRSA-24-019"
        self.matching_subsection.save()
        results = find_subsections_with_nofo_field_value(self.nofo, "number")
        self.assertEqual(len(results), 1)
        match = results[0]
        self.assertIn(
            '<strong><mark class="bg-yellow">HRSA-24-019</mark></strong>',
            match["subsection_body_highlight"],
        )
        self.assertEqual(self.matching_subsection.id, match["subsection"].id)

    def test_returns_multiple_matches_for_same_field(self):
        # NOTE - Create a second subsection that also contains the title
        second_subsection = Subsection.objects.create(
            section=self.section,
            name="Another Section",
            order=3,
            tag="h3",
            body="Check out Test NOFO for more details",
        )
        results = find_subsections_with_nofo_field_value(self.nofo, "title")
        self.assertEqual(len(results), 1)
        self.matching_subsection.body = "This document is for Test NOFO"
        self.matching_subsection.save()

        results = find_subsections_with_nofo_field_value(self.nofo, "title")
        self.assertEqual(len(results), 2)
        subsection_ids = [r["subsection"].id for r in results]
        self.assertIn(self.matching_subsection.id, subsection_ids)
        self.assertIn(second_subsection.id, subsection_ids)

    def test_returns_empty_when_field_value_is_empty(self):
        self.nofo.number = ""
        self.nofo.save()
        results = find_subsections_with_nofo_field_value(self.nofo, "number")
        self.assertEqual(results, [])


class FindMatchesWithContextTests(TestCase):
    def setUp(self):
        self.nofo = Nofo.objects.create(
            title="Test NOFO", opdiv="AHA", application_deadline="July 15, 2025"
        )
        self.section = Section.objects.create(
            nofo=self.nofo, name="Important Dates", order=1
        )

        self.matching_subsection = Subsection.objects.create(
            section=self.section,
            name="Deadline Details",
            order=3,
            tag="h3",
            body="All applications are due by July 15, 2025. Late submissions will not be accepted.",
        )

        self.non_matching_subsection = Subsection.objects.create(
            section=self.section,
            name="Other Info",
            order=4,
            tag="h3",
            body="This section does not mention any deadlines.",
        )

    def test_finds_body_match(self):
        results = find_matches_with_context(self.nofo, "July 15, 2025")
        self.assertEqual(len(results), 1)
        match = results[0]
        self.assertEqual(match["subsection"], self.matching_subsection)
        self.assertIn("July 15, 2025", match["subsection_body_highlight"])
        self.assertIsNone(match["subsection_name_highlight"])

    def test_finds_name_match_with_flag(self):
        self.matching_subsection.body = "No deadline info here."
        self.matching_subsection.name = "Deadline July 15, 2025"
        self.matching_subsection.save()
        results = find_matches_with_context(
            self.nofo, "July 15, 2025", include_name=True
        )
        self.assertEqual(len(results), 1)
        self.assertIn("July 15, 2025", results[0]["subsection_name_highlight"])

    def test_finds_both_body_and_name_match(self):
        self.matching_subsection.name = "Deadline July 15, 2025"
        self.matching_subsection.save()
        results = find_matches_with_context(
            self.nofo, "July 15, 2025", include_name=True
        )
        self.assertEqual(len(results), 1)
        self.assertIn("July 15, 2025", results[0]["subsection_body_highlight"])
        self.assertIn("July 15, 2025", results[0]["subsection_name_highlight"])

    def test_does_not_return_basic_info_subsection(self):
        self.matching_subsection.name = "Basic Information"
        self.matching_subsection.order = 1
        self.matching_subsection.section.order = 1
        self.matching_subsection.section.save()
        self.matching_subsection.save()
        results = find_matches_with_context(
            self.nofo, "July 15, 2025", include_name=True
        )
        self.assertEqual(results, [])

    def test_returns_basic_info_if_not_first(self):
        self.matching_subsection.name = "Basic Information"
        self.matching_subsection.order = 2
        self.matching_subsection.save()
        results = find_matches_with_context(
            self.nofo, "July 15, 2025", include_name=True
        )
        self.assertEqual(len(results), 1)

    def test_returns_empty_list_if_no_matches(self):
        results = find_matches_with_context(
            self.nofo, "Nonexistent String", include_name=True
        )
        self.assertEqual(results, [])

    def test_case_insensitive_matching(self):
        self.matching_subsection.body = "The DEADLINE is JULY 15, 2025."
        self.matching_subsection.save()
        results = find_matches_with_context(self.nofo, "july 15, 2025")
        self.assertEqual(len(results), 1)
        self.assertIn("JULY 15, 2025", results[0]["subsection_body_highlight"])

    def test_strips_markdown_links_in_normal_search(self):
        self.matching_subsection.body = (
            "See [the details](https://example.com/details)."
        )
        self.matching_subsection.save()
        results = find_matches_with_context(self.nofo, "details")
        self.assertEqual(len(results), 1)
        self.assertIn("details", results[0]["subsection_body_highlight"])
        self.assertNotIn(
            "href=", results[0]["subsection_body_highlight"]
        )  # Confirm link stripped

    def test_preserves_anchor_links_when_searching_for_hash(self):
        self.matching_subsection.body = "See [the FAQ](#faq-section) for details."
        self.matching_subsection.save()
        results = find_matches_with_context(self.nofo, "#faq")
        self.assertEqual(len(results), 1)
        self.assertIn(
            'See [the FAQ](<strong><mark class="bg-yellow">#faq</mark></strong>-section) for details.',
            results[0]["subsection_body_highlight"],
        )

    def test_preserves_http_links_when_searching_for_http(self):
        self.matching_subsection.body = (
            "See [the details](https://example.com/details)."
        )
        self.matching_subsection.save()
        results = find_matches_with_context(self.nofo, "https://example")
        self.assertEqual(len(results), 1)
        self.assertIn(
            'See [the details](<strong><mark class="bg-yellow">https://example</mark></strong>.com/details).',
            results[0]["subsection_body_highlight"],
        )


class ReplaceValueInSubsectionsTests(TestCase):
    def setUp(self):
        self.nofo = Nofo.objects.create(
            title="Test NOFO", opdiv="AHA", application_deadline="July 15, 2025"
        )
        self.section = Section.objects.create(nofo=self.nofo, name="Section A", order=1)

        self.subsection_1 = Subsection.objects.create(
            section=self.section,
            name="Dates",
            order=1,
            tag="h3",
            body="The application deadline is June 1, 2025.",
        )

        self.subsection_2 = Subsection.objects.create(
            section=self.section,
            name="Reminder",
            order=2,
            tag="h3",
            body="Make sure you apply before JUNE 1, 2025!",
        )

        self.subsection_3 = Subsection.objects.create(
            section=self.section,
            name="Unrelated",
            order=3,
            tag="h3",
            body="This subsection does not contain the target string.",
        )

    def test_case_insensitive_replace(self):
        updated = replace_value_in_subsections(
            [self.subsection_1.id, self.subsection_2.id],
            "June 1, 2025",
            "August 1, 2025",
        )

        self.assertEqual(len(updated), 2)
        self.subsection_1.refresh_from_db()
        self.subsection_2.refresh_from_db()

        self.assertIn("August 1, 2025", self.subsection_1.body)
        self.assertIn("August 1, 2025", self.subsection_2.body)
        self.assertNotIn("June 1, 2025", self.subsection_1.body)
        self.assertNotIn("JUNE 1, 2025", self.subsection_2.body)

    def test_unmatched_subsection_not_updated(self):
        updated = replace_value_in_subsections(
            [self.subsection_3.id], "June 1, 2025", "August 1, 2025"
        )

        self.assertEqual(len(updated), 0)

        self.subsection_3.refresh_from_db()
        self.assertIn("does not contain the target", self.subsection_3.body)

    def test_mixed_match_and_nonmatch(self):
        updated = replace_value_in_subsections(
            [self.subsection_1.id, self.subsection_3.id],
            "June 1, 2025",
            "August 1, 2025",
        )

        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0].id, self.subsection_1.id)

    def test_empty_id_list_returns_empty_list(self):
        updated = replace_value_in_subsections([], "June 1, 2025", "August 1, 2025")
        self.assertEqual(updated, [])

    def test_replace_title(self):
        self.subsection_1.body = "The NOFO title is Test NOFO"
        self.subsection_1.save()
        updated = replace_value_in_subsections(
            [self.subsection_1.id],
            "Test NOFO",
            "Updated NOFO Title",
        )
        self.assertEqual(len(updated), 1)
        self.subsection_1.refresh_from_db()
        self.assertIn("Updated NOFO Title", self.subsection_1.body)
        self.assertNotIn("Test NOFO", self.subsection_1.body)

    def test_replace_number(self):
        self.subsection_1.body = "The NOFO number is HRSA-24-019"
        self.subsection_1.save()
        updated = replace_value_in_subsections(
            [self.subsection_1.id],
            "HRSA-24-019",
            "HRSA-24-020",
        )
        self.assertEqual(len(updated), 1)
        self.subsection_1.refresh_from_db()
        self.assertIn("HRSA-24-020", self.subsection_1.body)
        self.assertNotIn("HRSA-24-019", self.subsection_1.body)

    # Additional tests for replacing title
    def test_replace_title_case_insensitive(self):
        self.subsection_1.body = "The NOFO title is TEST NOFO"
        self.subsection_1.save()
        self.subsection_2.body = "Check out test nofo for details"
        self.subsection_2.save()
        updated = replace_value_in_subsections(
            [self.subsection_1.id, self.subsection_2.id],
            "Test NOFO",
            "Updated NOFO Title",
        )
        self.assertEqual(len(updated), 2)
        self.subsection_1.refresh_from_db()
        self.subsection_2.refresh_from_db()
        self.assertIn("Updated NOFO Title", self.subsection_1.body)
        self.assertIn("Updated NOFO Title", self.subsection_2.body)
        self.assertNotIn("TEST NOFO", self.subsection_1.body)
        self.assertNotIn("test nofo", self.subsection_2.body)

    def test_replace_partial_title_match(self):
        self.subsection_1.body = "This is for Test NOFO program"
        self.subsection_1.save()
        updated = replace_value_in_subsections(
            [self.subsection_1.id],
            "Test NOFO",
            "Updated NOFO Title",
        )
        self.assertEqual(len(updated), 1)
        self.subsection_1.refresh_from_db()
        self.assertIn("Updated NOFO Title program", self.subsection_1.body)

    # NOTE - Additional tests for replacing number
    def test_replace_number_case_insensitive(self):
        self.subsection_1.body = "The NOFO number is HRSA-24-019"
        self.subsection_1.save()
        self.subsection_2.body = "Apply for hrsa-24-019 now"
        self.subsection_2.save()
        updated = replace_value_in_subsections(
            [self.subsection_1.id, self.subsection_2.id],
            "HRSA-24-019",
            "HRSA-24-020",
        )
        self.assertEqual(len(updated), 2)
        self.subsection_1.refresh_from_db()
        self.subsection_2.refresh_from_db()
        self.assertIn("HRSA-24-020", self.subsection_1.body)
        self.assertIn("HRSA-24-020", self.subsection_2.body)
        self.assertNotIn("HRSA-24-019", self.subsection_1.body)
        self.assertNotIn("hrsa-24-019", self.subsection_2.body)

    def test_replace_number_with_hyphens_and_spaces(self):
        self.subsection_1.body = "Apply to HRSA - 24 - 019"
        self.subsection_1.save()
        updated = replace_value_in_subsections(
            [self.subsection_1.id],
            "HRSA-24-019",
            "HRSA-24-020",
        )
        self.assertEqual(len(updated), 0)
        self.subsection_1.refresh_from_db()
        self.assertIn("HRSA - 24 - 019", self.subsection_1.body)

    def test_replace_multiple_occurrences_in_single_subsection(self):
        self.subsection_1.body = "Test NOFO is great. I love Test NOFO!"
        self.subsection_1.save()
        updated = replace_value_in_subsections(
            [self.subsection_1.id],
            "Test NOFO",
            "New Title",
        )
        self.assertEqual(len(updated), 1)
        self.subsection_1.refresh_from_db()
        self.assertIn("New Title is great. I love New Title!", self.subsection_1.body)
        self.assertNotIn("Test NOFO", self.subsection_1.body)

    def test_replace_with_empty_value(self):
        original_body = "The title is Test NOFO"
        self.subsection_1.body = original_body
        self.subsection_1.save()
        updated = replace_value_in_subsections(
            [self.subsection_1.id],
            "Test NOFO",
            "",
        )
        self.assertEqual(len(updated), 0)
        self.subsection_1.refresh_from_db()
        self.assertEqual(self.subsection_1.body, original_body)

    def test_replace_value_in_subsections_empty_value(self):
        """Test that empty values are not allowed as replacement values"""
        nofo = Nofo.objects.create(title="Test NOFO", opdiv="Test OpDiv")
        section = Section.objects.create(nofo=nofo, name="Test Section", order=1)
        subsection = Subsection.objects.create(
            section=section,
            name="Test Subsection",
            order=1,
            tag="h3",
            body="The deadline is June 1, 2025",
        )

        # Attempt to replace with empty value
        updated = replace_value_in_subsections([subsection.id], "June 1, 2025", "")

        self.assertEqual(len(updated), 0)

        # Verify subsection was not changed
        subsection.refresh_from_db()
        self.assertEqual(subsection.body, "The deadline is June 1, 2025")

    def test_replace_empty_old_value_behavior(self):
        original_body = self.subsection_1.body
        updated = replace_value_in_subsections(
            [self.subsection_1.id],
            "",
            "New Value",
        )
        self.assertEqual(len(updated), 0)
        self.subsection_1.refresh_from_db()
        self.assertEqual(self.subsection_1.body, original_body)

    def test_replace_in_name_with_include_name(self):
        self.subsection_1.name = "Important Dates"
        self.subsection_1.save()

        updated = replace_value_in_subsections(
            [self.subsection_1.id],
            "Important",
            "Key",
            include_name=True,
        )

        self.assertEqual(len(updated), 1)
        self.subsection_1.refresh_from_db()
        self.assertEqual(self.subsection_1.name, "Key Dates")

    def test_replace_in_name_is_case_insensitive(self):
        self.subsection_2.name = "REMINDER"
        self.subsection_2.save()

        updated = replace_value_in_subsections(
            [self.subsection_2.id],
            "reminder",
            "Heads Up",
            include_name=True,
        )

        self.assertEqual(len(updated), 1)
        self.subsection_2.refresh_from_db()
        self.assertEqual(self.subsection_2.name, "Heads Up")

    def test_replace_in_name_but_include_name_false(self):
        self.subsection_1.name = "Important Dates"
        self.subsection_1.save()

        updated = replace_value_in_subsections(
            [self.subsection_1.id],
            "Important",
            "Key",
            include_name=False,  # should skip name
        )

        self.assertEqual(len(updated), 0)
        self.subsection_1.refresh_from_db()
        self.assertEqual(self.subsection_1.name, "Important Dates")

    def test_replace_in_name_and_body(self):
        self.subsection_1.name = "Important Dates"
        self.subsection_1.body = "June 1, 2025 is an important date."
        self.subsection_1.save()

        updated = replace_value_in_subsections(
            [self.subsection_1.id],
            "important",
            "critical",
            include_name=True,
        )

        self.assertEqual(len(updated), 1)
        self.subsection_1.refresh_from_db()
        self.assertEqual(self.subsection_1.name, "critical Dates")
        self.assertEqual(self.subsection_1.body, "June 1, 2025 is an critical date.")

    def test_replace_in_name_no_match(self):
        self.subsection_3.name = "No Match Here"
        self.subsection_3.save()

        updated = replace_value_in_subsections(
            [self.subsection_3.id],
            "Something Else",
            "Updated",
            include_name=True,
        )

        self.assertEqual(len(updated), 0)
        self.subsection_3.refresh_from_db()
        self.assertEqual(self.subsection_3.name, "No Match Here")

    def test_replace_name_with_multiple_matches(self):
        self.subsection_3.name = "Important dates that are important"
        self.subsection_3.save()

        updated = replace_value_in_subsections(
            [self.subsection_3.id],
            "Important",
            "Critical",
            include_name=True,
        )

        self.assertEqual(len(updated), 1)
        self.subsection_3.refresh_from_db()
        self.assertEqual(self.subsection_3.name, "Critical dates that are Critical")

    def test_term_in_markdown_link_not_replaced_if_not_url_or_anchor(self):
        self.subsection_1.body = "Click [here](https://example.com/june-1-2025) to learn more about June-1-2025."
        self.subsection_1.save()
        updated = replace_value_in_subsections(
            [self.subsection_1.id], "June-1-2025", "August-1-2025"
        )
        self.assertEqual(len(updated), 1)  # body has visible match, not in URL
        self.subsection_1.refresh_from_db()
        self.assertIn("https://example.com/june-1-2025", self.subsection_1.body)
        self.assertIn("August-1-2025", self.subsection_1.body)
        self.assertNotIn("June-1-2025", self.subsection_1.body)

    def test_term_starting_with_hash_replaces_markdown_link(self):
        self.subsection_1.body = (
            "Click [anchor](#deadline-june-1-2025) to jump to deadline."
        )
        self.subsection_1.save()
        updated = replace_value_in_subsections(
            [self.subsection_1.id], "#deadline-june-1-2025", "#deadline-august-1-2025"
        )
        self.assertEqual(len(updated), 1)
        self.subsection_1.refresh_from_db()
        self.assertIn("#deadline-august-1-2025", self.subsection_1.body)
        self.assertNotIn("#deadline-june-1-2025", self.subsection_1.body)

    def test_term_starting_with_http_replaces_markdown_link(self):
        self.subsection_1.body = (
            "Click [external site](http://example.com/june-1-2025) to view details."
        )
        self.subsection_1.save()
        updated = replace_value_in_subsections(
            [self.subsection_1.id],
            "http://example.com/june-1-2025",
            "http://example.com/august-1-2025",
        )
        self.assertEqual(len(updated), 1)
        self.subsection_1.refresh_from_db()
        self.assertIn("http://example.com/august-1-2025", self.subsection_1.body)
        self.assertNotIn("http://example.com/june-1-2025", self.subsection_1.body)
