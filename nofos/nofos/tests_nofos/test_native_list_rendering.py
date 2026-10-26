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

    def test_adjacent_independent_lists_retain_boundaries_after_rendering(self):
        for tag in ("ol", "ul"):
            with self.subTest(tag=tag):
                body, rendered = self.render(
                    f"<{tag}><li>First group</li></{tag}>\n"
                    f"<{tag}><li>New group</li></{tag}>"
                )
                lists = rendered.find_all(tag, recursive=False)
                self.assertEqual(len(lists), 2)
                self.assertEqual(
                    [el.li.text for el in lists], ["First group", "New group"]
                )
                self.assertIn(f"<{tag}>", body)

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

    def test_adjacent_mixed_lists_preserve_types_items_and_inline_content(self):
        for first, second in (("ul", "ol"), ("ol", "ul")):
            for separator in ("", "\n", " \n "):
                with self.subTest(first=first, separator=separator):
                    body, rendered = self.render(
                        "<p>Before.</p>"
                        f"<{first}><li>First <strong>group</strong></li>"
                        f"<li>Another item</li></{first}>"
                        + separator
                        + f"<{second}><li>Second <em>group</em> "
                        '<a href="https://example.org/apply">apply</a></li>'
                        f"<li>Last item</li></{second}><p>After.</p>"
                    )
                    lists = rendered.find_all(["ul", "ol"], recursive=False)
                    self.assertEqual([tag.name for tag in lists], [first, second])
                    self.assertEqual(
                        [
                            [
                                li.get_text()
                                for li in tag.find_all("li", recursive=False)
                            ]
                            for tag in lists
                        ],
                        [
                            ["First group", "Another item"],
                            ["Second group apply", "Last item"],
                        ],
                    )
                    self.assertEqual(lists[0].strong.text, "group")
                    self.assertEqual(lists[1].em.text, "group")
                    self.assertEqual(lists[1].a["href"], "https://example.org/apply")
                    self.assertEqual(
                        [p.text for p in rendered.find_all("p", recursive=False)],
                        ["Before.", "After."],
                    )
                    self.assertIn(f"<{first}>", body)
                    self.assertIn(f"<{second}>", body)

    def test_adjacent_mixed_children_preserve_the_entire_parent_tree(self):
        for parent in ("ul", "ol"):
            for first, second in (("ul", "ol"), ("ol", "ul")):
                with self.subTest(parent=parent, first=first):
                    _, rendered = self.render(
                        f"<{parent}><li>Parent<{first}><li>Child one</li></{first}>"
                        f"<{second}><li>Child two</li></{second}></li>"
                        f"<li>Next parent</li></{parent}>"
                    )
                    root = rendered.find(parent, recursive=False)
                    items = root.find_all("li", recursive=False)
                    self.assertEqual(len(items), 2)
                    self.assertEqual(items[1].text, "Next parent")
                    children = items[0].find_all(["ul", "ol"], recursive=False)
                    self.assertEqual([tag.name for tag in children], [first, second])
                    self.assertEqual(
                        [tag.li.text for tag in children], ["Child one", "Child two"]
                    )
                    self.assertEqual(len(rendered.find_all("li")), 4)

    def test_mixed_list_chain_keeps_each_boundary(self):
        for tags in (("ul", "ol", "ul"), ("ol", "ul", "ol")):
            with self.subTest(tags=tags):
                _, rendered = self.render(
                    "\n".join(
                        f"<{tag}><li>Group {index}</li></{tag}>"
                        for index, tag in enumerate(tags)
                    )
                )
                lists = rendered.find_all(["ul", "ol"], recursive=False)
                self.assertEqual([tag.name for tag in lists], list(tags))
                self.assertEqual(
                    [tag.li.text for tag in lists], ["Group 0", "Group 1", "Group 2"]
                )

    def test_prose_separated_simple_lists_still_use_markdown(self):
        for first, second in (("ul", "ol"), ("ol", "ul")):
            with self.subTest(first=first):
                body, rendered = self.render(
                    f"<{first}><li>First</li></{first}><p>Boundary.</p>"
                    f"<{second}><li>Second</li></{second}>"
                )
                self.assertNotIn("<ul", body)
                self.assertNotIn("<ol", body)
                self.assertEqual(
                    [
                        tag.name
                        for tag in rendered.find_all(["ul", "ol"], recursive=False)
                    ],
                    [first, second],
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
