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
from .nofo import _get_all_id_attrs_for_nofo as get_all_id_attrs_for_nofo
from .nofo import _get_font_size_from_cssText as get_font_size_from_cssText
from .nofo import _update_link_statuses as update_link_statuses
from .nofo import (
    add_em_to_de_minimis,
    add_endnotes_header_if_exists,
    add_headings_to_nofo,
    add_page_breaks_to_headings,
    add_strongs_to_soup,
    clean_heading_tags,
    clean_table_cells,
    combine_consecutive_links,
    convert_table_first_row_to_header_row,
    convert_table_with_all_ths_to_a_regular_table,
    create_nofo,
    decompose_empty_tags,
    escape_asterisks_in_table_cells,
    find_broken_links,
    find_external_links,
    get_sections_from_soup,
    get_subsections_from_sections,
    is_callout_box_table,
    join_nested_lists,
    md,
    overwrite_nofo,
    preserve_bookmark_links,
    preserve_heading_links,
    remove_google_tracking_info_from_links,
    replace_src_for_inline_images,
    suggest_nofo_agency,
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
)
from .utils import clean_string, match_view_url

#########################################################
############# MARKDOWNIFY CONVERTER TESTS ###############
#########################################################


class TablesAndStuffInTablesConverterTABLESTest(TestCase):
    def test_table_no_colspan_or_rowspan(self):
        html = "<table><tr><td>Cell 1</td><td>Cell 2</td></tr></table>"
        expected_markdown = "|  |  |\n| --- | --- |\n| Cell 1 | Cell 2 |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_table_with_colspan(self):
        html = '<table><tr><td colspan="2">Cell 1</td></tr></table>'
        pretty_html = (
            '<table>\n <tr>\n  <td colspan="2">\n   Cell 1\n  </td>\n </tr>\n</table>'
        )
        md_body = md(html)
        self.assertEqual(md_body.strip(), pretty_html)

    def test_table_with_rowspan(self):
        html = '<table><tr><td rowspan="2">Cell 1</td><td>Cell 2</td></tr></table>'
        pretty_html = '<table>\n <tr>\n  <td rowspan="2">\n   Cell 1\n  </td>\n  <td>\n   Cell 2\n  </td>\n </tr>\n</table>'
        md_body = md(html)
        self.assertEqual(md_body.strip(), pretty_html)

    def test_table_with_nested_html(self):
        html = '<table class="c229 c294"><tr class="c202"><th class="c170 c184" colspan="4" rowspan="1"><p class="c21 c205">Year 1 Work Plan </p></th></tr><tr class="c100"><td class="c170" colspan="4" rowspan="1"><p class="c18"><strong>Program goal</strong>: Provide targeted assistance to support program efforts for outreach, education, and enrollment in health insurance plans. </p></td></tr><tr class="c281"><td class="c155 c191" colspan="1" rowspan="1"><p class="c21"><strong>Activities</strong></p></td><td class="c155 c218" colspan="1" rowspan="1"><p class="c21"><strong>Target number</strong></p></td></tr><tr class="c303"><td class="c85" colspan="1" rowspan="1"><p class="c18">Publish marketing ads on tv, radio, and print to increase visibility in community. </p></td><td class="c145" colspan="1" rowspan="1"><ul class="c1 lst-kix_list_18-0 start"><li class="c12 li-bullet-0">3 billboards </li><li class="c12 li-bullet-0">6 radio ads  </li><li class="c12 li-bullet-0">8 TV ads </li></ul></td></tr></table>'
        pretty_html = """<table>
 <tr>
  <th colspan="4" rowspan="1">
   <p>
    Year 1 Work Plan
   </p>
  </th>
 </tr>
 <tr>
  <td colspan="4" rowspan="1">
   <p>
    <strong>
     Program goal
    </strong>
    : Provide targeted assistance to support program efforts for outreach, education, and enrollment in health insurance plans.
   </p>
  </td>
 </tr>
 <tr>
  <td colspan="1" rowspan="1">
   <p>
    <strong>
     Activities
    </strong>
   </p>
  </td>
  <td colspan="1" rowspan="1">
   <p>
    <strong>
     Target number
    </strong>
   </p>
  </td>
 </tr>
 <tr>
  <td colspan="1" rowspan="1">
   <p>
    Publish marketing ads on tv, radio, and print to increase visibility in community.
   </p>
  </td>
  <td colspan="1" rowspan="1">
   <ul>
    <li>
     3 billboards
    </li>
    <li>
     6 radio ads
    </li>
    <li>
     8 TV ads
    </li>
   </ul>
  </td>
 </tr>
</table>"""

        md_body = md(html)
        self.assertEqual(md_body.strip(), pretty_html)


class TablesAndStuffInTablesConverterOLSTest(TestCase):
    maxDiff = None

    def test_ol_for_footnotes(self):
        html = '<ol><li id="footnote-0">Item 1</li><li id="footnote-1">Item 2</li></ol>'
        pretty_html = '<ol>\n <li id="footnote-0" tabindex="-1">\n  Item 1\n </li>\n <li id="footnote-1" tabindex="-1">\n  Item 2\n </li>\n</ol>'
        md_body = md(html)
        self.assertEqual(md_body.strip(), pretty_html)

    def test_ol_start_not_one(self):
        html = '<ol start="2"><li>Item 1</li><li>Item 2</li></ol>'
        pretty_html = '<ol start="2"><li>Item 1</li><li>Item 2</li></ol>'
        md_body = md(html)
        self.assertEqual(md_body.strip(), pretty_html)

    def test_ol_inside_td(self):
        html = "<table><tr><th>Header</th></tr><tr><td><ol><li>Item 1</li><li>Item 2</li></ol></td></tr></table>"
        pretty_html = "| Header |\n| --- |\n| <ol><li>Item 1</li><li>Item 2</li></ol> |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), pretty_html)

    def test_ol_start_one(self):
        html = '<ol start="1"><li>Item 1</li><li>Item 2</li></ol>'
        expected_markdown = "1. Item 1\n2. Item 2"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_ol_inside_td_start_not_one(self):
        html = '<table><tr><th>Header</th></tr><tr><td><ol start="3"><li>Item 1</li><li>Item 2</li></ol></td></tr></table>'
        pretty_html = (
            '| Header |\n| --- |\n| <ol start="3"><li>Item 1</li><li>Item 2</li></ol> |'
        )
        md_body = md(html)
        self.assertEqual(md_body.strip(), pretty_html)

    def test_ol_inside_td_start_not_one(self):
        html = '<table><tr><th>Header</th></tr><tr><td><ol start="3"><li>Item 1</li><li>Item 2</li></ol></td></tr></table>'
        pretty_html = (
            '| Header |\n| --- |\n| <ol start="3"><li>Item 1</li><li>Item 2</li></ol> |'
        )
        md_body = md(html)
        self.assertEqual(md_body.strip(), pretty_html)

    def test_table_with_ol_strip_classes_nested_html(self):
        html = '<table class="c40"><tr class="c311"><td class="c68 c127" colspan="1" rowspan="1"><p class="c89"><span class="c6">Demonstrates the ability to comply with all applicable privacy and security standards by developing a PII plan that outlines the following:</span></p></td><td class="c168 c127" colspan="1" rowspan="1"><p class="c41 c104"><span class="c69 c67"></span></p></td></tr><tr class="c216"><td class="c31" colspan="1" rowspan="1"><ul class="c1 lst-kix_list_76-0"><li class="c33 li-bullet-0"><span class="c6">A process for ensuring compliance by all staff performing Navigator activities (as well as those who have access to sensitive information or PII related to your organization’s Navigator activities) with </span><span class="c7"><a class="c32" href="https://www.google.com">FFE privacy and security standards</a></span><span class="c6">, especially when using computers, laptops, tablets, smartphones, and other electronic devices.</span></li></ul></td><td class="c11" colspan="1" rowspan="1"><p class="c41"><span class="c51">5 points</span></p></td></tr></table>'
        pretty_html = """|  |  |\n| --- | --- |\n| Demonstrates the ability to comply with all applicable privacy and security standards by developing a PII plan that outlines the following: |  |\n| <ul><li><span>A process for ensuring compliance by all staff performing Navigator activities (as well as those who have access to sensitive information or PII related to your organization’s Navigator activities) with </span><span><a href="https://www.google.com">FFE privacy and security standards</a></span><span>, especially when using computers, laptops, tablets, smartphones, and other electronic devices.</span></li></ul> | 5 points |"""

        md_body = md(html)
        self.assertEqual(md_body.strip(), pretty_html)


class TablesAndStuffInTablesConverterASTest(TestCase):
    maxDiff = None

    def test_a_for_footnotes(self):
        html = '<a id="footnote-0" href="#footnote-0">1</a>'
        expected_html = '<a href="#footnote-0" id="footnote-0">1</a>'
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html)

    def test_a_without_footnotes(self):
        html = '<a href="https://example.com">Example</a>'
        expected_markdown = "[Example](https://example.com)"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_a_with_classes(self):
        html = '<a class="link-class" href="https://example.com">Example</a>'
        expected_markdown = "[Example](https://example.com)"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_a_footnote_with_classes(self):
        html = '<a id="footnote-0" class="footnote-class" href="#footnote-0">1</a>'
        expected_html = '<a href="#footnote-0" id="footnote-0">1</a>'
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html)


class TablesAndStuffInTablesConverterPSTest(TestCase):
    maxDiff = None

    def test_p_with_bookmark_id(self):
        html = '<p id="bookmark-1">Bookmark Paragraph</p>'
        expected_html = '<p id="bookmark-1">Bookmark Paragraph</p>'
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html)

    def test_regular_p(self):
        html = "<p>Regular Paragraph</p>"
        expected_markdown = "Regular Paragraph"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())


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


#########################################################
################### FUNCTION TESTS ######################
#########################################################


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


class AddPageBreaksToHeadingsTests(TestCase):
    def setUp(self):
        # Set up a Nofo instance and related Sections and Subsections
        nofo = Nofo.objects.create(title="Test Nofo AddPageBreaksToHeadingsTests")
        section = Section.objects.create(nofo=nofo, name="Test Section", order=1)

        Subsection.objects.create(
            section=section,
            name="Basic information",
            tag="h3",
            body="Basic information section, no html_class",
            order=1,
        )

        # Subsection without a broken link
        Subsection.objects.create(
            section=section,
            name="Eligibility",
            tag="h3",
            body="Eligibility section, yes html_class",
            order=2,
        )

        Subsection.objects.create(
            section=section,
            name="Eligible applicants",
            tag="h4",
            body="Eligible applicants section, no html_class",
            order=3,
        )

        Subsection.objects.create(
            section=section,
            name="Program description",
            tag="h3",
            body="Program description section, yes html_class",
            order=4,
        )

        Subsection.objects.create(
            section=section,
            name="Application checklist",
            tag="h3",
            body="Application checklist section, yes html_class",
            order=5,
        )

    def test_add_page_breaks_to_headings(self):
        nofo = Nofo.objects.get(title="Test Nofo AddPageBreaksToHeadingsTests")

        for section in nofo.sections.all():
            for subsection in section.subsections.all():
                self.assertEqual(subsection.html_class, "")

        add_page_breaks_to_headings(nofo)

        for section in nofo.sections.all():
            self.assertEqual(section.subsections.get(order=1).html_class, "")
            self.assertEqual(
                section.subsections.get(order=2).html_class, "page-break-before"
            )
            self.assertEqual(section.subsections.get(order=3).html_class, "")
            self.assertEqual(
                section.subsections.get(order=4).html_class, "page-break-before"
            )
            self.assertEqual(
                section.subsections.get(order=5).html_class, "page-break-before"
            )


class TestGetAllIdAttrsForNofo(TestCase):
    def setUp(self):
        # Set up a Nofo instance and related Sections and Subsections
        self.nofo = Nofo.objects.create(title="Test Nofo")
        section = Section.objects.create(
            nofo=self.nofo, name="Test Section", order=1, html_id="section1"
        )

        Subsection.objects.create(
            section=section,
            name="Basic information",
            tag="h3",
            body="Basic information section with <span id='subsection_1_custom_id'>custom id</span>",
            order=1,
            html_id="subsection1",
        )

        Subsection.objects.create(
            section=section,  # no id
            body="Eligibility section with a link to <span id='subsection_2_custom_id'>custom id 2</span> and <a href='fake_id'>a link</a> to some other id",
            order=2,
        )

        Subsection.objects.create(
            section=section,
            name="Section 3",
            tag="h4",
            body="Eligible applicants section mentioning #applicants (not a valid id)",
            order=3,
            html_id="subsection3",
        )

        Subsection.objects.create(
            section=section,
            name="Section 4",
            tag="h3",
            body="ID for this section is autogenerated",
            order=4,
        )

    def test_find_all_ids(self):
        expected_ids = {
            "#section1",
            "#subsection1",
            "#subsection_1_custom_id",
            "#subsection_2_custom_id",
            "#subsection3",
            "#4--test-section--section-4",  # autogenerated
        }
        result = get_all_id_attrs_for_nofo(self.nofo)
        self.assertEqual(result, expected_ids)


class TestFindBrokenLinks(TestCase):
    def setUp(self):
        # Set up a Nofo instance and related Sections and Subsections
        nofo = Nofo.objects.create(title="Test Nofo TestFindBrokenLinks")
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

        Subsection.objects.create(
            section=section,
            name="Subsection with a Blank link",
            tag="h3",
            body="This is an [About:Blank link](about:blank) in markdown.",
            order=6,
        )

        Subsection.objects.create(
            section=section,
            name="Subsection with an underscore link",
            tag="h3",
            body="This is an [Underscore link](#_Paper_Submissions) in markdown.",
            order=7,
        )

        Subsection.objects.create(
            section=section,
            name="Subsection with real id and fake id",
            tag="h3",
            body="This is an [link](#link), and this is [fake](#fake). <span id='link'>Link links here</span>.",
            order=8,
        )

    def test_find_broken_links_identifies_broken_links(self):
        nofo = Nofo.objects.get(title="Test Nofo TestFindBrokenLinks")
        broken_links = find_broken_links(nofo)
        self.assertEqual(len(broken_links), 7)
        self.assertEqual(broken_links[0]["link_href"], "#h.broken-link")
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

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["url"], "https://groundhog-day.com")

    def test_find_external_links_ignore_nofo_rodeo(self):
        self_sections = self.sections
        # add external links to subsections
        self_sections[0]["subsections"][0]["body"] = [
            '<p>Section 1 body with link to <a href="https://nofo.rodeo/nofos/">All Nofos</a></p>'
        ]

        nofo = create_nofo("Test Nofo", self_sections)
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

    def test_suggest_nofo_number_no_match_returns_hrsa_theme(self):
        nofo_number = "abc-def-ghi"
        nofo_theme = "portrait-hrsa-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_empty_returns_hrsa_theme(self):
        nofo_number = ""
        nofo_theme = "portrait-hrsa-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)


class HTMLSuggestCoverTests(TestCase):
    def test_suggest_nofo_cover_hrsa_returns_medium(self):
        nofo_cover = "nofo--cover-page--medium"
        self.assertEqual(suggest_nofo_cover("portrait-hrsa-blue"), nofo_cover)

    def test_suggest_nofo_cover_cdc_returns_medium(self):
        nofo_cover = "nofo--cover-page--medium"
        self.assertEqual(suggest_nofo_cover("portrait-cdc-blue"), nofo_cover)

    def test_suggest_nofo_cover_cms_returns_medium(self):
        nofo_cover = "nofo--cover-page--medium"
        self.assertEqual(suggest_nofo_cover("portrait-cms-white"), nofo_cover)

    def test_suggest_nofo_cover_ihs_returns_medium(self):
        nofo_cover = "nofo--cover-page--medium"
        self.assertEqual(suggest_nofo_cover("portrait-ihs-white"), nofo_cover)

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
            "<div><h1>Endnotes</h1></div>",
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
        html_content = '<div><ol><li id="footnote-0">Item 1</li></ol></div>'
        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup)
        self.assertEqual(
            str(soup),
            '<div><h1>Endnotes</h1><ol><li id="footnote-0">Item 1</li></ol></div>',
        )

    def test_basic_ol_with_li_no_id(self):
        html_content = "<div><ol><li>Item 1</li></ol></div>"
        soup = BeautifulSoup(html_content, "html.parser")
        add_endnotes_header_if_exists(soup)
        self.assertEqual(str(soup), html_content)

    def test_basic_ol_with_wrong_footnote_li(self):
        html_content = '<div><ol><li id="footnote-1">Item 1</li></ol></div>'
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

    def test_asterisk_escaped_in_table_headings(self):
        html = "<table><thead><tr><th>Test* Text</th></tr></thead></table>"
        soup = BeautifulSoup(html, "html.parser")
        escape_asterisks_in_table_cells(soup)
        self.assertIn(r"Test\* Text", soup.th.text)

    def test_already_escaped_asterisk_not_doubly_escaped_in_table_headings(self):
        html = "<table><thead><tr><th>Test\\* Text</th></tr></thead></table>"
        soup = BeautifulSoup(html, "html.parser")
        escape_asterisks_in_table_cells(soup)
        self.assertIn(r"Test\* Text", soup.th.text)
        self.assertNotIn(r"Test\\* Text", soup.th.text)


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
        expected_html = "<p>Some text <em>de minimis</em> rate and <em>De Minimis</em> threshold.</p>"
        soup = BeautifulSoup(html, "html.parser")
        add_em_to_de_minimis(soup)
        self.assertEqual(str(soup), expected_html)

    def test_ignores_non_matching_spans(self):
        html = "<p><span>not de minimis</span> example <span>DE MINIMUS</span>.</p>"
        expected_html = (
            "<p><span>not de minimis</span> example <span>DE MINIMUS</span>.</p>"
        )
        soup = BeautifulSoup(html, "html.parser")
        add_em_to_de_minimis(soup)
        self.assertEqual(str(soup), expected_html)

    def test_handles_empty_spans(self):
        html = "<p><span></span> <span>De Minimis</span></p>"
        expected_html = "<p><span></span> <em>De Minimis</em></p>"
        soup = BeautifulSoup(html, "html.parser")
        add_em_to_de_minimis(soup)
        self.assertEqual(str(soup), expected_html)

    def test_case_insensitive_matching(self):
        html = "<p><span>de minimis</span> <span>De Minimis</span> <span>dE mInImIs</span></p>"
        expected_html = (
            "<p><em>de minimis</em> <em>De Minimis</em> <em>dE mInImIs</em></p>"
        )
        soup = BeautifulSoup(html, "html.parser")
        add_em_to_de_minimis(soup)
        self.assertEqual(str(soup), expected_html)

    def test_classnames_are_prereserved(self):
        html = '<p><strong><span class="c7">Method 2—</span></strong><strong><span class="c7 c67">De minimis</span></strong><strong><span class="c7"> rate.</span></strong><span> Per </span><a class="c6" href="https://www.ecfr.gov/current/title-45/part-75#p-75.414(f)">45 CFR 75.414(f)</a><span>, if you have never received a negotiated indirect cost rate, you may elect to charge a </span><span class="c67">de minimis</span><span> rate. If you are awaiting approval of an indirect cost proposal, you may also use the </span><span class="c67">de minimis</span><span class="c0"> rate. If you choose this method, costs included in the indirect cost pool must not be charged as direct costs. </span>I am <em>an emphasized element</em></p>'
        expected_html = '<p><strong><span class="c7">Method 2—</span></strong><strong><em class="c7 c67">De minimis</em></strong><strong><span class="c7"> rate.</span></strong><span> Per </span><a class="c6" href="https://www.ecfr.gov/current/title-45/part-75#p-75.414(f)">45 CFR 75.414(f)</a><span>, if you have never received a negotiated indirect cost rate, you may elect to charge a </span><em class="c67">de minimis</em><span> rate. If you are awaiting approval of an indirect cost proposal, you may also use the </span><em class="c67">de minimis</em><span class="c0"> rate. If you choose this method, costs included in the indirect cost pool must not be charged as direct costs. </span>I am <em>an emphasized element</em></p>'
        soup = BeautifulSoup(html, "html.parser")
        add_em_to_de_minimis(soup)
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


class PreserveHeadingLinksTest(TestCase):
    def test_empty_anchor_with_heading_id(self):
        html = '<h4><a id="_heading=h.3rdcrjn"></a>About priority populations</h4>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = '<h4 id="_heading=h.3rdcrjn">About priority populations</h4>'
        self.assertEqual(result, expected)

    def test_empty_anchor_with_underscore_id(self):
        html = '<h4><a id="_Deadlines"></a>About priority populations</h4>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = '<h4 id="_Deadlines">About priority populations</h4>'
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

    def test_empty_anchor_without_heading_id(self):
        html = '<h4><a id="other_id"></a>About priority populations</h4>'
        soup = BeautifulSoup(html, "html.parser")
        preserve_heading_links(soup)
        result = str(soup)
        expected = '<h4><a id="other_id"></a>About priority populations</h4>'
        self.assertEqual(result, expected)

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
