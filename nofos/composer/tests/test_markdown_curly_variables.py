"""
Tests for curly variable syntax in markdown rendering.
"""

import re

from bloom_nofos.markdown_extensions.curly_variables import CURLY_VARIABLE_PATTERN
from django.test import SimpleTestCase
from martor.utils import markdownify


class CurlyVariableMarkdownTests(SimpleTestCase):
    """Test that curly variables are properly rendered in markdown."""

    def test_no_variables(self):
        """No variables in text."""
        text = "This sentence has no variables."
        html = markdownify(text)
        self.assertEqual("<p>This sentence has no variables.</p>", html)

    def test_simple_variable(self):
        """Single variable in text."""
        text = "This sentence has one {variable}."
        html = markdownify(text)
        self.assertEqual(
            '<p>This sentence has one <span class="md-curly-variable">{variable}</span>.</p>',
            html,
        )

    def test_variable_with_spaces(self):
        """Variable with spaces inside braces."""
        text = "This has { variable with spaces }."
        html = markdownify(text)
        self.assertEqual(
            '<p>This has <span class="md-curly-variable">{ variable with spaces }</span>.</p>',
            html,
        )

    def test_duplicate_variables(self):
        """Variable with spaces inside braces."""
        text = "Enter {Project name} and confirm {Project name}."
        html = markdownify(text)
        self.assertEqual(
            '<p>Enter <span class="md-curly-variable">{Project name}</span> and confirm <span class="md-curly-variable">{Project name}</span>.</p>',
            html,
        )

    def test_multiple_variables(self):
        """Multiple variables in one sentence."""
        text = "This has {first} and {second} variables."
        html = markdownify(text)
        self.assertEqual(
            '<p>This has <span class="md-curly-variable">{first}</span> and <span class="md-curly-variable">{second}</span> variables.</p>',
            html,
        )

    def test_escaped_braces(self):
        """Escaped braces should not be treated as variables."""
        text = r"This is not a \{variable\}."
        html = markdownify(text)
        self.assertEqual("<p>This is not a {variable}.</p>", html)

    def test_escaped_opening_brace(self):
        """Escaped braces should not be treated as variables."""
        text = r"This is not a \{variable1} but this is a {variable2}."
        html = markdownify(text)
        self.assertEqual(
            '<p>This is not a {variable1} but this is a <span class="md-curly-variable">{variable2}</span>.</p>',
            html,
        )

    def test_nested_braces(self):
        """Nested braces should only match inner braces."""
        text = "This {outer {inner} text} has nesting."
        html = markdownify(text)
        self.assertEqual(
            '<p>This <span class="md-curly-variable">{outer {inner}</span> text} has nesting.</p>',
            html,
        )

    def test_empty_braces(self):
        """Empty braces should not be treated as variables."""
        text = "This has {} empty braces."
        html = markdownify(text)
        self.assertNotIn('<span class="md-curly-variable"></span>', html)
        self.assertEqual("<p>This has {} empty braces.</p>", html)

    def test_empty_braces_with_whitespace(self):
        """Empty braces should not be treated as variables."""
        text = "This has {   } empty braces with whitespace."
        html = markdownify(text)
        self.assertNotIn('<span class="md-curly-variable"></span>', html)
        self.assertEqual("<p>This has {   } empty braces with whitespace.</p>", html)

    def test_unmatched_braces(self):
        """Unmatched braces should not be treated as variables."""
        text = "This has { unmatched brace."
        html = markdownify(text)
        self.assertEqual("<p>This has { unmatched brace.</p>", html)

    def test_list_type_variable(self):
        """List-type variables with colon syntax."""
        text = "Choose from {List: available options}."
        html = markdownify(text)
        self.assertEqual(
            '<p>Choose from <span class="md-curly-variable">{List: available options}</span>.</p>',
            html,
        )

    def test_variable_in_markdown_context(self):
        """Variables should work with other markdown syntax."""
        text = "**Bold** and {variable} and _italic_."
        html = markdownify(text)
        self.assertEqual(
            '<p><strong>Bold</strong> and <span class="md-curly-variable">{variable}</span> and <em>italic</em>.</p>',
            html,
        )

    def test_attr_list_block_not_wrapped_colon(self):
        """Attribute list starting with '{:' is not treated as a variable."""
        text = "This is a paragraph.\n{: #an_id .a_class }"
        html = markdownify(text)
        self.assertEqual(
            '<p class="a_class" id="an_id">This is a paragraph.<br></p>', html
        )

    def test_attr_list_block_not_wrapped_class(self):
        """Attribute list starting with '{.' is not treated as a variable."""
        text = "This is a paragraph.\n{.lead}"
        html = markdownify(text)
        self.assertEqual('<p class="lead">This is a paragraph.<br></p>', html)

    def test_attr_list_block_not_wrapped_id(self):
        """Attribute list starting with '{#' is not treated as a variable."""
        text = "This is a paragraph.\n{#section-id}"
        html = markdownify(text)
        self.assertEqual('<p id="section-id">This is a paragraph.<br></p>', html)


class CurlyVariablePatternTests(SimpleTestCase):
    """Test that the regex pattern correctly matches curly variables."""

    def setUp(self):
        """Compile the pattern once for all tests."""
        self.pattern = re.compile(CURLY_VARIABLE_PATTERN)

    def _find_curly_variables(self, text):
        """Helper to extract variable content from text."""
        return [m.group(1) for m in self.pattern.finditer(text)]

    def test_extraction_simple(self):
        """Extract simple variables."""
        text = "This has {var1} and {var2}."
        vars = self._find_curly_variables(text)
        self.assertEqual(vars, ["var1", "var2"])

    def test_extraction_with_spaces(self):
        """Extract variables with spaces."""
        text = "This has { variable with spaces }."
        vars = self._find_curly_variables(text)
        self.assertEqual(vars, [" variable with spaces "])

    def test_extraction_list_type(self):
        """Extract list-type variables."""
        text = "Choose {List: options here}."
        vars = self._find_curly_variables(text)
        self.assertEqual(vars, ["List: options here"])

    def test_extraction_ignores_escaped(self):
        """Escaped variables should not be extracted."""
        text = r"This \{is not\} a variable but {this is}."
        vars = self._find_curly_variables(text)
        self.assertEqual(vars, ["this is"])

    def test_extraction_ignores_nested(self):
        """First set of nested braces should match: '{outer { inner}'."""
        text = "This {outer {inner} text} end."
        vars = self._find_curly_variables(text)
        self.assertEqual(vars, ["outer {inner"])

    def test_extraction_empty_braces(self):
        """Empty braces should not match."""
        text = "This has {} empty."
        vars = self._find_curly_variables(text)
        self.assertEqual(vars, [])

    def test_extraction_no_matches(self):
        """Text without variables returns empty list."""
        text = "This has no variables at all."
        vars = self._find_curly_variables(text)
        self.assertEqual(vars, [])

    def test_extraction_ignores_attr_list_colon(self):
        """Attribute lists starting with '{:' should be ignored."""
        text = "This is a paragraph.\n{: #an_id .a_class }"
        vars = self._find_curly_variables(text)
        self.assertEqual(vars, [])

    def test_extraction_ignores_attr_list_class(self):
        """Attribute lists starting with '{.' should be ignored."""
        text = "This {.lead} should not be a variable."
        vars = self._find_curly_variables(text)
        self.assertEqual(vars, [])

    def test_extraction_ignores_attr_list_id(self):
        """Attribute lists starting with '{#' should be ignored."""
        text = "This {#section-id} should not be a variable."
        vars = self._find_curly_variables(text)
        self.assertEqual(vars, [])
