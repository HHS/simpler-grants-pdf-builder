from composer.utils import (
    get_conditional_questions_label,
    get_edit_mode_label,
    render_curly_variable_list_html_string,
)
from django.test import SimpleTestCase


class GetEditModeLabelTests(SimpleTestCase):
    def test_known_values(self):
        self.assertEqual(get_edit_mode_label("variables"), "Certain text")
        self.assertEqual(get_edit_mode_label("locked"), "Locked")

    def test_unknown_value_returns_empty_string(self):
        self.assertEqual(get_edit_mode_label("draft"), "")

    def test_none_or_empty_returns_empty_string(self):
        self.assertEqual(get_edit_mode_label(None), "")
        self.assertEqual(get_edit_mode_label(""), "")


class GetConditionalQuestionsLabelTests(SimpleTestCase):
    def test_true_returns_yes_label(self):
        self.assertEqual(
            get_conditional_questions_label(True),
            "Conditional: Yes",
        )

    def test_false_returns_no_label(self):
        self.assertEqual(
            get_conditional_questions_label(False),
            "Conditional: No",
        )

    def test_none_returns_empty_string(self):
        self.assertEqual(
            get_conditional_questions_label(None),
            "",
        )

    def test_non_bool_values_return_empty_string(self):
        # Anything that is not literal True/False should give empty string
        for value in ("yes", "no", "", 0, 1, [], {}, object()):
            with self.subTest(value=value):
                self.assertEqual(get_conditional_questions_label(value), "")


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
