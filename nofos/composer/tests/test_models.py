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

    def test_no_variables_returns_empty_list(self):
        ss = self._mk("No placeholders here.")
        self.assertEqual(ss.extract_variables(), [])

    def test_simple_string_variable(self):
        ss = self._mk("Please provide {Project name} for the application.")
        vars_ = ss.extract_variables()
        self.assertEqual(
            vars_,
            [
                {"key": "project_name", "type": "string", "label": "Project name"},
            ],
        )

    def test_list_variable_type(self):
        ss = self._mk("Add tags: {List: Tags}")
        vars_ = ss.extract_variables()
        self.assertEqual(
            vars_,
            [
                {"key": "tags", "type": "list", "label": "Tags"},
            ],
        )

    def test_duplicate_labels_are_deduped(self):
        ss = self._mk("Enter {Project name} and confirm {Project name}")
        vars_ = ss.extract_variables()
        self.assertEqual(
            vars_[0], {"key": "project_name", "type": "string", "label": "Project name"}
        )
        self.assertEqual(
            vars_[1],
            {"key": "project_name_2", "type": "string", "label": "Project name"},
        )

    def test_escaped_opening_brace_does_not_create_variable(self):
        ss = self._mk(r"Literal \{not a variable} and real {Variable}")
        vars_ = ss.extract_variables()
        self.assertEqual(
            vars_,
            [
                {"key": "variable", "type": "string", "label": "Variable"},
            ],
        )

    def test_empty_or_whitespace_label_falls_back_to_key_var(self):
        ss = self._mk("Weird case: {   }")
        vars_ = ss.extract_variables()
        self.assertEqual(
            vars_,
            [
                {
                    "key": "var",
                    "type": "string",
                    "label": "",
                },  # label trimmed to empty → key fallback
            ],
        )

    def test_text_override_parameter_is_used_instead_of_instance_body(self):
        ss = self._mk("Old body without vars")
        override = "New body with a {Fresh var}"
        vars_ = ss.extract_variables(text=override)
        self.assertEqual(
            vars_,
            [
                {"key": "fresh_var", "type": "string", "label": "Fresh var"},
            ],
        )
