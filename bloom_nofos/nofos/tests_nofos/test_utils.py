import json
from datetime import timedelta

from constance.test import override_config
from django.test import TestCase
from django.utils.timezone import now
from easyaudit.models import CRUDEvent
from nofos.models import Nofo
from nofos.utils import (
    StyleMapManager,
    add_html_id_to_subsection,
    clean_string,
    create_nofo_audit_event,
    create_subsection_html_id,
    get_icon_path_choices,
    match_view_url,
)
from users.models import BloomUser as User

from ..models import Nofo, Section, Subsection


class CreateNofoAuditEventTests(TestCase):

    def setUp(self):
        # Set up a user and a NOFO object to pass into the function
        self.user = User.objects.create(email="takumi@speed-stars.com")
        self.nofo = Nofo.objects.create(title="Akina Pass NOFO", opdiv="Test OpDiv")

    def test_audit_event_exists(self):
        create_nofo_audit_event("nofo_print", self.nofo, self.user)

        event = CRUDEvent.objects.last()
        self.assertEqual(event.event_type, CRUDEvent.UPDATE)
        self.assertEqual(event.object_id, str(self.nofo.id))
        self.assertEqual(event.user, self.user)

    def test_valid_event_type_nofo_print_test(self):
        # Set DOCRAPTOR_LIVE_MODE to a past timestamp to simulate "test" mode
        with override_config(
            DOCRAPTOR_LIVE_MODE=now() - timedelta(minutes=5, seconds=1)
        ):
            create_nofo_audit_event("nofo_print", self.nofo, self.user)

        event = CRUDEvent.objects.last()
        # Check changed_fields JSON structure for "nofo_print" with "test" mode
        changed_fields = json.loads(event.changed_fields)
        self.assertEqual(changed_fields["action"], "nofo_print")
        self.assertEqual(changed_fields["print_mode"], ["test"])
        self.assertTrue("updated" in changed_fields)

    def test_valid_event_type_nofo_print_live(self):
        # Set DOCRAPTOR_LIVE_MODE to current timestamp to simulate "live" mode
        with override_config(DOCRAPTOR_LIVE_MODE=now()):
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


class TestAddHtmlIdToSubsection(TestCase):
    def setUp(self):
        self.nofo = Nofo.objects.create(
            title="Test NOFO",
            number="1234",
            opdiv="Test OpDiv",
        )
        # Mock section for use in tests
        self.section = Section(name="Sample Section", order=1, nofo=self.nofo)
        self.section.save()

    def test_add_html_id_to_subsection_with_empty_html_id(self):
        """Test that a subsection without an HTML ID gets assigned one."""
        subsection = Subsection(
            name="Sample Subsection", order=1, section=self.section, html_id=""
        )
        add_html_id_to_subsection(subsection)
        self.assertEqual(subsection.html_id, "1--sample-section--sample-subsection")

    def test_add_html_id_to_subsection_with_existing_html_id(self):
        """Test that a subsection with an existing HTML ID does not get overwritten."""
        subsection = Subsection(
            name="Sample Subsection",
            order=1,
            section=self.section,
            html_id="existing-html-id",
        )
        add_html_id_to_subsection(subsection)
        # Ensure the HTML ID remains the same
        self.assertEqual(subsection.html_id, "existing-html-id")

    def test_add_html_id_to_subsection_with_empty_name(self):
        """Test that a subsection without a name does not get an HTML ID."""
        subsection = Subsection(name="", order=1, section=self.section, html_id="")
        add_html_id_to_subsection(subsection)
        # Ensure no HTML ID is generated
        self.assertEqual(subsection.html_id, "")

    def test_add_html_id_to_subsection_with_none_html_id(self):
        """Test that a subsection with a None HTML ID gets assigned one."""
        subsection = Subsection(
            name="Another Subsection", order=2, section=self.section, html_id=None
        )
        add_html_id_to_subsection(subsection)
        self.assertEqual(subsection.html_id, "2--sample-section--another-subsection")

    def test_add_html_id_to_subsection_with_pk(self):
        """Test that a subsection with a primary key uses it to generate the HTML ID."""
        subsection = Subsection(
            name="PK-based Subsection",
            tag="h3",
            order=2,
            section=self.section,
            html_id=None,
        )
        subsection.save()  # Assign a primary key
        add_html_id_to_subsection(subsection)
        self.assertEqual(subsection.html_id, "2--sample-section--pk-based-subsection")


class CleanStringTests(TestCase):
    def test_trim_leading_and_trailing_spaces(self):
        self.assertEqual(clean_string("  test string  "), "test string")

    def test_replace_newlines(self):
        self.assertEqual(clean_string("test\nstring"), "test string")

    def test_replace_carriage_returns(self):
        self.assertEqual(clean_string("test\rstring"), "test string")

    def test_replace_tabs(self):
        self.assertEqual(clean_string("test\tstring"), "test string")

    def test_replace_multiple_spaces(self):
        self.assertEqual(clean_string("test  string"), "test string")

    def test_replace_mixed_whitespace(self):
        self.assertEqual(clean_string("test \t\n\r string"), "test string")

    def test_replace_leading_weird_space(self):
        self.assertEqual(clean_string(" test \t\n\r string"), "test string")

    def test_replace_trailing_weird_space(self):
        self.assertEqual(clean_string("test \t\n\r string "), "test string")

    def test_no_whitespace_change(self):
        self.assertEqual(clean_string("test string"), "test string")

    def test_empty_string(self):
        self.assertEqual(clean_string(""), "")

    def test_only_whitespace(self):
        self.assertEqual(clean_string(" \t\r\n "), "")

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
        # No note
        style_map_manager.add_style(
            style_rule="p[style-name='Table'] => p",
            location_in_nofo="Step 3 > Other required forms > All table cells",
        )
        # No location_in_nofo
        style_map_manager.add_style(
            style_rule="p:unordered-list(1) => ul > li:fresh",
            note="Bullet list 1",
        )
        # No note or location_in_nofo
        style_map_manager.add_style(
            style_rule="p:unordered-list(2) => ul|ol > li > ul > li:fresh",
        )

        self.assertEqual(len(style_map_manager.styles), 4)
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
        self.assertIn(
            {
                "style_rule": "p:unordered-list(1) => ul > li:fresh",
                "note": "Bullet list 1",
                "location_in_nofo": None,
            },
            style_map_manager.styles,
        )
        self.assertIn(
            {
                "style_rule": "p:unordered-list(2) => ul|ol > li > ul > li:fresh",
                "note": None,
                "location_in_nofo": None,
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


class MatchUrlTests(TestCase):
    def test_match_valid_uuid_urls(self):
        """
        Test the match_view_url function with valid UUID URLs.
        """
        self.assertTrue(match_view_url("/nofos/8713ea6d-335a-409f-90c0-f75162aecf0e"))
        self.assertTrue(match_view_url("/nofos/123e4567-e89b-12d3-a456-426614174000"))
        self.assertTrue(match_view_url("/nofos/abcdef12-1234-5678-1234-abcdefabcdef"))

    def test_match_invalid_urls(self):
        """
        Test the match_view_url function with invalid URLs.
        """
        # Invalid UUIDs
        self.assertFalse(match_view_url("/nofos/123"))
        self.assertFalse(match_view_url("/nofos/1"))
        self.assertFalse(match_view_url("/nofos/0"))
        self.assertFalse(match_view_url("/nofos/12345"))
        self.assertFalse(match_view_url("/nofos/not-a-uuid"))
        self.assertFalse(match_view_url("/nofos/1234-5678"))

        # Invalid paths
        self.assertFalse(match_view_url("/nofos"))
        self.assertFalse(match_view_url("/nofos/"))
        self.assertFalse(match_view_url("/nofos/abc"))
        self.assertFalse(match_view_url("/nofos/123/456"))
        self.assertFalse(match_view_url("/nofos/1/2"))
