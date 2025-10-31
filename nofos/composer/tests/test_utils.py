from composer.utils import get_edit_mode_label
from django.test import SimpleTestCase


class GetEditModeLabelTests(SimpleTestCase):
    def test_known_values(self):
        self.assertEqual(get_edit_mode_label("full"), "Some text")
        self.assertEqual(get_edit_mode_label("variables"), "Variables")
        self.assertEqual(get_edit_mode_label("yes_no"), "Yes/No")
        self.assertEqual(get_edit_mode_label("locked"), "Locked")

    def test_unknown_value_falls_back_to_capitalize(self):
        self.assertEqual(get_edit_mode_label("draft"), "draft")

    def test_none_or_empty_returns_empty_string(self):
        self.assertEqual(get_edit_mode_label(None), "")
        self.assertEqual(get_edit_mode_label(""), "")
