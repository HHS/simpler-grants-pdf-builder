import re

from bs4 import BeautifulSoup
from django.test import TestCase
from django.utils.safestring import SafeString

from nofos.models import Nofo, Section, Subsection
from nofos.templatetags.add_classes_to_links import add_classes_to_broken_links
from nofos.templatetags.safe_br import safe_br
from nofos.templatetags.utils import (
    _add_class_if_not_exists_to_tag,
    _add_class_if_not_exists_to_tags,
    add_caption_to_table,
    add_class_to_list,
    add_class_to_nofo_title,
    add_class_to_table,
    add_class_to_table_rows,
    convert_paragraph_to_searchable_hr,
    filter_breadcrumb_sections,
    find_elements_with_character,
    format_footnote_ref_html,
    get_breadcrumb_text,
    get_footnote_type,
    get_parent_td,
    is_callout_box_table_markdown,
    is_floating_callout_box,
    is_footnote_ref,
    match_numbered_sublist,
    wrap_text_before_colon_in_strong,
)


class MockSection:
    def __init__(self, name):
        self.name = name


class TestAddClassIfNotExists(TestCase):
    def test_add_class_to_element_without_class(self):
        html = "<div></div>"
        soup = BeautifulSoup(html, "html.parser")
        div = soup.find("div")
        _add_class_if_not_exists_to_tag(div, "new-class", "div")
        self.assertIn("new-class", div["class"])

    def test_do_not_add_class_if_already_exists(self):
        html = "<div class='existing-class'></div>"
        soup = BeautifulSoup(html, "html.parser")
        div = soup.find("div")
        _add_class_if_not_exists_to_tag(div, "existing-class", "div")
        self.assertEqual(len(div["class"]), 1)

    def test_add_class_only_if_tag_name_matches(self):
        html = "<div>123</div><span>456</span>"
        soup = BeautifulSoup(html, "html.parser")
        div = soup.find("div")
        span = soup.find("span")
        _add_class_if_not_exists_to_tag(div, "new-class", "span")
        self.assertNotIn("new-class", div.get("class", []))
        _add_class_if_not_exists_to_tag(span, "new-class", "span")
        self.assertIn("new-class", span.get("class", []))

    def test_add_class_to_tags(self):
        html = "<div>123</div><span>456</span>"
        soup = BeautifulSoup(html, "html.parser")
        div = soup.find("div")
        span = soup.find("span")
        _add_class_if_not_exists_to_tags(div, "new-class", "span|div")
        self.assertIn("new-class", div.get("class", []))
        _add_class_if_not_exists_to_tags(span, "new-class", "span|div")
        self.assertIn("new-class", span.get("class", []))

    def test_add_class_to_tags_only_if_tag_name_matches(self):
        html = "<div>123</div><span>456</span><strong>789</strong>"
        soup = BeautifulSoup(html, "html.parser")
        div = soup.find("div")
        span = soup.find("span")
        strong = soup.find("strong")
        _add_class_if_not_exists_to_tags(div, "new-class", "span|div")
        self.assertIn("new-class", div.get("class", []))
        _add_class_if_not_exists_to_tags(span, "new-class", "span|div")
        self.assertIn("new-class", span.get("class", []))
        _add_class_if_not_exists_to_tags(strong, "new-class", "span|div")
        self.assertNotIn("new-class", strong.get("class", []))


class AddCaptionToTableTests(TestCase):
    def setUp(self):
        self.caption_text = "Table: Physician Assistant Training Chart"
        self.html_filename = "nofos/fixtures/html/table.html"
        with open(self.html_filename, "r", encoding="UTF-8") as file:
            self.soup = BeautifulSoup(file, "html.parser")

    def _contains_table(self, tag):
        if tag.name != "p":
            return False
        text = "".join(tag.stripped_strings)
        return re.search(r"^table:", text, re.IGNORECASE)

    def test_table_before_add_caption_to_table(self):
        table = self.soup.find("table")

        # table doesn't have a caption
        self.assertIsNone(table.find("caption"))

        # there is a paragraph tag with the caption
        paragraph = self.soup.find_all(self._contains_table)[0]
        self.assertIsNotNone(paragraph)

        # the paragraph tag has a span inside of it
        self.assertIsNotNone(paragraph.find("span"))

    def test_table_after_add_caption_to_table(self):
        table = self.soup.find("table")
        add_caption_to_table(table)

        # no paragraph tag with the caption
        paragraph = self.soup.find_all(self._contains_table)
        self.assertEqual(len(paragraph), 0)

        # table DOES have a caption
        caption = table.find("caption", string=self.caption_text)
        self.assertIsNotNone(caption)

        # the caption tag does not have a span inside of it
        self.assertIsNone(caption.find("span"))

        # assert the table has the classname "table--with-caption"
        self.assertIn("table--with-caption", table["class"])

    def test_add_caption_to_table(self):
        html = "<p>Table: Example Caption</p><table><tr><td>Data</td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        add_caption_to_table(table)
        self.assertIsNotNone(table.caption)
        self.assertEqual(table.caption.string.strip(), "Table: Example Caption")
        self.assertIn("table--with-caption", table.get("class", []))

    def test_no_caption_if_no_preceding_paragraph(self):
        html = "<table><tr><td>Data</td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        add_caption_to_table(table)
        self.assertIsNone(table.caption)

    def test_no_caption_if_paragraph_does_not_start_with_keyword(self):
        html = "<p>Not a caption</p><table><tr><td>Data</td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        add_caption_to_table(table)
        self.assertIsNone(table.caption)

    def test_add_caption_only_to_first_table(self):
        html = "<p>Table: Example Caption for Table 1</p><table><tr><th>Table 1</th></tr><tr><td>Data</td></tr></table><table><tr><th>Table 2</th></tr><tr><td>Data</td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        table1 = soup.find_all("table")[0]
        table2 = soup.find_all("table")[1]

        add_caption_to_table(table1)
        self.assertIsNotNone(table1.caption)
        self.assertEqual(
            table1.caption.string.strip(), "Table: Example Caption for Table 1"
        )
        self.assertIn("table--with-caption", table1.get("class", []))

        add_caption_to_table(table2)
        self.assertIsNone(table2.caption)
        self.assertNotIn("table--with-caption", table2.get("class", []))

    def test_add_caption_only_to_second_table(self):
        html = "<table><tr><th>Table 1</th></tr><tr><td>Data</td></tr></table><p>Table: Example Caption for Table 2</p><table><tr><th>Table 2</th></tr><tr><td>Data</td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        table1 = soup.find_all("table")[0]
        table2 = soup.find_all("table")[1]

        add_caption_to_table(table1)
        self.assertIsNone(table1.caption)
        self.assertNotIn("table--with-caption", table1.get("class", []))

        add_caption_to_table(table2)
        self.assertIsNotNone(table2.caption)
        self.assertEqual(
            table2.caption.string.strip(), "Table: Example Caption for Table 2"
        )
        self.assertIn("table--with-caption", table2.get("class", []))


class AddClassToListsTests(TestCase):
    def test_add_class_to_ordered_list(self):
        html_content = "<ol><li>Item 1</li><li>Item 2</li><li>Short</li></ol>"
        soup = BeautifulSoup(html_content, "html.parser")
        add_class_to_list(soup.ol)
        self.assertIn("avoid-page-break-before", soup.find_all("li")[-1]["class"])

    def test_add_class_to_unordered_list(self):
        html_content = "<ul><li>Item 1</li><li>Item 2</li><li>Short</li></ul>"
        soup = BeautifulSoup(html_content, "html.parser")
        add_class_to_list(soup.ul)
        self.assertIn("avoid-page-break-before", soup.find_all("li")[-1]["class"])

    def test_do_not_add_class_to_70_char_final_item(self):
        html_content = "<ul><li>Item 1</li><li>Item 2</li><li>This sentence is exactly 85 characters in length, so it should not add the classname.</li></ul>"
        soup = BeautifulSoup(html_content, "html.parser")
        add_class_to_list(soup.ul)
        final_list_item = soup.find_all("li")[-1]
        self.assertFalse("avoid-page-break-before" in final_list_item.get("class", []))

    def test_add_class_to_69_char_final_item(self):
        html_content = "<ul><li>Item 1</li><li>Item 2</li><li>This sentence is exactly 84 characters in length, so it should not add the classname</li></ul>"
        soup = BeautifulSoup(html_content, "html.parser")
        add_class_to_list(soup.ul)
        final_list_item = soup.find_all("li")[-1]
        self.assertTrue("avoid-page-break-before" in final_list_item.get("class", []))

    def test_empty_list(self):
        html_content = "<ul></ul>"
        soup = BeautifulSoup(html_content, "html.parser")
        add_class_to_list(soup.ul)
        self.assertEqual(len(soup.find_all("li")), 0)

    def test_class_already_exists(self):
        html_content = (
            "<ul><li>Item 1</li><li class='avoid-page-break-before'>Short</li></ul>"
        )
        soup = BeautifulSoup(html_content, "html.parser")
        add_class_to_list(soup.ul)
        self.assertEqual(soup.find_all("li")[-1]["class"], ["avoid-page-break-before"])


class AddClassToNofoTitleTest(TestCase):
    def test_normal_title_length(self):
        title = "Tribal Management Grant (TMG) Program"
        result = add_class_to_nofo_title(title)
        self.assertEqual(result, "nofo--cover-page--title--h1--normal")

    def test_smaller_title_length(self):
        title = "Improving quality of care and health outcomes through innovative systems and technologies in Malawi under the President’s Emergency Plan for AIDS Relief (PEPFAR)"
        result = add_class_to_nofo_title(title)
        self.assertEqual(result, "nofo--cover-page--title--h1--smaller")

    def test_very_smol_title_length(self):
        title = "Strengthening economic analysis and capacity in support of program management for HIV, TB, and related health threats in South Africa (SA) under the President's Emergency Plan for AIDS Relief (PEPFAR)"
        result = add_class_to_nofo_title(title)
        self.assertEqual(result, "nofo--cover-page--title--h1--very-smol")

    def test_very_very_smol_title_length(self):
        title = "Strengthening the Botswana Ministry of Health (MOH) laboratory and health systems through technical assistance (TA) to effectively manage and sustain a quality HIV/TB program in Botswana under the President’s Emergency Plan for AIDS Relief (PEPFAR)"
        result = add_class_to_nofo_title(title)
        self.assertEqual(result, "nofo--cover-page--title--h1--very-very-smol")

    def test_edge_case_exact_120(self):
        title = "x" * 120
        result = add_class_to_nofo_title(title)
        self.assertEqual(result, "nofo--cover-page--title--h1--normal")

    def test_edge_case_just_over_120(self):
        title = "x" * 121
        result = add_class_to_nofo_title(title)
        self.assertEqual(result, "nofo--cover-page--title--h1--smaller")

    def test_edge_case_exact_165(self):
        title = "x" * 165
        result = add_class_to_nofo_title(title)
        self.assertEqual(result, "nofo--cover-page--title--h1--smaller")

    def test_edge_case_just_over_165(self):
        title = "x" * 166
        result = add_class_to_nofo_title(title)
        self.assertEqual(result, "nofo--cover-page--title--h1--very-smol")

    def test_edge_case_exact_225(self):
        title = "x" * 225
        result = add_class_to_nofo_title(title)
        self.assertEqual(result, "nofo--cover-page--title--h1--very-smol")

    def test_edge_case_just_over_225(self):
        title = "x" * 226
        result = add_class_to_nofo_title(title)
        self.assertEqual(result, "nofo--cover-page--title--h1--very-very-smol")


class IsCalloutBoxTableMarkdownTest(TestCase):
    def test_valid_callout_box_table(self):
        # A table with 1 column, 2 rows, and 1 empty cell
        html = """
        <table>
            <tr><th>Header</th></tr>
            <tr><td></td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        self.assertTrue(is_callout_box_table_markdown(table))

    def test_invalid_multiple_columns(self):
        # A table with more than 1 column
        html = """
        <table>
            <tr><th>Header 1</th><th>Header 2</th></tr>
            <tr><td></td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        self.assertFalse(is_callout_box_table_markdown(table))

    def test_invalid_multiple_rows(self):
        # A table with more than 2 rows
        html = """
        <table>
            <tr><th>Header</th></tr>
            <tr><td></td></tr>
            <tr><td></td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        self.assertFalse(is_callout_box_table_markdown(table))

    def test_invalid_non_empty_cell(self):
        # A table with a non-empty cell
        html = """
        <table>
            <tr><th>Header</th></tr>
            <tr><td>Non-empty</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        self.assertFalse(is_callout_box_table_markdown(table))

    def test_invalid_no_cell(self):
        # A table with no <td> cells
        html = """
        <table>
            <tr><th>Header</th></tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        self.assertFalse(is_callout_box_table_markdown(table))

    def test_invalid_no_rows(self):
        # An empty table with no rows
        html = "<table>Hello</table>"
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        self.assertFalse(is_callout_box_table_markdown(table))


class HTMLTableClassTests(TestCase):
    def _generate_table(self, num_cols, num_rows=1, cell="td", table_empty=False):
        rows = ""
        for j in range(num_rows):
            cols = ""
            for i in range(num_cols):
                if table_empty:
                    cols += "<{0}></{0}>".format(cell, i + 1)
                else:
                    cols += "<{0}>Col {1}</{0}>".format(cell, i + 1)
            rows += "<tr>{}</tr>".format(cols)

        return "<table>{}</table>".format(rows)

    def test_table_class_2_cols(self):
        table_html = self._generate_table(num_cols=2)
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--small")

    def test_table_class_2_cols_empty(self):
        table_html = self._generate_table(num_cols=2, table_empty=True)
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--small")

    def test_table_class_3_cols(self):
        table_html = self._generate_table(num_cols=3)
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--large")

    def test_table_class_3_cols_empty(self):
        table_html = self._generate_table(num_cols=3, table_empty=True)
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--small")

    def test_table_class_4_cols(self):
        table_html = self._generate_table(num_cols=4)
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--large")

    def test_table_class_4_cols_empty(self):
        table_html = self._generate_table(num_cols=4, table_empty=True)
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--large")

    def test_table_class_5_cols(self):
        table_html = self._generate_table(num_cols=5)
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--large")

    def test_table_class_md_rows(self):
        table_html = self._generate_table(num_cols=2, num_rows=6)
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--small")

    def test_table_class_lg_rows(self):
        table_html = self._generate_table(num_cols=2, num_rows=7)
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--small")

    def test_table_class_md_md(self):
        table_html = self._generate_table(num_cols=4, num_rows=6)
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--large")

    def test_table_class_lg_recommended_for_header(self):
        table_html = "<table><thead><tr><th>Recommended For</th></tr></thead><tbody><tr><td>Cell content</td></tr></tbody></table>"
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--large")

    def test_table_class_sm_criterion_header(self):
        # 3 cols, should ordinarily be table--large
        table_html = "<table><thead><tr><th>Criterion</th><th>Heading 2</th><th>Heading 3</th></tr></thead><tbody><tr><td>Cell 1</td><td>Cell 2</td><td>Cell 3</td></tr></tbody></table>"
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--criterion")

    def test_invalid_table(self):
        table_html = "<table>Hello</table>"
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--invalid")


class TestAddClassToTableRows(TestCase):
    def test_all_empty_rows(self):
        html = """
        <table>
            <tr><td></td><td></td></tr>
            <tr><td></td><td></td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        table_rows = soup.find_all("tr")
        for row in table_rows:
            self.assertEqual(add_class_to_table_rows(row), "table-row--empty")

    def test_all_empty_rows_including_header_row(self):
        html = """
        <table>
            <tr><th></th><th></th></tr>
            <tr><td></td><td></td></tr>
            <tr><td></td><td></td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        table_rows = soup.find_all("tr")
        for row in table_rows:
            self.assertEqual(add_class_to_table_rows(row), "table-row--empty")

    def test_non_empty_row(self):
        html = """
        <table>
            <tr><td>Content</td><td></td></tr>
            <tr><td></td><td></td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        table_rows = soup.find_all("tr")
        self.assertNotEqual(add_class_to_table_rows(table_rows[0]), "table-row--empty")
        self.assertEqual(add_class_to_table_rows(table_rows[1]), "table-row--empty")

    def test_non_empty_header_row(self):
        html = """
        <table>
            <tr><th>Column 1</th><th>Column 2</th></tr>
            <tr><td></td><td></td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        table_rows = soup.find_all("tr")
        self.assertNotEqual(add_class_to_table_rows(table_rows[0]), "table-row--empty")
        self.assertEqual(add_class_to_table_rows(table_rows[1]), "table-row--empty")


class ModifyHtmlTests(TestCase):
    # page-break
    def test_convert_paragraph_to_searchable_hr_with_matching_paragraph_page_break(
        self,
    ):
        original_html = "<p>page-break</p>"
        expected_html = '<div class="page-break--hr--container"><hr class="page-break-before page-break--hr"/><span class="page-break--hr--text">[ ↓ page-break ↓ ]</span></div>'
        soup = BeautifulSoup(original_html, "html.parser")
        convert_paragraph_to_searchable_hr(soup.p)
        self.assertEqual(str(soup), expected_html)

    def test_convert_paragraph_to_searchable_hr_without_matching_paragraph_page_break(
        self,
    ):
        original_html = "<p>Some other content</p>"
        soup = BeautifulSoup(original_html, "html.parser")
        convert_paragraph_to_searchable_hr(soup.p)
        self.assertEqual(str(soup), original_html)

    def test_convert_paragraph_to_searchable_hr_without_matching_paragraph_page_break(
        self,
    ):
        original_html = "<p> page-break </p>"  # fails because of the extra whitespace
        soup = BeautifulSoup(original_html, "html.parser")
        convert_paragraph_to_searchable_hr(soup.p)
        self.assertEqual(str(soup), original_html)

    def test_convert_paragraph_to_searchable_hr_with_multiple_matching_paragraphs_page_break(
        self,
    ):
        original_html = "<p>page-break</p><p>page-break</p>"
        expected_html = '<div class="page-break--hr--container"><hr class="page-break-before page-break--hr"/><span class="page-break--hr--text">[ ↓ page-break ↓ ]</span></div><div class="page-break--hr--container"><hr class="page-break-before page-break--hr"/><span class="page-break--hr--text">[ ↓ page-break ↓ ]</span></div>'
        soup = BeautifulSoup(original_html, "html.parser")
        for p in soup.find_all("p"):
            convert_paragraph_to_searchable_hr(p)
        self.assertEqual(str(soup), expected_html)

    # page-break-before
    def test_convert_paragraph_to_searchable_hr_with_matching_paragraph_page_break_before(
        self,
    ):
        original_html = "<p>page-break-before</p>"
        expected_html = '<div class="page-break--hr--container"><hr class="page-break-before page-break--hr"/><span class="page-break--hr--text">[ ↓ page-break ↓ ]</span></div>'
        soup = BeautifulSoup(original_html, "html.parser")
        convert_paragraph_to_searchable_hr(soup.p)
        self.assertEqual(str(soup), expected_html)

    def test_convert_paragraph_to_searchable_hr_with_nested_tags_page_break(
        self,
    ):
        original_html = "<div><p>page-break</p></div>"
        expected_html = '<div><div class="page-break--hr--container"><hr class="page-break-before page-break--hr"/><span class="page-break--hr--text">[ ↓ page-break ↓ ]</span></div></div>'
        soup = BeautifulSoup(original_html, "html.parser")
        convert_paragraph_to_searchable_hr(soup.p)
        self.assertEqual(str(soup), expected_html)

    def test_convert_paragraph_to_searchable_hr_without_matching_paragraph_page_break_before(
        self,
    ):
        original_html = (
            "<p> page-break-before </p>"  # fails because of the extra whitespace
        )
        soup = BeautifulSoup(original_html, "html.parser")
        convert_paragraph_to_searchable_hr(soup.p)
        self.assertEqual(str(soup), original_html)

    def test_convert_paragraph_to_searchable_hr_with_multiple_matching_paragraphs_page_break_before(
        self,
    ):
        original_html = "<p>page-break-before</p><p>page-break-before</p>"
        expected_html = '<div class="page-break--hr--container"><hr class="page-break-before page-break--hr"/><span class="page-break--hr--text">[ ↓ page-break ↓ ]</span></div><div class="page-break--hr--container"><hr class="page-break-before page-break--hr"/><span class="page-break--hr--text">[ ↓ page-break ↓ ]</span></div>'
        soup = BeautifulSoup(original_html, "html.parser")
        for p in soup.find_all("p"):
            convert_paragraph_to_searchable_hr(p)
        self.assertEqual(str(soup), expected_html)

    def test_convert_paragraph_to_searchable_hr_with_nested_tags_page_break_before(
        self,
    ):
        original_html = "<div><p>page-break-before</p></div>"
        expected_html = '<div><div class="page-break--hr--container"><hr class="page-break-before page-break--hr"/><span class="page-break--hr--text">[ ↓ page-break ↓ ]</span></div></div>'
        soup = BeautifulSoup(original_html, "html.parser")
        convert_paragraph_to_searchable_hr(soup.p)
        self.assertEqual(str(soup), expected_html)

    # page-break-after
    def test_convert_paragraph_to_searchable_hr_with_matching_paragraph_page_break_after(
        self,
    ):
        original_html = "<p>page-break-after</p>"
        expected_html = '<div class="page-break--hr--container"><hr class="page-break-after page-break--hr"/><span class="page-break--hr--text">[ ↓ page-break ↓ ]</span></div>'
        soup = BeautifulSoup(original_html, "html.parser")
        convert_paragraph_to_searchable_hr(soup.p)
        self.assertEqual(str(soup), expected_html)

    def test_convert_paragraph_to_searchable_hr_without_matching_paragraph_page_break_after(
        self,
    ):
        original_html = (
            "<p> page-break-after </p>"  # fails because of the extra whitespace
        )
        soup = BeautifulSoup(original_html, "html.parser")
        convert_paragraph_to_searchable_hr(soup.p)
        self.assertEqual(str(soup), original_html)

    def test_convert_paragraph_to_searchable_hr_with_multiple_matching_paragraphs_page_break_after(
        self,
    ):
        original_html = "<p>page-break-after</p><p>page-break-after</p>"
        expected_html = '<div class="page-break--hr--container"><hr class="page-break-after page-break--hr"/><span class="page-break--hr--text">[ ↓ page-break ↓ ]</span></div><div class="page-break--hr--container"><hr class="page-break-after page-break--hr"/><span class="page-break--hr--text">[ ↓ page-break ↓ ]</span></div>'
        soup = BeautifulSoup(original_html, "html.parser")
        for p in soup.find_all("p"):
            convert_paragraph_to_searchable_hr(p)
        self.assertEqual(str(soup), expected_html)

    def test_convert_paragraph_to_searchable_hr_with_nested_tags_page_break_after(self):
        original_html = "<div><p>page-break-after</p></div>"
        expected_html = '<div><div class="page-break--hr--container"><hr class="page-break-after page-break--hr"/><span class="page-break--hr--text">[ ↓ page-break ↓ ]</span></div></div>'
        soup = BeautifulSoup(original_html, "html.parser")
        convert_paragraph_to_searchable_hr(soup.p)
        self.assertEqual(str(soup), expected_html)

    # column-break-before
    def test_convert_paragraph_to_searchable_hr_with_matching_paragraph_column_break_before(
        self,
    ):
        original_html = "<p>column-break-before</p>"
        expected_html = '<div class="page-break--hr--container"><hr class="column-break-before page-break--hr"/><span class="page-break--hr--text">[ ← column-break-before ← ]</span></div>'
        soup = BeautifulSoup(original_html, "html.parser")
        convert_paragraph_to_searchable_hr(soup.p)
        self.assertEqual(str(soup), expected_html)

    def test_convert_paragraph_to_searchable_hr_without_matching_paragraph_page_break_before(
        self,
    ):
        original_html = (
            "<p> column-break-before </p>"  # fails because of the extra whitespace
        )
        soup = BeautifulSoup(original_html, "html.parser")
        convert_paragraph_to_searchable_hr(soup.p)
        self.assertEqual(str(soup), original_html)

    def test_convert_paragraph_to_searchable_hr_with_multiple_matching_paragraphs_column_break_before(
        self,
    ):
        original_html = "<p>column-break-before</p><p>column-break-before</p>"
        expected_html = '<div class="page-break--hr--container"><hr class="column-break-before page-break--hr"/><span class="page-break--hr--text">[ ← column-break-before ← ]</span></div><div class="page-break--hr--container"><hr class="column-break-before page-break--hr"/><span class="page-break--hr--text">[ ← column-break-before ← ]</span></div>'
        soup = BeautifulSoup(original_html, "html.parser")
        for p in soup.find_all("p"):
            convert_paragraph_to_searchable_hr(p)
        self.assertEqual(str(soup), expected_html)

    def test_convert_paragraph_to_searchable_hr_with_nested_tags_column_break_before(
        self,
    ):
        original_html = "<div><p>column-break-before</p></div>"
        expected_html = '<div><div class="page-break--hr--container"><hr class="column-break-before page-break--hr"/><span class="page-break--hr--text">[ ← column-break-before ← ]</span></div></div>'
        soup = BeautifulSoup(original_html, "html.parser")
        convert_paragraph_to_searchable_hr(soup.p)
        self.assertEqual(str(soup), expected_html)

    # column-break-after
    def test_convert_paragraph_to_searchable_hr_with_matching_paragraph_column_break_after(
        self,
    ):
        original_html = "<p>column-break-after</p>"
        expected_html = '<div class="page-break--hr--container"><hr class="column-break-after page-break--hr"/><span class="page-break--hr--text">[ → column-break-after → ]</span></div>'
        soup = BeautifulSoup(original_html, "html.parser")
        convert_paragraph_to_searchable_hr(soup.p)
        self.assertEqual(str(soup), expected_html)

    def test_convert_paragraph_to_searchable_hr_without_matching_paragraph_page_break_after(
        self,
    ):
        original_html = (
            "<p> column-break-after </p>"  # fails because of the extra whitespace
        )
        soup = BeautifulSoup(original_html, "html.parser")
        convert_paragraph_to_searchable_hr(soup.p)
        self.assertEqual(str(soup), original_html)

    def test_convert_paragraph_to_searchable_hr_with_multiple_matching_paragraphs_column_break_after(
        self,
    ):
        original_html = "<p>column-break-after</p><p>column-break-after</p>"
        expected_html = '<div class="page-break--hr--container"><hr class="column-break-after page-break--hr"/><span class="page-break--hr--text">[ → column-break-after → ]</span></div><div class="page-break--hr--container"><hr class="column-break-after page-break--hr"/><span class="page-break--hr--text">[ → column-break-after → ]</span></div>'
        soup = BeautifulSoup(original_html, "html.parser")
        for p in soup.find_all("p"):
            convert_paragraph_to_searchable_hr(p)
        self.assertEqual(str(soup), expected_html)

    def test_convert_paragraph_to_searchable_hr_with_nested_tags_column_break_after(
        self,
    ):
        original_html = "<div><p>column-break-after</p></div>"
        expected_html = '<div><div class="page-break--hr--container"><hr class="column-break-after page-break--hr"/><span class="page-break--hr--text">[ → column-break-after → ]</span></div></div>'
        soup = BeautifulSoup(original_html, "html.parser")
        convert_paragraph_to_searchable_hr(soup.p)
        self.assertEqual(str(soup), expected_html)


class SafeBrOnlyFilterTests(TestCase):

    def test_all_html_is_escaped_except_br(self):
        input_text = 'Line 1<br>Line 2<b>bold</b><script>alert("hi")</script>'
        expected = SafeString(
            "Line 1<br>Line 2&lt;b&gt;bold&lt;/b&gt;&lt;script&gt;alert(&quot;hi&quot;)&lt;/script&gt;"
        )
        result = safe_br(input_text)
        self.assertEqual(result, expected)

    def test_br_variants_are_normalized(self):
        input_text = "Line 1<BR/>Line 2<Br >Line 3<br >Line 4<BR >"
        expected = SafeString("Line 1<br>Line 2<br>Line 3<br>Line 4<br>")
        result = safe_br(input_text)
        self.assertEqual(result, expected)

    def test_escaping_angle_brackets(self):
        input_text = "This is <not a tag> and should be escaped"
        expected = SafeString("This is &lt;not a tag&gt; and should be escaped")
        result = safe_br(input_text)
        self.assertEqual(result, expected)

    def test_plain_text_remains_unchanged(self):
        input_text = "Just some normal text here."
        expected = SafeString("Just some normal text here.")
        result = safe_br(input_text)
        self.assertEqual(result, expected)

    def test_non_string_input_is_returned_as_is(self):
        self.assertEqual(safe_br(None), None)
        self.assertEqual(safe_br(42), 42)
        self.assertEqual(safe_br(True), True)


class TestFindElementsWithChar(TestCase):
    def test_single_element_with_char(self):
        html = "<div><span>~Test</span></div>"
        soup = BeautifulSoup(html, "html.parser")
        container = []
        find_elements_with_character(soup, container, "~")
        self.assertEqual(len(container), 1)
        self.assertEqual(container[0].name, "span")

    def test_nested_elements_with_char(self):
        html = "<div><p>~Test</p><span><em>~Another test</em></span></div>"
        soup = BeautifulSoup(html, "html.parser")
        container = []
        find_elements_with_character(soup, container, "~")
        self.assertEqual(len(container), 2)
        self.assertEqual({el.name for el in container}, {"p", "em"})

    def test_no_element_with_char(self):
        html = "<div><p>Test</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        container = []
        find_elements_with_character(soup, container, "~")
        self.assertEqual(len(container), 0)


class FilterBreadcrumbSectionsTests(TestCase):

    def setUp(self):
        # Mock sections as objects with a `name` attribute
        self.sections = [
            MockSection("Appendix: RESEP Outcomes Reporting System"),
            MockSection("Appendix B: Sample Attachment Templates"),
            MockSection("Appendix A: List of Eligible Applicants"),
            MockSection("Step 6. Learn What Happens After Award"),
            MockSection("Step 1: Review the Funding Opportunity"),
            MockSection("Appendix A: Additional Activity Detail"),
            MockSection("Step 4: Learn About Review and Award"),
            MockSection("Step 4: Learn About Review & Award"),
            MockSection("Step 3: Prepare Your Application"),
            MockSection("Appendix C: Glossary"),
            MockSection("Contacts and Support"),
            MockSection("Contacts & Support"),
        ]

    def test_filter_breadcrumb_sections(self):
        # Expected filtered sections
        expected_sections = [
            "Step 6. Learn What Happens After Award",
            "Step 1: Review the Funding Opportunity",
            "Step 4: Learn About Review and Award",
            "Step 4: Learn About Review & Award",
            "Step 3: Prepare Your Application",
            "Contacts and Support",
            "Contacts & Support",
        ]

        filtered_sections = filter_breadcrumb_sections(self.sections)

        # Extract names for comparison
        filtered_section_names = [section.name for section in filtered_sections]
        self.assertEqual(filtered_section_names, expected_sections)

    def test_empty_list_of_sections(self):
        filtered_sections = filter_breadcrumb_sections([])
        self.assertEqual(filtered_sections, [])

    def test_no_matching_sections(self):
        no_matching_sections = [
            MockSection("Appendix: Additional Notes"),
            MockSection("Glossary: Key Terms"),
            MockSection("Overview of Funding Opportunity"),
            MockSection("Appendix C: Glossary"),
        ]
        filtered_sections = filter_breadcrumb_sections(no_matching_sections)
        self.assertEqual(filtered_sections, [])


class GetBreadcrumbTextTests(TestCase):

    def test_get_breadcrumb_text(self):
        sections = [
            MockSection("Step 1: Review the Funding Opportunity"),
            MockSection("Step 3: Prepare Your Application"),
            MockSection("Step 3: Understand Review, Selection, and Award"),
            MockSection("Step 5: Learn What Happens After the Award"),
            MockSection("Step 5: Submit Your Application"),
            MockSection("Step 6: Learn What Happens After Award"),
            MockSection("Contacts and Support"),
            MockSection("Contacts & Support"),
            MockSection("Appendix A: List of Eligible Applicants"),
        ]

        expected_results = [
            ("Step 1: Review the Funding Opportunity", "Review"),
            ("Step 3: Prepare Your Application", "Prepare"),
            ("Step 3: Understand Review, Selection, and Award", "Understand"),
            ("Step 5: Learn What Happens After the Award", "Award"),
            ("Step 5: Submit Your Application", "Submit"),
            ("Step 6: Learn What Happens After Award", "Award"),
            ("Contacts and Support", "Contacts"),
            ("Contacts & Support", "Contacts"),
            ("Appendix A: List of Eligible Applicants", "⚠️ TODO ⚠️"),
        ]

        for section, expected in expected_results:
            with self.subTest(section=section):
                self.assertEqual(get_breadcrumb_text(section), expected)

    def test_case_insensitivity(self):
        self.assertEqual(
            get_breadcrumb_text("step 3: prepare your application"), "Prepare"
        )
        self.assertEqual(
            get_breadcrumb_text("STEP 3: PREPARE YOUR APPLICATION"), "Prepare"
        )

    def test_unmapped_section(self):
        self.assertEqual(
            get_breadcrumb_text("Appendix Z: Future Considerations"), "⚠️ TODO ⚠️"
        )


class TestGetParentTd(TestCase):
    def test_span_directly_inside_td(self):
        html = "<table><tr><td><span>Test</span></td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        span = soup.find("span")
        self.assertTrue(get_parent_td(span).name == "td")

    def test_span_nested_inside_td(self):
        html = "<table><tr><td><div><span>Test</span></div></td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        span = soup.find("span")
        self.assertTrue(get_parent_td(span).name == "td")

    def test_td_is_parent_td(self):
        html = "<table><tr><td>Test</td></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        td = soup.find("td")
        self.assertTrue(get_parent_td(td).name == "td")

    def test_span_not_inside_td(self):
        html = "<div><span>Test</span></div>"
        soup = BeautifulSoup(html, "html.parser")
        span = soup.find("span")
        self.assertFalse(get_parent_td(span))


class IsFootnoteRefTest(TestCase):
    def test_footnote_ref_true(self):
        tag = BeautifulSoup('<a href="#ftnt1">[1]</a>', "html.parser").a
        self.assertTrue(is_footnote_ref(tag))

    def test_footnote_ref_arrow_true(self):
        tag = BeautifulSoup('<a href="#ftnt1">↑</a>', "html.parser").a
        self.assertTrue(is_footnote_ref(tag))

    def test_footnote_ref_false(self):
        tag = BeautifulSoup('<a href="#section">Not a footnote</a>', "html.parser").a
        self.assertFalse(is_footnote_ref(tag))

    def test_footnote_ref_arrow_false(self):
        tag = BeautifulSoup('<a href="#section">Not a footnote ↑</a>', "html.parser").a
        self.assertFalse(is_footnote_ref(tag))

    def test_empty_tag(self):
        tag = BeautifulSoup('<a href="#ftnt1"></a>', "html.parser").a
        self.assertFalse(is_footnote_ref(tag))

    def test_non_footnote_format(self):
        tag = BeautifulSoup('<a href="#ftnt1">(1)</a>', "html.parser").a
        self.assertFalse(is_footnote_ref(tag))

    def test_footnote_ref_two_digits(self):
        tag = BeautifulSoup('<a href="#ftnt99">[99]</a>', "html.parser").a
        self.assertTrue(is_footnote_ref(tag))

    def test_footnote_ref_zero(self):
        tag = BeautifulSoup('<a href="#ftnt0">[0]</a>', "html.parser").a
        self.assertTrue(is_footnote_ref(tag))

    def test_footnote_ref_negative_one(self):
        tag = BeautifulSoup('<a href="#ftnt-1">[-1]</a>', "html.parser").a
        self.assertFalse(is_footnote_ref(tag))

    def test_footnote_ref_letter(self):
        tag = BeautifulSoup('<a href="#ftnt-a">[a]</a>', "html.parser").a
        self.assertFalse(is_footnote_ref(tag))


class GetFootnoteTypeTest(TestCase):
    def test_html_inline_footnote(self):
        html = '<a href="#ref10">[10]</a>'
        soup = BeautifulSoup(html, "html.parser")
        a_tag = soup.find("a")
        self.assertEqual(get_footnote_type(a_tag), "html")

    def test_html_endnote_footnote(self):
        html = '<a href="#ftnt_ref_10">[10]</a>'
        soup = BeautifulSoup(html, "html.parser")
        a_tag = soup.find("a")
        self.assertEqual(get_footnote_type(a_tag), "html")

    def test_docx_inline_footnote(self):
        html = '<sup><a href="#footnote-1" id="footnote-ref-1">[2]</a></sup>'
        soup = BeautifulSoup(html, "html.parser")
        a_tag = soup.find("a")
        self.assertEqual(get_footnote_type(a_tag), "docx")

    def test_docx_endnote_footnote(self):
        html = '<li id="footnote-1"><p> American Lung Association. <a href="https://etc">Asthma Trends and Burden</a>.  <a href="#footnote-ref-1">↑</a></p></li>'
        soup = BeautifulSoup(html, "html.parser")
        a_tag = soup.find("a", href="#footnote-ref-1")
        self.assertEqual(get_footnote_type(a_tag), "docx")

    def test_docx_inline_endnote(self):
        html = '<a href="#endnote-2" id="endnote-ref-2">[1]</a>'
        soup = BeautifulSoup(html, "html.parser")
        a_tag = soup.find("a")
        self.assertEqual(get_footnote_type(a_tag), "docx")

    def test_docx_endnote_footnote(self):
        html = '<li id="footnote-1"><p> American Lung Association. <a href="https://etc">Asthma Trends and Burden</a>.  <a href="#endnote-ref-2">↑</a></p></li>'
        soup = BeautifulSoup(html, "html.parser")
        a_tag = soup.find("a", href="#endnote-ref-2")
        self.assertEqual(get_footnote_type(a_tag), "docx")

    def test_no_footnote(self):
        html = '<a href="#some-other-link">[2]</a>'
        soup = BeautifulSoup(html, "html.parser")
        a_tag = soup.find("a")
        self.assertIsNone(get_footnote_type(a_tag))


class FormatFootnoteRefHTMLTest(TestCase):
    def test_format_footnote_ref_html_body(self):
        tag = BeautifulSoup('<a href="#ftnt1">[1]</a>', "html.parser").a
        format_footnote_ref_html(tag)
        self.assertEqual(tag.get("href"), "#ftnt1")
        self.assertEqual(tag.get("id"), "ftnt_ref1")

    def test_format_footnote_ref_html_endnote(self):
        tag = BeautifulSoup('<a href="#ftnt_ref1">[1]</a>', "html.parser").a
        format_footnote_ref_html(tag)
        self.assertEqual(tag.get("href"), "#ftnt_ref1")
        self.assertEqual(tag.get("id"), "ftnt1")

    def test_format_footnote_ref_html_body_overwrite_id_href(self):
        tag = BeautifulSoup(
            '<a href="#ftnt999" id="ftnt_ref999">[1]</a>', "html.parser"
        ).a
        format_footnote_ref_html(tag)
        self.assertEqual(tag.get("href"), "#ftnt1")
        self.assertEqual(tag.get("id"), "ftnt_ref1")

    def test_format_footnote_ref_html_endnote_overwrite_id(self):
        tag = BeautifulSoup(
            '<a href="#ftnt_ref999" id="ftnt999">[1]</a>', "html.parser"
        ).a
        format_footnote_ref_html(tag)
        self.assertEqual(tag.get("href"), "#ftnt_ref999")
        self.assertEqual(tag.get("id"), "ftnt1")


class TestIsFloatingCalloutBox(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.nofo = Nofo.objects.create(title="Test Nofo", opdiv="Test OpDiv")
        cls.section = Section.objects.create(name="Test Section", nofo=cls.nofo)

    def test_name_matches(self):
        """Test that the subsection is identified as a floating callout box by name."""
        names = [
            "Key facts",
            "Key Facts",
            "Key dates",
            "Key Dates",
            "Questions?",
            "Have questions?",
            "**Have questions?",
            "**Have** **questions?**",
        ]
        for index, name in enumerate(names):
            subsection = Subsection.objects.create(
                section=self.section,
                name=name,
                callout_box=True,
                tag="h4",  # needs a tag
                order=index
                + 2,  # Start from 2 since order=1 is taken by default subsection
            )
            self.assertTrue(is_floating_callout_box(subsection))

    def test_name_does_not_match(self):
        """Test subsections are not identified as floating callout boxes with an unrelated name."""
        subsection = Subsection.objects.create(
            section=self.section,
            name="Random name",
            callout_box=True,
            tag="h4",
            order=2,  # Use order=2 since order=1 is taken by default subsection
        )
        self.assertFalse(is_floating_callout_box(subsection))

    def test_wrong_casing_name_does_not_match(self):
        """Test subsections are not identified as floating callout boxes if the capitalization is wrong."""
        subsection = Subsection.objects.create(
            section=self.section,
            name="KEY FACTS",
            callout_box=True,
            tag="h4",
            order=2,  # Use order=2 since order=1 is taken by default subsection
        )
        self.assertFalse(is_floating_callout_box(subsection))

    def test_body_starts_with_valid_string(self):
        """Test subsections identified as floating callout boxes by body content."""
        valid_bodies = [
            "Key facts about something",
            "Key dates are important",
            "Questions? Ask here",
            "Have questions? We can help",
            "**Have questions? Contact us",
        ]
        for index, body in enumerate(valid_bodies):
            subsection = Subsection.objects.create(
                section=self.section,
                body=body,
                callout_box=True,
                order=index
                + 2,  # Start from 2 since order=1 is taken by default subsection
            )
            self.assertTrue(is_floating_callout_box(subsection))

    def test_body_does_not_start_with_valid_string(self):
        """Test subsections are not identified as floating callout boxes with unrelated body content."""
        subsection = Subsection.objects.create(
            section=self.section,
            body="The Administration on Disabilities (AoD) within...",
            callout_box=True,
            order=2,  # Use order=2 since order=1 is taken by default subsection
        )
        self.assertFalse(is_floating_callout_box(subsection))


class TestAddClassesToBrokenLinks(TestCase):

    def test_no_broken_links(self):
        html = '<div><a href="http://groundhog-day.com">Link</a></div>'
        broken_links = []
        modified_html = add_classes_to_broken_links(html, broken_links)
        soup = BeautifulSoup(str(modified_html), "html.parser")
        self.assertIsNone(soup.find("a", {"class": "nofo_edit--broken-link"}))

    def test_some_broken_links(self):
        html = '<div><a href="http://groundhog-day.com">Example</a><a href="#Appendix_A:__List_of_Eligible_Applicants">Broken Appendix Link</a></div>'
        broken_links = [{"link_href": "#Appendix_A:__List_of_Eligible_Applicants"}]
        modified_html = add_classes_to_broken_links(html, broken_links)
        soup = BeautifulSoup(str(modified_html), "html.parser")
        self.assertIn(
            "nofo_edit--broken-link",
            soup.find("a", {"href": "#Appendix_A:__List_of_Eligible_Applicants"}).get(
                "class"
            ),
        )

    def test_all_links_broken(self):
        html = '<div><a href="#Appendix_A:__List_of_Eligible_Applicants">Broken Appendix Link</a><a href="#_Purpose">Broken Purpose Link</a></div>'
        broken_links = [
            {"link_href": "#Appendix_A:__List_of_Eligible_Applicants"},
            {"link_href": "#_Purpose"},
        ]
        modified_html = add_classes_to_broken_links(html, broken_links)
        soup = BeautifulSoup(str(modified_html), "html.parser")
        self.assertEqual(len(soup.find_all("a", class_="nofo_edit--broken-link")), 2)

    def test_no_links_in_html(self):
        html = "<div>No links at all!</div>"
        broken_links = [{"link_href": "#_Purpose"}]
        modified_html = add_classes_to_broken_links(html, broken_links)
        soup = BeautifulSoup(str(modified_html), "html.parser")
        self.assertIsNone(soup.find("a"))


class MatchNumberedSublistTest(TestCase):

    def test_single_number(self):
        self.assertTrue(match_numbered_sublist("1. This is a list item."))

    def test_range_with_hyphen(self):
        self.assertTrue(match_numbered_sublist("8-15. This is a range."))

    def test_range_with_spaces_and_hyphen(self):
        self.assertTrue(match_numbered_sublist("16 - 21. Another range."))

    def test_range_with_through(self):
        self.assertTrue(match_numbered_sublist("22 through 25. With words."))

    def test_range_with_to(self):
        self.assertTrue(match_numbered_sublist("30 to 40. Another delimiter."))

    def test_range_with_emdash(self):
        self.assertTrue(match_numbered_sublist("45—50. Using emdash."))

    def test_range_with_spaces_and_emdash(self):
        self.assertTrue(match_numbered_sublist("1 — 1000. Using emdash and spaces."))

    def test_non_matching_text(self):
        self.assertFalse(match_numbered_sublist("Not a match."))

    def test_missing_period(self):
        self.assertFalse(match_numbered_sublist("1 This is invalid"))

    def test_no_space_after_period(self):
        self.assertFalse(match_numbered_sublist("1.This is invalid"))

    def test_invalid_number_format(self):
        self.assertFalse(match_numbered_sublist("abc123. Not valid"))

    def test_empty_string(self):
        self.assertFalse(match_numbered_sublist(""))


class WrapTextBeforeColonInStrongTests(TestCase):
    def test_simple_paragraph(self):
        """Test a basic paragraph with text before and after the colon."""
        html = "<p>Label: Value</p>"
        soup = BeautifulSoup(html, "html.parser")
        paragraph = soup.find("p")

        wrap_text_before_colon_in_strong(paragraph, soup)

        expected_html = "<p><strong>Label: </strong><span> Value</span></p>"
        self.assertEqual(str(paragraph), expected_html)

    def test_paragraph_with_link(self):
        """Test a paragraph with a link after the colon."""
        html = '<p>Link: <a href="https://example.com">Example</a></p>'
        soup = BeautifulSoup(html, "html.parser")
        paragraph = soup.find("p")

        wrap_text_before_colon_in_strong(paragraph, soup)

        expected_html = '<p><strong>Link: </strong><span> <a href="https://example.com">Example</a></span></p>'
        self.assertEqual(str(paragraph), expected_html)

    def test_no_colon(self):
        """Test a paragraph with no colon."""
        html = "<p>No colon here</p>"
        soup = BeautifulSoup(html, "html.parser")
        paragraph = soup.find("p")

        wrap_text_before_colon_in_strong(paragraph, soup)

        # In practice, we only call this func if there is a colon in the text string.
        expected_html = "<p>No colon here</p>"
        self.assertEqual(str(paragraph), expected_html)

    def test_multiple_colons(self):
        """Test a paragraph with multiple colons."""
        html = "<p>First: Second: Third</p>"
        soup = BeautifulSoup(html, "html.parser")
        paragraph = soup.find("p")

        wrap_text_before_colon_in_strong(paragraph, soup)

        # Only the first colon should be handled
        expected_html = "<p><strong>First: </strong><span> Second: Third</span></p>"
        self.assertEqual(str(paragraph), expected_html)

    def test_nested_elements(self):
        """Test a paragraph with nested elements before and after the colon."""
        html = '<p><span>Nested</span>: <ul><li><a href="https://example.com">Example</a></li></ul></p>'
        soup = BeautifulSoup(html, "html.parser")
        paragraph = soup.find("p")

        wrap_text_before_colon_in_strong(paragraph, soup)

        expected_html = '<p><strong><span>Nested</span>: </strong><span> <ul><li><a href="https://example.com">Example</a></li></ul></span></p>'
        self.assertEqual(str(paragraph), expected_html)

    def test_only_colon(self):
        """Test a paragraph with just a colon."""
        html = "<p>:</p>"
        soup = BeautifulSoup(html, "html.parser")
        paragraph = soup.find("p")

        wrap_text_before_colon_in_strong(paragraph, soup)

        expected_html = "<p><strong>: </strong><span></span></p>"
        self.assertEqual(str(paragraph), expected_html)

    def test_strong_with_colon_already(self):
        """Test a paragraph with a strong tag in a colon already."""
        html = "<p><strong>Opportunity Name:</strong> NOFO 100</p>"
        soup = BeautifulSoup(html, "html.parser")
        paragraph = soup.find("p")

        wrap_text_before_colon_in_strong(paragraph, soup)

        expected_html = "<p><strong>Opportunity Name:</strong> NOFO 100</p>"
        self.assertEqual(str(paragraph), expected_html)

    def test_strong_with_NO_colon_already(self):
        """Test a paragraph with a strong tag in a colon already."""
        html = "<p><strong>Opportunity</strong> Name: NOFO 100</p>"
        soup = BeautifulSoup(html, "html.parser")
        paragraph = soup.find("p")

        wrap_text_before_colon_in_strong(paragraph, soup)

        expected_html = "<p><strong><strong>Opportunity</strong> Name: </strong><span> NOFO 100</span></p>"
        self.assertEqual(str(paragraph), expected_html)
