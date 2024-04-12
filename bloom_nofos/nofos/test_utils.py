from django.test import TestCase

from .utils import clean_string, create_subsection_html_id, get_icon_path_choices


class TestGetIconPathChoices(TestCase):
    def test_get_icon_path_choices_acf_white(self):
        """Test that all icon choices are returned for the 'portrait-acf-white' theme."""
        expected_choices = [
            (
                "nofo--icons--border",
                "(Filled) Color background, white icon, white outline",
            ),
            (
                "nofo--icons--solid",
                "(Standard) White background, color icon, color outline",
            ),
            ("nofo--icons--thin", "(Thin) White background, color icon, color outline"),
        ]
        result = get_icon_path_choices("portrait-acf-white")
        self.assertEqual(result, expected_choices)

    def test_get_icon_path_choices_other_theme(self):
        """Test that only 'border' and 'solid' icon choices are returned for other themes."""
        expected_choices = [
            (
                "nofo--icons--border",
                "(Filled) Color background, white icon, white outline",
            ),
            (
                "nofo--icons--solid",
                "(Standard) White background, color icon, color outline",
            ),
        ]
        result = get_icon_path_choices("portrait-hrsa-white")
        self.assertEqual(result, expected_choices)


class TestCreateSubsectionHtmlId(TestCase):
    def test_create_subsection_html_id_simple(self):
        """Test that the HTML ID is correctly created with simple inputs."""

        class MockSubsection:
            def __init__(self, section_name, name):
                self.name = name

                class MockSection:
                    def __init__(self, name):
                        self.name = name

                self.section = MockSection(section_name)

        subsection = MockSubsection("Introduction", "Overview")
        result = create_subsection_html_id(1, subsection)
        expected_id = "1--introduction--overview"
        self.assertEqual(result, expected_id)

    def test_create_subsection_html_id_complex(self):
        """Test that the HTML ID is correctly created with complex inputs including special characters and spaces."""

        class MockSubsection:
            def __init__(self, section_name, name):
                self.name = name

                class MockSection:
                    def __init__(self, name):
                        self.name = name

                self.section = MockSection(section_name)

        subsection = MockSubsection("Main Section: The Start", "Subsection 1/2")
        result = create_subsection_html_id(10, subsection)
        expected_id = "10--main-section-the-start--subsection-1-2"
        self.assertEqual(result, expected_id)

    def test_create_subsection_html_id_empty_names(self):
        """Test that the HTML ID handles empty names correctly."""

        class MockSubsection:
            def __init__(self, section_name, name):
                self.name = name

                class MockSection:
                    def __init__(self, name):
                        self.name = name

                self.section = MockSection(section_name)

        subsection = MockSubsection("", "")
        result = create_subsection_html_id(5, subsection)
        expected_id = "5----"
        self.assertEqual(result, expected_id)


class TestCleanString(TestCase):
    def test_clean_string_simple(self):
        """Test that the function removes extra spaces and trims the string."""
        result = clean_string("  Hello   World!  ")
        self.assertEqual(result, "Hello World!")

    def test_clean_string_newlines_tabs(self):
        """Test that newlines and tabs are replaced with a single space."""
        result = clean_string("\nHello\tWorld!\t \n")
        self.assertEqual(result, "Hello World!")

    def test_clean_string_no_extra_spaces(self):
        """Test strings that do not have extra spaces to begin with."""
        result = clean_string("Hello World!")
        self.assertEqual(result, "Hello World!")

    def test_clean_string_empty_string(self):
        """Test that an empty string is handled correctly."""
        result = clean_string("   ")
        self.assertEqual(result, "")

    def test_clean_string_complex_whitespace(self):
        """Test a string with complex whitespace scenarios."""
        result = clean_string("  Hello   there \t new world   \n")
        self.assertEqual(result, "Hello there new world")
