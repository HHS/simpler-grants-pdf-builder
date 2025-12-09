"""
Tests for curly variable syntax in markdown rendering.
"""

import re

from bloom_nofos.markdown_extensions.curly_variables import CURLY_VARIABLE_PATTERN
from composer.models import VariableInfo
from composer.templatetags.replace_variable_keys_with_values import (
    find_variable_by_label,
    replace_variable_keys_with_values,
)
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


class ReplaceVariableKeysWithValuesTests(SimpleTestCase):
    """Test the replace_variable_keys_with_values template tag."""

    def test_no_variables_in_html(self):
        """HTML without variables should remain unchanged."""
        html_string = "<p>This is a simple paragraph.</p>"
        variables_dict = {}
        result = replace_variable_keys_with_values(html_string, variables_dict)
        self.assertEqual(str(result), html_string)

    def test_single_variable_replacement(self):
        """A single variable should be replaced with its value."""
        html_string = '<p>Hello <span class="md-curly-variable">{Name}</span>!</p>'
        variables_dict = {
            "var1": VariableInfo(key="var1", type="string", label="Name", value="Alice")
        }
        result = replace_variable_keys_with_values(html_string, variables_dict)
        self.assertIn("Alice", str(result))
        self.assertNotIn("{Name}", str(result))

    def test_multiple_variable_replacement(self):
        """Multiple variables should be replaced with their values."""
        html_string = '<p><span class="md-curly-variable">{First}</span> and <span class="md-curly-variable">{Second}</span></p>'
        variables_dict = {
            "var1": VariableInfo(
                key="var1", type="string", label="First", value="Alice"
            ),
            "var2": VariableInfo(
                key="var2", type="string", label="Second", value="Bob"
            ),
        }
        result = replace_variable_keys_with_values(html_string, variables_dict)
        self.assertIn("Alice", str(result))
        self.assertIn("Bob", str(result))
        self.assertNotIn("{First}", str(result))
        self.assertNotIn("{Second}", str(result))

    def test_variable_with_spaces_in_label(self):
        """Variables with spaces in labels should be replaced."""
        html_string = '<p><span class="md-curly-variable">{ Project Name }</span></p>'
        variables_dict = {
            "var1": VariableInfo(
                key="var1", type="string", label="Project Name", value="My Project"
            )
        }
        result = replace_variable_keys_with_values(html_string, variables_dict)
        self.assertIn("My Project", str(result))
        self.assertNotIn("{ Project Name }", str(result))

    def test_variable_without_value(self):
        """Variables without a value should not be replaced."""
        html_string = '<p><span class="md-curly-variable">{Name}</span></p>'
        variables_dict = {"var1": VariableInfo(key="var1", type="string", label="Name")}
        result = replace_variable_keys_with_values(html_string, variables_dict)
        self.assertIn("{Name}", str(result))

    def test_variable_with_empty_value(self):
        """Variables with empty string value should not be replaced."""
        html_string = '<p><span class="md-curly-variable">{Name}</span></p>'
        variables_dict = {
            "var1": VariableInfo(key="var1", type="string", label="Name", value="")
        }
        result = replace_variable_keys_with_values(html_string, variables_dict)
        self.assertIn("{Name}", str(result))

    def test_variable_with_none_value(self):
        """Variables with None value should not be replaced."""
        html_string = '<p><span class="md-curly-variable">{Name}</span></p>'
        variables_dict = {
            "var1": VariableInfo(key="var1", type="string", label="Name", value=None)
        }
        result = replace_variable_keys_with_values(html_string, variables_dict)
        self.assertIn("{Name}", str(result))

    def test_variable_not_in_dict(self):
        """Variables not in the dict should remain unchanged."""
        html_string = '<p><span class="md-curly-variable">{Unknown}</span></p>'
        variables_dict = {
            "var1": VariableInfo(key="var1", type="string", label="Name", value="Alice")
        }
        result = replace_variable_keys_with_values(html_string, variables_dict)
        self.assertIn("{Unknown}", str(result))
        self.assertNotIn("Alice", str(result))

    def test_duplicate_variables(self):
        """Duplicate variables should all be replaced."""
        html_string = '<p><span class="md-curly-variable">{Name}</span> and <span class="md-curly-variable">{Name}</span></p>'
        variables_dict = {
            "var1": VariableInfo(key="var1", type="string", label="Name", value="Alice")
        }
        result = replace_variable_keys_with_values(html_string, variables_dict)
        # Both instances should be replaced
        self.assertEqual(str(result).count("Alice"), 2)
        self.assertNotIn("{Name}", str(result))

    def test_complex_html_structure(self):
        """Variables in complex HTML should be replaced."""
        html_string = """
            <div>
                <p>Welcome <span class="md-curly-variable">{User}</span>!</p>
                <ul>
                    <li>Project: <span class="md-curly-variable">{Project}</span></li>
                    <li>Status: <span class="md-curly-variable">{Status}</span></li>
                </ul>
            </div>
        """
        variables_dict = {
            "var1": VariableInfo(
                key="var1", type="string", label="User", value="Alice"
            ),
            "var2": VariableInfo(
                key="var2", type="string", label="Project", value="Demo"
            ),
            "var3": VariableInfo(
                key="var3", type="string", label="Status", value="Active"
            ),
        }
        result = replace_variable_keys_with_values(html_string, variables_dict)
        self.assertIn("Alice", str(result))
        self.assertIn("Demo", str(result))
        self.assertIn("Active", str(result))
        self.assertNotIn("{User}", str(result))
        self.assertNotIn("{Project}", str(result))
        self.assertNotIn("{Status}", str(result))

    def test_non_variable_spans_unchanged(self):
        """Spans without md-curly-variable class should be unchanged."""
        html_string = '<p><span class="other-class">{NotAVariable}</span></p>'
        variables_dict = {
            "var1": VariableInfo(
                key="var1", type="string", label="NotAVariable", value="Value"
            )
        }
        result = replace_variable_keys_with_values(html_string, variables_dict)
        self.assertIn("{NotAVariable}", str(result))
        self.assertNotIn("Value", str(result))

    def test_returns_safe_string(self):
        """The result should be a SafeString (marked safe for templates)."""
        html_string = '<p><span class="md-curly-variable">{Name}</span></p>'
        variables_dict = {
            "var1": VariableInfo(key="var1", type="string", label="Name", value="Alice")
        }
        result = replace_variable_keys_with_values(html_string, variables_dict)
        from django.utils.safestring import SafeString

        self.assertIsInstance(result, SafeString)


class FindVariableByLabelTests(SimpleTestCase):
    """Test the find_variable_by_label helper function."""

    def test_find_existing_variable(self):
        """Should return key and info for existing variable."""
        variables_dict = {
            "var1": VariableInfo(
                key="var1", type="string", label="Name", value="Alice"
            ),
            "var2": VariableInfo(key="var2", type="string", label="Age", value="30"),
        }
        key, info = find_variable_by_label(variables_dict, "Name")
        self.assertEqual(key, "var1")
        self.assertEqual(
            info, VariableInfo(key="var1", type="string", label="Name", value="Alice")
        )

    def test_find_nonexistent_variable(self):
        """Should return None, None for nonexistent variable."""
        variables_dict = {
            "var1": VariableInfo(key="var1", type="string", label="Name", value="Alice")
        }
        key, info = find_variable_by_label(variables_dict, "Unknown")
        self.assertIsNone(key)
        self.assertIsNone(info)

    def test_find_in_empty_dict(self):
        """Should return None, None for empty dict."""
        variables_dict = {}
        key, info = find_variable_by_label(variables_dict, "Name")
        self.assertIsNone(key)
        self.assertIsNone(info)

    def test_find_first_matching_label(self):
        """Should return first match if multiple variables have same label."""
        variables_dict = {
            "var1": VariableInfo(
                key="var1", type="string", label="Name", value="Alice"
            ),
            "var2": VariableInfo(key="var2", type="string", label="Name", value="Bob"),
        }
        key, info = find_variable_by_label(variables_dict, "Name")
        # Should return the first one found (dict iteration order)
        self.assertEqual(key, "var1")
        self.assertEqual(
            info, VariableInfo(key="var1", type="string", label="Name", value="Alice")
        )
