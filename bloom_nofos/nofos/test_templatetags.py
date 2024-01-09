from bs4 import BeautifulSoup

from django.test import TestCase

from .templatetags.utils import (
    add_caption_to_table,
    add_class_to_table,
    find_elements_with_character,
    get_icon_for_section,
    get_parent_td,
    is_footnote_ref,
    format_footnote_ref,
)


class AddCaptionToTableTests(TestCase):
    def setUp(self):
        self.caption_text = "Physician Assistant Training Chart"
        self.html_filename = "nofos/fixtures/html/table.html"
        self.soup = BeautifulSoup(open(self.html_filename), "html.parser")

    def test_table_before_add_caption_to_table(self):
        table = self.soup.find("table")

        # table doesn't have a caption
        self.assertIsNone(table.find("caption"))

        # there is a paragraph tag with the caption
        paragraph = self.soup.find("p", string=self.caption_text)
        self.assertIsNotNone(paragraph)

        # the paragraph tag has a span inside of it
        self.assertIsNotNone(paragraph.find("span"))

    def test_table_after_add_caption_to_table(self):
        table = self.soup.find("table")
        add_caption_to_table(table)

        # no paragraph tag with the caption
        paragraph = self.soup.find("p", string=self.caption_text)
        self.assertIsNone(paragraph)

        # table DOES have a caption
        caption = table.find("caption", string=self.caption_text)
        self.assertIsNotNone(caption)

        # the caption tag has a span inside of it
        self.assertIsNotNone(caption.find("span"))


class HTMLTableClassTests(TestCase):
    def _generate_table(self, num_cols, num_rows=1, cell="td"):
        rows = ""
        for j in range(num_rows):
            cols = ""
            for i in range(num_cols):
                cols += "<{0}>Col {1}</{0}>".format(cell, i + 1)
            rows += "<tr>{}</tr>".format(cols)

        return "<table>{}</table>".format(rows)

    def test_table_class_sm(self):
        table_html = self._generate_table(num_cols=2)
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--small")

    def test_table_class_md(self):
        table_html = self._generate_table(num_cols=4)
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--medium")

    def test_table_class_lg(self):
        table_html = self._generate_table(num_cols=5)
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--large")

    def test_table_class_lg_with_th(self):
        table_html = self._generate_table(num_cols=10, cell="th")

        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--large")

    def test_table_class_lg_with_th_2_rows(self):
        # generate a table with 2 rows
        table_html = self._generate_table(num_cols=10, num_rows=2, cell="th")

        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--large")

    def test_table_class_md_rows(self):
        table_html = self._generate_table(num_cols=2, num_rows=6)
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--medium")

    def test_table_class_lg_rows(self):
        table_html = self._generate_table(num_cols=2, num_rows=7)
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--large")

    def test_table_class_md_md(self):
        table_html = self._generate_table(num_cols=4, num_rows=6)
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--medium")


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


class GetIconForSectionTests(TestCase):
    def test_default_parameters(self):
        """Test the function with default parameters."""
        self.assertEqual(get_icon_for_section(), "img/figma-icons/1-review.svg")

    def test_different_section(self):
        """Test the function with a different section."""
        self.assertEqual(get_icon_for_section("write"), "img/figma-icons/3-write.svg")

    def test_no_matching_section(self):
        """Test the function with a non-existent section."""
        self.assertEqual(
            get_icon_for_section("non-existent section"),
            "img/figma-icons/1-review.svg",
        )

    def test_partial_match(self):
        """Test the function with a partial match."""
        self.assertEqual(get_icon_for_section("review"), "img/figma-icons/1-review.svg")

    def test_case_insensitivity(self):
        """Test the function with case-insensitive input."""
        self.assertEqual(
            get_icon_for_section("ReViEw ThE OpPoRtUnItY"),
            "img/figma-icons/1-review.svg",
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
