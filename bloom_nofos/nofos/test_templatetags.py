import re
from unittest.mock import patch

from bs4 import BeautifulSoup
from django.test import TestCase

from .templatetags.utils import (
    _add_class_if_not_exists_to_tag,
    _add_class_if_not_exists_to_tags,
    _get_icon_path_from_theme,
    add_caption_to_table,
    add_class_to_table,
    add_class_to_table_rows,
    find_elements_with_character,
    format_footnote_ref,
    get_icon_from_theme,
    get_parent_td,
    is_footnote_ref,
)


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
        self.soup = BeautifulSoup(open(self.html_filename), "html.parser")

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
        table_html = "<table><thead><tr><th>Recommended For</th></tr></thead><tbody><tr><td>Cell content></tr></tbody></table>"
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--large")


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


class GetIconPathFromThemeTests(TestCase):
    def test_toc_section_with_white_colour(self):
        path = _get_icon_path_from_theme("landscape-cbc-white", "toc")
        self.assertEqual(path, "img/figma-icons/med-blue-border")

    def test_toc_section_non_white_colour(self):
        path = _get_icon_path_from_theme("landscape-cbc-blue", "toc")
        self.assertEqual(path, "img/figma-icons/white-icon")

    def test_before_you_begin_section_hrsa_opdiv(self):
        path = _get_icon_path_from_theme("theme-hrsa-blue", "before_you_begin")
        self.assertEqual(path, "img/figma-icons/dark-blue-border")

    def test_before_you_begin_section_cms_opdiv(self):
        path = _get_icon_path_from_theme("theme-cms-blue", "before_you_begin")
        self.assertEqual(path, "img/figma-icons/cms-blue-border")

    def test_before_you_begin_section_other_opdiv(self):
        path = _get_icon_path_from_theme("theme-cdc-blue", "before_you_begin")
        self.assertEqual(path, "img/figma-icons/med-blue-border")

    def test_callout_box_section_acf_white_theme(self):
        path = _get_icon_path_from_theme("theme-acf-white", "callout_box")
        self.assertEqual(path, "img/figma-icons/acf-black-border")

    def test_callout_box_section_acf_blue_theme(self):
        path = _get_icon_path_from_theme("theme-acf-blue", "callout_box")
        self.assertEqual(path, "img/figma-icons/white-border")

    def test_callout_box_section_white_theme(self):
        path = _get_icon_path_from_theme("theme-cdc-white", "callout_box")
        self.assertEqual(path, "img/figma-icons/dark-blue-border")

    def test_callout_box_section_any_nonwhite_theme(self):
        path = _get_icon_path_from_theme("theme-cdc-blue", "callout_box")
        self.assertEqual(path, "img/figma-icons/white-border")

    def test_section_cover_section_any_white_theme(self):
        path = _get_icon_path_from_theme("theme-cdc-white", "section_cover")
        self.assertEqual(path, "img/figma-icons/med-blue-border")

    def test_section_cover_section_cms_white_theme(self):
        path = _get_icon_path_from_theme("theme-cms-white", "section_cover")
        self.assertEqual(path, "img/figma-icons/white-border")

    def test_section_cover_section_acf_white_theme(self):
        path = _get_icon_path_from_theme("theme-acf-white", "section_cover")
        self.assertEqual(path, "img/figma-icons/acf-black-border")

    def test_section_cover_section_acf_blue_theme(self):
        path = _get_icon_path_from_theme("theme-acf-blue", "section_cover")
        self.assertEqual(path, "img/figma-icons/white-border")

    def test_section_cover_section_any_theme(self):
        path = _get_icon_path_from_theme("theme-cdc-blue", "section_cover")
        self.assertEqual(path, "img/figma-icons/white-border")

    def test_before_you_begin_section_dop_theme(self):
        path = _get_icon_path_from_theme("theme-cdc-dop", "section_cover")
        self.assertEqual(path, "img/figma-icons/white-border")

    def test_callout_box_section_dop_theme(self):
        path = _get_icon_path_from_theme("theme-cdc-dop", "section_cover")
        self.assertEqual(path, "img/figma-icons/white-border")

    def test_section_cover_section_dop_theme(self):
        path = _get_icon_path_from_theme("theme-cdc-dop", "section_cover")
        self.assertEqual(path, "img/figma-icons/white-border")

    def test_default_case(self):
        path = _get_icon_path_from_theme("any-theme-any-colour", "any-section")
        self.assertEqual(path, "img/figma-icons/white-border")


class GetIconFromThemeTests(TestCase):
    @patch("nofos.templatetags.utils._get_icon_path_from_theme")
    def test_icon_matching(self, mock_get_icon_path):
        mock_get_icon_path.return_value = "img/figma-icons/med-blue-border"
        # Test known icon name
        icon_path = get_icon_from_theme(
            "review the opportunity", "portrait-cdc-blue", "section_cover"
        )
        self.assertEqual(icon_path, "img/figma-icons/med-blue-border/1-review.svg")

    @patch("nofos.templatetags.utils._get_icon_path_from_theme")
    def test_icon_default_when_no_match(self, mock_get_icon_path):
        mock_get_icon_path.return_value = "img/figma-icons/med-blue-border"
        # Test an unknown icon name, which should default
        icon_path = get_icon_from_theme(
            "unknown icon", "portrait-cdc-blue", "section_cover"
        )
        self.assertEqual(icon_path, "img/figma-icons/med-blue-border/1-review.svg")

    @patch("nofos.templatetags.utils._get_icon_path_from_theme")
    def test_correct_path_construction(self, mock_get_icon_path):
        mock_get_icon_path.return_value = "img/figma-icons/custom-path"
        # Test correct path construction
        icon_path = get_icon_from_theme("write", "custom-theme", "custom_section")
        self.assertEqual(icon_path, "img/figma-icons/custom-path/3-write.svg")

    @patch("nofos.templatetags.utils._get_icon_path_from_theme")
    def test_correct_path_construction(self, mock_get_icon_path):
        mock_get_icon_path.return_value = "img/figma-icons/custom-path"
        # Test correct path construction
        icon_path = get_icon_from_theme(
            "prepare your application", "custom-theme", "custom_section"
        )
        self.assertEqual(icon_path, "img/figma-icons/custom-path/3-write.svg")


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

    def test_footnote_ref_false(self):
        tag = BeautifulSoup('<a href="#section">Not a footnote</a>', "html.parser").a
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


class FormatFootnoteRefTest(TestCase):
    def test_format_footnote_ref_body(self):
        tag = BeautifulSoup('<a href="#ftnt1">[1]</a>', "html.parser").a
        format_footnote_ref(tag)
        self.assertEqual(tag.get("href"), "#ftnt1")
        self.assertEqual(tag.get("id"), "ftnt_ref1")

    def test_format_footnote_ref_endnote(self):
        tag = BeautifulSoup('<a href="#ftnt_ref1">[1]</a>', "html.parser").a
        format_footnote_ref(tag)
        self.assertEqual(tag.get("href"), "#ftnt_ref1")
        self.assertEqual(tag.get("id"), "ftnt1")

    def test_format_footnote_ref_body_overwrite_id_href(self):
        tag = BeautifulSoup(
            '<a href="#ftnt999" id="ftnt_ref999">[1]</a>', "html.parser"
        ).a
        format_footnote_ref(tag)
        self.assertEqual(tag.get("href"), "#ftnt1")
        self.assertEqual(tag.get("id"), "ftnt_ref1")

    def test_format_footnote_ref_endnote_overwrite_id(self):
        tag = BeautifulSoup(
            '<a href="#ftnt_ref999" id="ftnt999">[1]</a>', "html.parser"
        ).a
        format_footnote_ref(tag)
        self.assertEqual(tag.get("href"), "#ftnt_ref999")
        self.assertEqual(tag.get("id"), "ftnt1")
