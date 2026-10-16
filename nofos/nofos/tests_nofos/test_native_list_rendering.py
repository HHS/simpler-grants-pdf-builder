"""Source marker semantics survive conversion and configured sanitization."""

from bs4 import BeautifulSoup
from django.test import SimpleTestCase
from martor.templatetags.martortags import safe_markdown

from nofos.content_processing import join_nested_lists, unwrap_nested_lists
from nofos.nofo_markdown import md


class NativeListRenderingTests(SimpleTestCase):
    def render(self, html):
        body = md(html)
        return body, BeautifulSoup(safe_markdown(body), "html.parser")

    def test_typed_tree_retains_every_descendant_and_surrounding_markdown(self):
        for marker in ("a", "A", "i", "I"):
            with self.subTest(marker=marker):
                body, rendered = self.render(
                    "<p>Before <strong>the list</strong>.</p>"
                    f'<ol type="{marker}" data-nofo-source-list="1"><li>'
                    "First <em>activity</em><ul><li>Bulleted instruction"
                    '<ol type="1"><li>Decimal criterion '
                    '<a href="https://example.org/criteria">details</a></li></ol>'
                    "</li></ul></li><li>Second activity</li></ol><p>After.</p>"
                )
                root = rendered.find("ol")
                self.assertEqual(root["type"], marker)
                self.assertEqual(root.find("ol")["type"], "1")
                self.assertEqual(len(root.find_all("li")), 4)
                self.assertIsNotNone(root.find("ul").find("ol"))
                self.assertEqual(root.find("a")["href"], "https://example.org/criteria")
                self.assertIsNotNone(root.find("em"))
                self.assertEqual(rendered.find_all("p")[-1].get_text(), "After.")
                self.assertNotIn("data-nofo-source-list", body)
                self.assertNotIn("* Bulleted", body)
                self.assertIn("**the list**", body)

    def test_nondecimal_or_start_descendant_preserves_entire_parent_tree(self):
        for nested in ('type="i"', 'type="1"', 'start="4"'):
            with self.subTest(nested=nested):
                _, rendered = self.render(
                    "<ul><li>Parent<ol " + nested + "><li>Child</li></ol></li></ul>"
                )
                self.assertEqual(rendered.ul.li.ol.li.get_text(), "Child")
                self.assertEqual(len(rendered.find_all("li")), 2)

    def test_simple_lists_keep_existing_readable_markdown_and_indent(self):
        for html, expected in (
            ('<ol type="1"><li>First</li><li>Second</li></ol>', "1. First\n2. Second"),
            (
                "<ul><li>Parent<ul><li>Child</li></ul></li></ul>",
                "* Parent\n    + Child",
            ),
        ):
            with self.subTest(html=html):
                body, _ = self.render(html)
                self.assertEqual(body.strip(), expected)

    def test_simple_list_continuation_does_not_absorb_following_item(self):
        for tag in ("ol", "ul"):
            with self.subTest(tag=tag):
                body, rendered = self.render(
                    f"<{tag}><li>First<p>Explanation</p></li><li>Second</li></{tag}>"
                )
                self.assertEqual(len(rendered.find_all("li")), 2)
                self.assertEqual(rendered.find_all("li")[1].get_text(), "Second")
                self.assertEqual(
                    rendered.find("p").find_parent("li").get_text(), "FirstExplanation"
                )

    def test_typed_table_lists_keep_literal_asterisks_in_both_cell_types(self):
        for cell in ("td", "th"):
            for tag in ("ol", "ul"):
                with self.subTest(cell=cell, tag=tag):
                    _, rendered = self.render(
                        "<table><tr><th>Header</th><th>Other</th></tr><tr>"
                        f'<{cell}><{tag} type="a"><li>First *star*</li>'
                        f"<li>Second</li></{tag}></{cell}><td>More</td></tr></table>"
                    )
                    self.assertIsNone(rendered.find("em"))
                    self.assertIn("First *star*", rendered.get_text())

    def test_nonone_start_discards_internal_source_marker(self):
        body, rendered = self.render(
            '<p>Before.</p><ol type="a" start="3" data-nofo-source-list="true">'
            "<li>Third</li></ol><p>After.</p>"
        )
        self.assertEqual(rendered.ol["start"], "3")
        self.assertNotIn("data-nofo-source-list", body)
        self.assertEqual(rendered.find_all("p")[-1].text, "After.")

    def test_source_tree_is_not_reinterpreted_by_legacy_repairs(self):
        soup = BeautifulSoup(
            '<ol type="a" class="lst-one" data-nofo-source-list="1">'
            '<li>Parent<ol type="i"><li>Child</li></ol></li></ol>'
            '<ol type="a" class="lst-one" data-nofo-source-list="2">'
            "<li>Restart</li></ol>",
            "html.parser",
        )
        join_nested_lists(soup)
        unwrap_nested_lists(soup)
        self.assertEqual(len(soup.find_all("ol", recursive=False)), 2)
        self.assertEqual(len(soup.find_all("li")), 3)

    def test_same_class_merge_does_not_duplicate_nested_children(self):
        soup = BeautifulSoup(
            '<ul class="lst-one"><li>First</li></ul>'
            '<ul class="lst-one"><li>Second<ul><li>Child</li></ul></li></ul>',
            "html.parser",
        )
        join_nested_lists(soup)
        self.assertEqual(len(soup.find_all("li")), 3)
        self.assertEqual(soup.ul.find_all("li", recursive=False)[1].ul.li.text, "Child")

    def test_independent_explicit_marker_and_restart_boundaries_remain(self):
        for second in ('type="i"', 'type="a" start="3"'):
            with self.subTest(second=second):
                soup = BeautifulSoup(
                    '<ol type="a" class="lst-one"><li>First</li></ol>'
                    f'<ol {second} class="lst-one"><li>Second</li></ol>',
                    "html.parser",
                )
                join_nested_lists(soup)
                self.assertEqual(len(soup.find_all("ol", recursive=False)), 2)

    def test_legacy_mixed_list_classes_still_encode_nesting(self):
        for parent, child in (("ul", "ol"), ("ol", "ul")):
            with self.subTest(parent=parent, child=child):
                soup = BeautifulSoup(
                    f'<{parent} class="lst-parent"><li>Parent</li></{parent}>'
                    f'<{child} class="lst-child"><li>Child</li></{child}>',
                    "html.parser",
                )
                join_nested_lists(soup)
                self.assertEqual(len(soup.find_all(["ul", "ol"], recursive=False)), 1)
                self.assertEqual(
                    soup.find(parent).li.find(child).li.get_text(), "Child"
                )
