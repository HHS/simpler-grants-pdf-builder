from django.test import TestCase

from ..html_diff import html_diff


class TestHtmlDiffStrings(TestCase):

    def test_basic_text_change(self):
        original = "Groundhog Day!"
        new = "Valentines Day!"
        expected = "<del>Groundhog</del><ins>Valentines</ins> Day!"
        self.assertEqual(html_diff(original, new), expected)

    def test_whitespace_only_change(self):
        original = "Groundhog      Day!"
        new = "Groundhog Day!"
        expected = "Groundhog Day!"
        self.assertEqual(html_diff(original, new), expected)

    def test_identical_strings(self):
        original = "Groundhog Day!"
        new = "Groundhog Day!"
        expected = "Groundhog Day!"
        self.assertEqual(html_diff(original, new), expected)

    def test_empty_strings(self):
        original = ""
        new = ""
        expected = ""
        self.assertEqual(html_diff(original, new), expected)

    def test_Nones(self):
        original = None
        new = None
        expected = ""
        self.assertEqual(html_diff(original, new), expected)

    def test_None_and_empty(self):
        original = None
        new = ""
        expected = ""
        self.assertEqual(html_diff(original, new), expected)

    def test_text_added(self):
        original = "Groundhog"
        new = "Groundhog Day"
        expected = "Groundhog<ins> Day</ins>"
        self.assertEqual(html_diff(original, new), expected)

    def test_text_removed(self):
        original = "Groundhog Day"
        new = "Day"
        expected = "<del>Groundhog </del>Day"
        self.assertEqual(html_diff(original, new), expected)

    def test_replace_with_partial_whitespace(self):
        original = "Groundhog Day!"
        new = "Groundhog Day! (1993)"
        expected = "Groundhog Day!<ins> (1993)</ins>"
        self.assertEqual(html_diff(original, new), expected)

    def test_empty_input(self):
        self.assertEqual(html_diff("", ""), "")
        self.assertEqual(html_diff("", "Groundhog"), "<ins>Groundhog</ins>")  # insert
        self.assertEqual(html_diff("Groundhog", ""), "<del>Groundhog</del>")  # delete


class TestHtmlDiffHTMLStructure(TestCase):
    def test_identical_html_returns_same(self):
        html = "<p>Hello world</p>"
        self.assertEqual(html_diff(html, html), html)

    def test_single_paragraph_change(self):
        original = "<p>This sentence has been changed.</p>"
        modified = "<p>This sentence has been altered in some way.</p>"
        expected = "<p>This sentence has been <del>changed</del><ins>altered in some way</ins>.</p>"
        self.assertEqual(html_diff(original, modified), expected)

    def test_multiple_paragraphs_with_single_paragraph_change(self):
        original = """
<p>This sentence has NOT changed.</p>
<p>This sentence has been changed.</p>
<p>This sentence has NOT changed.</p>
"""
        modified = """
<p>This sentence has NOT changed.</p>
<p>This sentence has been altered in some way.</p>
<p>This sentence has NOT changed.</p>
"""

        expected = "<p>This sentence has NOT changed.</p><p>This sentence has been <del>changed</del><ins>altered in some way</ins>.</p><p>This sentence has NOT changed.</p>"
        self.assertEqual(html_diff(original, modified), expected)

    def test_adding_a_paragraph_after(self):
        original = """
<p>This sentence has NOT changed.</p>
"""
        modified = """
<p>This sentence has NOT changed.</p>
<p>This sentence is new.</p>
"""

        expected = "<p>This sentence has NOT changed.</p><ins><p>This sentence is new.</p></ins>"
        self.assertEqual(html_diff(original, modified), expected)

    def test_adding_a_paragraph_before(self):
        original = """
<p>This sentence has NOT changed.</p>
"""
        modified = """
<p>This sentence is new.</p>
<p>This sentence has NOT changed.</p>
"""

        expected = "<ins><p>This sentence is new.</p></ins><p>This sentence has NOT changed.</p>"
        self.assertEqual(html_diff(original, modified), expected)

    def test_deleting_a_paragraph_after(self):
        original = """
<p>This sentence will be deleted.</p>
<p>This sentence has NOT changed.</p>
"""
        modified = """
<p>This sentence has NOT changed.</p>
"""

        expected = "<del><p>This sentence will be deleted.</p></del><p>This sentence has NOT changed.</p>"
        assert html_diff(original, modified) == expected

    def test_matching_in_both_directions(self):
        original = """
<p>Sentence 1</p>
<p>Sentence 2</p>
<p>Sentence 3</p>
<p>Sentence 4</p>
<p>Sentence 5</p>
<p>Sentence 6</p>
"""

        modified = """
<p>Sentence 3</p>
<p>Sentence 3.5</p>
<p>Sentence 3.10</p>
<p>Sentence 5</p>
<p>Sentence 6</p>
<p>Sentence 7</p>
<p>Sentence 8</p>
"""

        expected = """
<del><p>Sentence 1</p></del>
<del><p>Sentence 2</p></del>
<p>Sentence 3</p>
<p>Sentence <del>4</del><ins>3.5</ins></p>
<ins><p>Sentence 3.10</p></ins>
<p>Sentence 5</p>
<p>Sentence 6</p>
<ins><p>Sentence 7</p></ins>
<ins><p>Sentence 8</p></ins>
"""
        self.assertEqual(
            html_diff(original, modified).replace("\n", ""), expected.replace("\n", "")
        )

    def test_multiple_matches_unequal_blocks(self):
        original = """
<p>Sentence 1</p>
<p>Sentence 2</p>
<p>Sentence 3</p>
<p>Sentence 4</p>
<p>Sentence 4.5</p>
<p>Sentence 6</p>
<p>Sentence 9</p>
"""

        modified = """
<p>Sentence 3</p>
<p>Sentence 3.1</p>
<p>Sentence 3.2</p>
<p>Sentence 3.3</p>
<p>Sentence 3.4</p>
<p>Sentence 5</p>
<p>Sentence 6</p>
<p>Sentence 7</p>
<p>Sentence 8</p>
<p>Sentence 9</p>
"""

        expected = """
<del><p>Sentence 1</p></del>
<del><p>Sentence 2</p></del>
<p>Sentence 3</p>
<p>Sentence <del>4</del><ins>3.1</ins></p>
<p>Sentence <del>4.5</del><ins>3.2</ins></p>
<ins><p>Sentence 3.3</p></ins>
<ins><p>Sentence 3.4</p></ins>
<ins><p>Sentence 5</p></ins>
<p>Sentence 6</p>
<ins><p>Sentence 7</p></ins>
<ins><p>Sentence 8</p></ins>
<p>Sentence 9</p>
"""
        self.assertEqual(
            html_diff(original, modified).replace("\n", ""), expected.replace("\n", "")
        )

    def test_paragraph_with_bold_formatting(self):
        original = "<p>This sentence has been changed.</p>"
        modified = "<p>This sentence has been <strong>changed</strong>.</p>"
        expected = "<p>This sentence has been changed.</p>"
        self.assertEqual(html_diff(original, modified), expected)

    def test_paragraph_with_em_formatting(self):
        original = "<p>This sentence has been changed.</p>"
        modified = "<p>This sentence has been <em>changed</strong>.</p>"
        expected = "<p>This sentence has been changed.</p>"
        self.assertEqual(html_diff(original, modified), expected)

    def test_heading_level_change(self):
        original = "<h3>This heading level changes.</h3>"
        modified = "<h4>This heading level changes.</h4>"
        expected = "<del><h3>This heading level changes.</h3></del><ins><h4>This heading level changes.</h4></ins>"
        self.assertEqual(html_diff(original, modified), expected)

    def test_link_href_change(self):
        original = "<p>This links to <a href='https://groundhog-day.com'>the best site ever</a>.</p>"
        modified = (
            "<p>This links to <a href='https://taxgpt.ca'>the best site ever</a>.</p>"
        )
        expected = "<p>This links to the best site ever.</p>"
        self.assertEqual(html_diff(original, modified), expected)

    def test_list_item_changed(self):
        original = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed.</li>
<li>This list item has changed.</li>
<li>This list item has not changed.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""
        modified = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed.</li>
<li>This list item has been lightly edited.</li>
<li>This list item has not changed.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        expected = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed.</li>
<li>This list item has <del>chang</del><ins>been lightly edit</ins>ed.</li>
<li>This list item has not changed.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        self.assertEqual(
            html_diff(original, modified).replace("\n", ""), expected.replace("\n", "")
        )

    def test_list_item_added(self):
        original = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has not changed 2.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""
        modified = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item is completely new.</li>
<li>This list item has not changed 2.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        expected = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li><ins>This list item is completely new.</ins></li>
<li>This list item has not changed 2.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        self.assertEqual(
            html_diff(original, modified).replace("\n", ""), expected.replace("\n", "")
        )

    def test_list_item_deleted(self):
        original = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item will be removed.</li>
<li>This list item has not changed 2.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""
        modified = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has not changed 2.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        expected = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li><del>This list item will be removed.</del></li>
<li>This list item has not changed 2.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        self.assertEqual(
            html_diff(original, modified).replace("\n", ""), expected.replace("\n", "")
        )

    def test_list_item_moved_lower(self):
        original = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item will be moved lower.</li>
<li>This list item has not changed 2.</li>
<li>This list item has not changed 3.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""
        modified = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has not changed 2.</li>
<li>This list item will be moved lower.</li>
<li>This list item has not changed 3.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        expected = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li><ins>This list item has not changed 2.</ins></li>
<li>This list item will be moved lower.</li>
<li><del>This list item has not changed 2.</del></li>
<li>This list item has not changed 3.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        self.assertEqual(
            html_diff(original, modified).replace("\n", ""), expected.replace("\n", "")
        )

    def test_list_item_moved_higher(self):
        original = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has not changed 2.</li>
<li>This list item will be moved higher.</li>
<li>This list item has not changed 3.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""
        modified = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item will be moved higher.</li>
<li>This list item has not changed 2.</li>
<li>This list item has not changed 3.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        expected = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li><ins>This list item will be moved higher.</ins></li>
<li>This list item has not changed 2.</li>
<li><del>This list item will be moved higher.</del></li>
<li>This list item has not changed 3.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        self.assertEqual(
            html_diff(original, modified).replace("\n", ""), expected.replace("\n", "")
        )

    def test_nested_list_item_changed(self):
        original = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has not changed 2.
<ul>
<li>This nested list item has not changed 1.</li>
<li>This nested list item has been changed.</li>
<li>This nested list item has not changed 2.</li>
</ul>
</li>
<li>This list item has not changed 3.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""
        modified = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has not changed 2.
<ul>
<li>This nested list item has not changed 1.</li>
<li>This nested list item has been rewritten.</li>
<li>This nested list item has not changed 2.</li>
</ul>
</li>
<li>This list item has not changed 3.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        expected = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has not changed 2.
<ul>
<li>This nested list item has not changed 1.</li>
<li>This nested list item has been <del>changed</del><ins>rewritten</ins>.</li>
<li>This nested list item has not changed 2.</li>
</ul>
</li>
<li>This list item has not changed 3.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        self.assertEqual(
            html_diff(original, modified).replace("\n", ""), expected.replace("\n", "")
        )

    def test_nested_list_item_moved_down(self):
        original = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has not changed 2.
<ul>
<li>This nested list item has been moved.</li>
<li>This nested list item has not changed 1.</li>
<li>This nested list item has not changed 2.</li>
</ul>
</li>
<li>This list item has not changed 3.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""
        modified = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has not changed 2.
<ul>
<li>This nested list item has not changed 1.</li>
<li>This nested list item has not changed 2.</li>
<li>This nested list item has been moved.</li>
</ul>
</li>
<li>This list item has not changed 3.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        expected = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has not changed 2.
<ul>
<li><del>This nested list item has been moved.</del></li>
<li>This nested list item has not changed 1.</li>
<li>This nested list item has not changed 2.</li>
<li><ins>This nested list item has been moved.</ins></li>
</ul>
</li>
<li>This list item has not changed 3.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        self.assertEqual(
            html_diff(original, modified).replace("\n", ""), expected.replace("\n", "")
        )

    def test_nested_list_item_moved_up(self):
        original = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has not changed 2.
<ul>
<li>This nested list item has not changed 1.</li>
<li>This nested list item has not changed 2.</li>
<li>This nested list item has been moved.</li>
</ul>
</li>
<li>This list item has not changed 3.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""
        modified = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has not changed 2.
<ul>
<li>This nested list item has been moved.</li>
<li>This nested list item has not changed 1.</li>
<li>This nested list item has not changed 2.</li>
</ul>
</li>
<li>This list item has not changed 3.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        expected = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has not changed 2.
<ul>
<li><ins>This nested list item has been moved.</ins></li>
<li>This nested list item has not changed 1.</li>
<li>This nested list item has not changed 2.</li>
<li><del>This nested list item has been moved.</del></li>
</ul>
</li>
<li>This list item has not changed 3.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        self.assertEqual(
            html_diff(original, modified).replace("\n", ""), expected.replace("\n", "")
        )

    def test_nested_list_item_moved_after_nested_list(self):
        original = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has been moved lower.</li>
<li>This list item has not changed 2.
<ul>
<li>This nested list item has not changed 1.</li>
<li>This nested list item has not changed 2.</li>
</ul>
</li>
<li>This list item has not changed 3.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""
        modified = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has not changed 2.
<ul>
<li>This nested list item has not changed 1.</li>
<li>This nested list item has not changed 2.</li>
</ul>
</li>
<li>This list item has not changed 3.</li>
<li>This list item has been moved lower.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        expected = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li><del>This list item has been moved lower.</del></li>
<li>This list item has not changed 2.
<ul>
<li>This nested list item has not changed 1.</li>
<li>This nested list item has not changed 2.</li>
</ul>
</li>
<li>This list item has not changed 3.</li>
<li><ins>This list item has been moved lower.</ins></li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        self.assertEqual(
            html_diff(original, modified).replace("\n", ""), expected.replace("\n", "")
        )

    def test_nested_list_item_moved_into_nested_list(self):
        original = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has been moved into the nested list.</li>
<li>This list item has not changed 2.
<ul>
<li>This nested list item has not changed 1.</li>
<li>This nested list item has not changed 2.</li>
</ul>
</li>
<li>This list item has not changed 3.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""
        modified = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has not changed 2.
<ul>
<li>This nested list item has not changed 1.</li>
<li>This list item has been moved into the nested list.</li>
<li>This nested list item has not changed 2.</li>
</ul>
</li>
<li>This list item has not changed 3.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        expected = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has <del>been moved into the nested list.</del><ins>not changed 2.</ins>
<ins><ul>
<li>This nested list item has not changed 1.</li>
<li>This list item has been moved into the nested list.</li>
<li>This nested list item has not changed 2.</li>
</ul></ins>
</li>
<li><del>This list item has not changed 2.<ul><li>This nested list item has not changed 1.</li><li>This nested list item has not changed 2.</li></ul></del></li>
<li>This list item has not changed 3.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        self.assertEqual(
            html_diff(original, modified).replace("\n", ""), expected.replace("\n", "")
        )

    def test_table_diff(self):
        original = """
<table class="table--small">
<thead>
<tr>
<th>Heading 1</th>
<th>Heading 2</th>
</tr>
</thead>
<tbody>
<tr>
<td>This cell has not been changed</td>
<td><p>This cell has a list</p><ul><li>This list item has not been changed</li><li class="avoid-page-break-before">This list item has been changed</li></ul></td>
</tr>
<tr>
<td>This cell has been changed</td>
<td>This cell has had all of its text removed</td>
</tr>
</tbody>
</table>
"""
        modified = """
<table class="table--small">
<thead>
<tr>
<th>Heading 1</th>
<th>Heading 2</th>
</tr>
</thead>
<tbody>
<tr>
<td>This cell has not been changed</td>
<td><p>This cell has a list</p><ul><li>This list item has not been changed</li><li class="avoid-page-break-before">This list item has been altered</li></ul></td>
</tr>
<tr>
<td>This cell has been edited to add some more words</td>
<td></td>
</tr>
</tbody>
</table>
"""

        expected = """<table>
<thead>
<tr>
<th>Heading 1</th>
<th>Heading 2</th>
</tr>
</thead>
<tbody>
<tr>
<td>This cell has not been changed</td>
<td><p>This cell has a list</p><ul><li>This list item has not been changed</li><li>This list item has been <del>chang</del><ins>alter</ins>ed</li></ul></td>
</tr>
<tr>
<td>This cell has been <del>changed</del><ins>edited to add some more words</ins></td>
<td><del>This cell has had all of its text removed</del></td>
</tr>
</tbody>
</table>"""

        self.assertEqual(
            html_diff(original, modified).replace("\n", ""), expected.replace("\n", "")
        )

    def test_pure_insert(self):
        original = ""

        modified = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has not changed 2.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        expected = """
<ins><p>This sentence has NOT changed.</p></ins>
<ins>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has not changed 2.</li>
</ul>
</ins>
<ins><p>This sentence has NOT changed.</p></ins>
"""

        self.assertEqual(
            html_diff(original, modified).replace("\n", ""), expected.replace("\n", "")
        )

    def test_pure_delete(self):
        original = """
<p>This sentence has NOT changed.</p>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has not changed 2.</li>
</ul>
<p>This sentence has NOT changed.</p>
"""

        modified = ""

        expected = """
<del><p>This sentence has NOT changed.</p></del>
<del>
<ul>
<li>This list item has not changed 1.</li>
<li>This list item has not changed 2.</li>
</ul>
</del>
<del><p>This sentence has NOT changed.</p></del>
"""

        self.assertEqual(
            html_diff(original, modified).replace("\n", ""), expected.replace("\n", "")
        )

    def test_string_diff(self):
        original = "NOFO-123-456-789"

        modified = "NOFO-123-444-777"

        expected = "NOFO-123-4<del>56-789</del><ins>44-777</ins>"

        self.assertEqual(html_diff(original, modified), expected)

    def test_string_whitespace_diff(self):
        original = "Groundhog Day!"

        modified = "Groundhog         Day!"

        expected = "Groundhog Day!"

        self.assertEqual(html_diff(original, modified), expected)

    def test_html_whitespace_diff(self):
        original = "<p>Groundhog Day!</p>"

        modified = "<p>Groundhog         Day!</p>"

        expected = "<p>Groundhog <ins>        </ins>Day!</p>"

        self.assertEqual(html_diff(original, modified), expected)
