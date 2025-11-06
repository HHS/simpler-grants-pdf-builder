from unittest import TestCase

from composer.models import (
    ContentGuide,
    ContentGuideSection,
    ContentGuideSubsection,
)


class ExtractVariablesTests(TestCase):
    def setUp(self):
        self.guide = ContentGuide.objects.create(
            title="Guide", opdiv="CDC", group="bloom"
        )
        self.section = ContentGuideSection.objects.create(
            document=self.guide, order=1, name="Section 1", html_id="sec-1"
        )

    def _mk(self, body: str):
        return ContentGuideSubsection.objects.create(
            section=self.section,
            order=1,
            name="Sub 1",
            tag="h3",
            body=body,
            edit_mode="full",
            enabled=True,
        )

    def test_no_variables(self):
        subsection = self._mk("This sentence has no variables.")
        self.assertEqual(subsection.extract_variables(), [])

    def test_simple_variable(self):
        subsection = self._mk("This sentence has one {variable}.")
        variables = subsection.extract_variables()
        self.assertEqual(
            variables,
            [
                {"key": "variable", "type": "string", "label": "variable"},
            ],
        )

    def test_variable_with_spaces(self):
        subsection = self._mk("This has { variable with spaces }.")
        variables = subsection.extract_variables()
        self.assertEqual(
            variables,
            [
                {
                    "key": "variable_with_spaces",
                    "type": "string",
                    "label": "variable with spaces",
                },
            ],
        )

    def test_duplicate_variables(self):
        subsection = self._mk("Enter {Project name} and confirm {Project name}")
        variables = subsection.extract_variables()
        self.assertEqual(
            variables[0],
            {"key": "project_name", "type": "string", "label": "Project name"},
        )
        self.assertEqual(
            variables[1],
            {"key": "project_name_2", "type": "string", "label": "Project name"},
        )

    def test_multiple_variables(self):
        subsection = self._mk("This has {first} and {second} variables.")
        variables = subsection.extract_variables()
        self.assertEqual(
            variables,
            [
                {
                    "key": "first",
                    "type": "string",
                    "label": "first",
                },
                {
                    "key": "second",
                    "type": "string",
                    "label": "second",
                },
            ],
        )

    def test_escaped_braces(self):
        """Escaped braces should not be treated as variables."""
        subsection = self._mk(r"This is not a \{variable\}.")
        variables = subsection.extract_variables()
        self.assertEqual(variables, [])

    def test_escaped_opening_brace(self):
        subsection = self._mk(r"Literal \{not a variable} and real {Variable}")
        variables = subsection.extract_variables()
        self.assertEqual(
            variables,
            [
                {"key": "variable", "type": "string", "label": "Variable"},
            ],
        )

    def test_nested_braces(self):
        """Nested braces should match first complete set of braces: '{outer {inner}'"""
        subsection = self._mk("This {outer {inner} text} has nesting.")
        variables = subsection.extract_variables()
        self.assertEqual(
            variables,
            [{"key": "outer_inner", "label": "outer {inner", "type": "string"}],
        )

    def test_empty_braces(self):
        """Empty braces should not be treated as variables."""
        subsection = self._mk("This has {} empty braces.")
        variables = subsection.extract_variables()
        self.assertEqual(variables, [])

    def test_empty_braces_with_whitespace(self):
        subsection = self._mk("This has {   } empty braces with whitespace.")
        variables = subsection.extract_variables()
        self.assertEqual(variables, [])

    def test_unmatched_braces(self):
        subsection = self._mk("This has { unmatched brace.")
        variables = subsection.extract_variables()
        self.assertEqual(variables, [])

    def test_list_type_variable(self):
        subsection = self._mk(
            "Type: {List: Choose from Grant or Cooperative agreement}."
        )
        variables = subsection.extract_variables()
        self.assertEqual(
            variables,
            [
                {
                    "key": "choose_from_grant_or_cooperative_agreement",
                    "type": "list",
                    "label": "Choose from Grant or Cooperative agreement",
                }
            ],
        )

    def test_variable_in_markdown_context(self):
        subsection = self._mk("**Bold** and {variable} and _italic_.")
        variables = subsection.extract_variables()
        self.assertEqual(
            variables,
            [{"key": "variable", "type": "string", "label": "variable"}],
        )

    def test_text_override_parameter_is_used_instead_of_instance_body(self):
        subsection = self._mk("Old body without vars")
        override = "New body with a {Fresh var}"
        variables = subsection.extract_variables(text=override)
        self.assertEqual(
            variables,
            [
                {"key": "fresh_var", "type": "string", "label": "Fresh var"},
            ],
        )
