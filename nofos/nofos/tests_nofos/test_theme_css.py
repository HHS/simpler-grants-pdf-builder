import re

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase


class SharedThemeHeadingSpacingTests(SimpleTestCase):
    def test_h3_has_extra_space_before_following_content(self):
        css_path = finders.find("theme-base.css")
        self.assertIsNotNone(
            css_path, "theme-base.css not found by staticfiles finders"
        )

        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        rule_match = re.search(r"^h3\s*\{([^}]*)\}", css, re.MULTILINE)
        self.assertIsNotNone(rule_match, "No h3 rule found")
        self.assertIn("margin-bottom: 10px", rule_match.group(1))
