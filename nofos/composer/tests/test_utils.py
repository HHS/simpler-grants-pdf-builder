from composer.utils import (
    get_conditional_questions_label,
    get_edit_mode_label,
    render_curly_variable_list_html_string,
)
from django.test import SimpleTestCase


class GetEditModeLabelTests(SimpleTestCase):
    def test_known_values(self):
        self.assertEqual(get_edit_mode_label("variables"), "Certain text")
        self.assertEqual(get_edit_mode_label("yes_no"), "Yes/No")
        self.assertEqual(get_edit_mode_label("locked"), "Locked")

    def test_unknown_value_returns_empty_string(self):
        self.assertEqual(get_edit_mode_label("draft"), "")

    def test_none_or_empty_returns_empty_string(self):
        self.assertEqual(get_edit_mode_label(None), "")
        self.assertEqual(get_edit_mode_label(""), "")


class MockSubsection:
    """Lightweight stand-in for ContentGuideSubsection for testing."""

    def __init__(self, is_conditional, conditional_answer: None):
        self.is_conditional = is_conditional
        self.conditional_answer = conditional_answer


class GetConditionalQuestionsLabelTests(SimpleTestCase):
    def test_conditional_yes_returns_yes_label(self):
        subsection = MockSubsection(is_conditional=True, conditional_answer=True)
        self.assertEqual(
            get_conditional_questions_label(subsection),
            "Conditional: Yes",
        )

    def test_conditional_no_returns_no_label(self):
        subsection = MockSubsection(is_conditional=True, conditional_answer=False)
        self.assertEqual(
            get_conditional_questions_label(subsection),
            "Conditional: No",
        )

    def test_non_conditional_returns_empty_string(self):
        subsection = MockSubsection(is_conditional=False, conditional_answer=None)
        self.assertEqual(
            get_conditional_questions_label(subsection),
            "",
        )

    def test_none_subsection_returns_empty_string(self):
        self.assertEqual(
            get_conditional_questions_label(None),
            "",
        )


class RenderCurlyVariableListHtmlStringTests(SimpleTestCase):
    def test_empty_list_returns_empty_string(self):
        self.assertEqual(render_curly_variable_list_html_string([]), "")

    def test_single_variable(self):
        data = [{"label": "one"}]
        expected = ': <span class="curly-var font-mono-xs">{one}</span>'
        self.assertEqual(render_curly_variable_list_html_string(data), expected)

    def test_multiple_variables_comma_separated(self):
        data = [{"label": "one"}, {"label": "two"}, {"label": "three"}]
        expected = (
            ': <span class="curly-var font-mono-xs">{one}</span>, '
            '<span class="curly-var font-mono-xs">{two}</span>, '
            '<span class="curly-var font-mono-xs">{three}</span>'
        )
        self.assertEqual(render_curly_variable_list_html_string(data), expected)

    def test_labels_are_trimmed(self):
        data = [{"label": "  first  "}, {"label": "\tsecond\t"}]
        expected = (
            ': <span class="curly-var font-mono-xs">{first}</span>, '
            '<span class="curly-var font-mono-xs">{second}</span>'
        )
        self.assertEqual(render_curly_variable_list_html_string(data), expected)

    def test_preserves_input_order(self):
        data = [{"label": "z"}, {"label": "a"}, {"label": "m"}]
        expected = (
            ': <span class="curly-var font-mono-xs">{z}</span>, '
            '<span class="curly-var font-mono-xs">{a}</span>, '
            '<span class="curly-var font-mono-xs">{m}</span>'
        )
        self.assertEqual(render_curly_variable_list_html_string(data), expected)
