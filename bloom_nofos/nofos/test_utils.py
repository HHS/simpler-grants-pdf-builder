import json

from constance.test import override_config
from django.test import TestCase
from easyaudit.models import CRUDEvent
from users.models import BloomUser as User

from .models import Nofo
from .utils import (
    StyleMapManager,
    clean_string,
    create_nofo_audit_event,
    create_subsection_html_id,
    get_icon_path_choices,
)


class CreateNofoAuditEventTests(TestCase):

    def setUp(self):
        # Set up a user and a NOFO object to pass into the function
        self.user = User.objects.create(email="takumi@speed-stars.com")
        self.nofo = Nofo.objects.create(title="Akina Pass NOFO")

    def test_audit_event_exists(self):
        create_nofo_audit_event("nofo_print", self.nofo, self.user)

        event = CRUDEvent.objects.last()
        self.assertEqual(event.event_type, CRUDEvent.UPDATE)
        self.assertEqual(event.object_id, str(self.nofo.id))
        self.assertEqual(event.user, self.user)

    def test_valid_event_type_nofo_print_test(self):
        with override_config(DOCRAPTOR_TEST_MODE=True):
            create_nofo_audit_event("nofo_print", self.nofo, self.user)

        event = CRUDEvent.objects.last()
        # Check changed_fields JSON structure for "nofo_print" with "test" mode
        changed_fields = json.loads(event.changed_fields)
        self.assertEqual(changed_fields["action"], "nofo_print")
        self.assertEqual(changed_fields["print_mode"], ["test"])
        self.assertTrue("updated" in changed_fields)

    def test_valid_event_type_nofo_print_live(self):
        with override_config(DOCRAPTOR_TEST_MODE=False):
            create_nofo_audit_event("nofo_print", self.nofo, self.user)

        event = CRUDEvent.objects.last()
        # Check changed_fields JSON structure for "nofo_print" with "live" mode
        changed_fields = json.loads(event.changed_fields)
        self.assertEqual(changed_fields["action"], "nofo_print")
        self.assertEqual(changed_fields["print_mode"], ["live"])
        self.assertTrue("updated" in changed_fields)

    def test_valid_event_type_nofo_import(self):
        create_nofo_audit_event("nofo_import", self.nofo, self.user)

        event = CRUDEvent.objects.last()
        changed_fields = json.loads(event.changed_fields)
        self.assertEqual(changed_fields["action"], "nofo_import")
        self.assertNotIn("print_mode", changed_fields)
        self.assertTrue("updated" in changed_fields)

    def test_valid_event_type_nofo_reimport(self):
        create_nofo_audit_event("nofo_reimport", self.nofo, self.user)

        event = CRUDEvent.objects.last()
        changed_fields = json.loads(event.changed_fields)
        self.assertEqual(changed_fields["action"], "nofo_reimport")
        self.assertNotIn("print_mode", changed_fields)
        self.assertTrue("updated" in changed_fields)

    def test_invalid_event_type_raises_error(self):
        # Test with an invalid event_type
        with self.assertRaises(ValueError) as context:
            create_nofo_audit_event("nofo_deleted", self.nofo, self.user)

        self.assertEqual(
            str(context.exception),
            "Invalid event_type 'nofo_deleted'. Allowed values are: nofo_import, nofo_print, nofo_reimport",
        )


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


class StyleMapManagerTests(TestCase):
    def test_add_style(self):
        """Test adding styles to the manager."""
        style_map_manager = StyleMapManager()
        style_map_manager.add_style(
            style_rule="p[style-name='Emphasis A'] => strong",
            location_in_nofo="Step 2 > Grants.gov > Need Help?",
            note="Just bold the entire sentence",
        )
        style_map_manager.add_style(
            style_rule="p[style-name='Table'] => p",
            location_in_nofo="Step 3 > Other required forms > All table cells",
        )

        self.assertEqual(len(style_map_manager.styles), 2)
        self.assertIn(
            {
                "style_rule": "p[style-name='Emphasis A'] => strong",
                "location_in_nofo": "Step 2 > Grants.gov > Need Help?",
                "note": "Just bold the entire sentence",
            },
            style_map_manager.styles,
        )
        self.assertIn(
            {
                "style_rule": "p[style-name='Table'] => p",
                "location_in_nofo": "Step 3 > Other required forms > All table cells",
                "note": None,
            },
            style_map_manager.styles,
        )

    def test_get_style_map(self):
        """Test the output of get_style_map method."""
        style_map_manager = StyleMapManager()
        style_map_manager.add_style(
            style_rule="p[style-name='Emphasis A'] => strong",
            location_in_nofo="Step 2 > Grants.gov > Need Help?",
            note="Just bold the entire sentence",
        )
        style_map_manager.add_style(
            style_rule="p[style-name='Table'] => p",
            location_in_nofo="Step 3 > Other required forms > All table cells",
        )
        expected_style_map = (
            "p[style-name='Emphasis A'] => strong\np[style-name='Table'] => p"
        )
        self.assertEqual(style_map_manager.get_style_map(), expected_style_map)

    def test_get_style_map_empty(self):
        """Test the output of get_style_map method when no styles have been added."""
        manager = StyleMapManager()
        self.assertEqual(manager.get_style_map(), "")
