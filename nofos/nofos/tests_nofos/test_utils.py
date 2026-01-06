import json
from datetime import timedelta

from constance.test import override_config
from django.test import TestCase
from django.utils.timezone import now
from easyaudit.models import CRUDEvent
from users.models import BloomUser as User

from nofos.models import Nofo
from nofos.utils import (
    StyleMapManager,
    add_html_id_to_subsection,
    clean_string,
    create_nofo_audit_event,
    create_subsection_html_id,
    extract_highlighted_context,
    get_icon_path_choices,
    match_view_url,
    replace_text_exclude_markdown_links,
    replace_text_include_markdown_links,
    strip_markdown_links,
)

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
        create_nofo_audit_event("nofo_print", self.nofo, self.user, is_test_pdf=True)

        event = CRUDEvent.objects.last()
        # Check changed_fields JSON structure for "nofo_print" with "test" mode
        changed_fields = json.loads(event.changed_fields)
        self.assertEqual(changed_fields["action"], "nofo_print")
        self.assertEqual(changed_fields["print_mode"], ["test"])
        self.assertTrue("updated" in changed_fields)

    def test_valid_event_type_nofo_print_live(self):
        create_nofo_audit_event("nofo_print", self.nofo, self.user, is_test_pdf=False)

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
                "(Outlined) White background, color icon, color outline",
            ),
            ("nofo--icons--thin", "(Thin) White background, color icon, color outline"),
        ]
        result = get_icon_path_choices("portrait-acf-white")
        self.assertEqual(result, expected_choices)

    def test_get_icon_path_choices_ihs_white(self):
        """Test that 'solid' + 'thin' icon choices are returned for the 'portrait-ihs-white' theme."""
        expected_choices = [
            (
                "nofo--icons--solid",
                "(Outlined) White background, color icon, color outline",
            ),
            (
                "nofo--icons--thin",
                "(Thin) White background, color icon, color outline",
            ),
        ]
        result = get_icon_path_choices("portrait-ihs-white")
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
                "(Outlined) White background, color icon, color outline",
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


class ExtractHighlightedContextTests(TestCase):
    def test_no_matches_returns_empty_list(self):
        body = "This is some text with no target."
        result = extract_highlighted_context(body, "missing")
        self.assertEqual(result, [])

    def test_single_match_highlights_correctly(self):
        body = "Welcome to the jungle."
        result = extract_highlighted_context(body, "jungle")
        self.assertEqual(len(result), 1)
        self.assertIn('<mark class="bg-yellow">jungle</mark>', result[0])

    def test_multiple_distant_matches_produce_multiple_snippets(self):
        body = "First match here. " + ("x" * 300) + "Second match way later."
        result = extract_highlighted_context(
            body, "match", context_chars=20, group_distance=50
        )
        self.assertEqual(len(result), 2)
        self.assertIn("…", result[0])  # Ellipsis should appear on truncated text
        self.assertIn('<mark class="bg-yellow">match</mark>', result[1])

    def test_multiple_close_matches_are_grouped(self):
        body = "match one, and then match two just a bit later."
        result = extract_highlighted_context(
            body, "match", context_chars=10, group_distance=50
        )
        self.assertEqual(len(result), 1)
        self.assertIn('<mark class="bg-yellow">match</mark>', result[0])
        self.assertGreater(result[0].count("mark class"), 1)  # Multiple highlights

    def test_ellipses_added_for_trimmed_context(self):
        body = "a" * 150 + "match" + "b" * 150
        result = extract_highlighted_context(body, "match", context_chars=50)
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].startswith("…"))
        self.assertTrue(result[0].endswith("…"))

    def test_case_insensitive_match(self):
        body = "Match me if you can."
        result = extract_highlighted_context(body, "match")
        self.assertIn("Match", result[0])
        self.assertIn('<mark class="bg-yellow">Match</mark>', result[0])


class ReplaceIncludeMarkdownLinksTests(TestCase):
    def test_simple_replacement(self):
        text = "The application deadline is June 1, 2025."
        result = replace_text_include_markdown_links(
            text, "June 1, 2025", "August 1, 2025"
        )
        self.assertEqual(result, "The application deadline is August 1, 2025.")

    def test_replacement_inside_markdown_link_text(self):
        text = "Visit [the deadline](https://grants.gov/deadline) for info."
        result = replace_text_include_markdown_links(text, "deadline", "date")
        self.assertEqual(result, "Visit [the date](https://grants.gov/date) for info.")

    def test_replacement_inside_url(self):
        text = "Check out [this link](https://example.com/deadline-info)"
        result = replace_text_include_markdown_links(text, "deadline", "date")
        self.assertEqual(result, "Check out [this link](https://example.com/date-info)")

    def test_case_insensitive_replacement(self):
        text = "Apply before the DEADLINE. Visit [Deadline Info](https://example.com/DEADLINE)."
        result = replace_text_include_markdown_links(text, "deadline", "date")
        expected = "Apply before the date. Visit [date Info](https://example.com/date)."
        self.assertEqual(result, expected)

    def test_multiple_occurrences(self):
        text = (
            "Apply by the deadline. See [the deadline](https://example.com/deadline) "
            "and [deadline info](#section-deadline)."
        )
        result = replace_text_include_markdown_links(text, "deadline", "date")
        expected = (
            "Apply by the date. See [the date](https://example.com/date) "
            "and [date info](#section-date)."
        )
        self.assertEqual(result, expected)

    def test_no_links(self):
        text = "The deadline is approaching."
        result = replace_text_include_markdown_links(text, "deadline", "date")
        self.assertEqual(result, "The date is approaching.")

    def test_empty_input(self):
        self.assertEqual(replace_text_include_markdown_links("", "foo", "bar"), "")
        self.assertIsNone(replace_text_include_markdown_links(None, "foo", "bar"))

    def test_special_characters_in_link(self):
        text = "Click [this (weird) deadline](https://example.com/deadline-stuff)"
        result = replace_text_include_markdown_links(text, "deadline", "date")
        self.assertEqual(
            result, "Click [this (weird) date](https://example.com/date-stuff)"
        )


class ReplaceExcludeMarkdownLinksTests(TestCase):
    def test_simple_replacement_outside_link(self):
        text = "The application deadline is June 1, 2025."
        result = replace_text_exclude_markdown_links(
            text, "June 1, 2025", "August 1, 2025"
        )
        self.assertEqual(result, "The application deadline is August 1, 2025.")

    def test_replacement_inside_markdown_text_only(self):
        text = "Visit [the deadline](https://grants.gov/deadline) for info."
        result = replace_text_exclude_markdown_links(text, "deadline", "date")
        self.assertEqual(
            result, "Visit [the date](https://grants.gov/deadline) for info."
        )

    def test_no_change_inside_url(self):
        text = "Check out [this link](https://example.com/deadline-info)"
        result = replace_text_exclude_markdown_links(text, "deadline", "date")
        self.assertEqual(
            result, "Check out [this link](https://example.com/deadline-info)"
        )

    def test_multiple_links_and_text(self):
        text = (
            "Apply by the deadline. See [the deadline](https://example.com/deadline) "
            "and [deadline info](#section-deadline)."
        )
        result = replace_text_exclude_markdown_links(text, "deadline", "date")
        expected = (
            "Apply by the date. See [the date](https://example.com/deadline) "
            "and [date info](#section-deadline)."
        )
        self.assertEqual(result, expected)

    def test_case_insensitive(self):
        text = "Apply before the DEADLINE. Visit [Deadline Info](https://example.com/deadline)."
        result = replace_text_exclude_markdown_links(text, "deadline", "date")
        expected = (
            "Apply before the date. Visit [date Info](https://example.com/deadline)."
        )
        self.assertEqual(result, expected)

    def test_no_links(self):
        text = "The deadline is approaching."
        result = replace_text_exclude_markdown_links(text, "deadline", "date")
        self.assertEqual(result, "The date is approaching.")

    def test_empty_input(self):
        self.assertEqual(replace_text_exclude_markdown_links("", "foo", "bar"), "")
        self.assertEqual(replace_text_exclude_markdown_links(None, "foo", "bar"), None)

    def test_link_with_special_chars(self):
        text = "Click [this (weird) deadline](https://example.com/deadline-stuff)"
        result = replace_text_exclude_markdown_links(text, "deadline", "date")
        self.assertEqual(
            result, "Click [this (weird) date](https://example.com/deadline-stuff)"
        )


class StripMarkdownLinksTests(TestCase):
    def test_removes_markdown_link_url(self):
        text = "Visit [the saloon](https://the-saloon.rodeo)"
        expected = "Visit [the saloon]"
        self.assertEqual(strip_markdown_links(text), expected)

    def test_multiple_links(self):
        text = "Links: [one](http://a.com) and [two](http://b.com)"
        expected = "Links: [one] and [two]"
        self.assertEqual(strip_markdown_links(text), expected)

    def test_no_links(self):
        text = "Just plain text."
        self.assertEqual(strip_markdown_links(text), text)

    def test_incomplete_link_syntax(self):
        text = "Here is a [link without closing"
        self.assertEqual(strip_markdown_links(text), text)

    def test_empty_string(self):
        self.assertEqual(strip_markdown_links(""), "")

    def test_none_input(self):
        self.assertIsNone(strip_markdown_links(None))

    def test_nested_like_links(self):
        text = "Check [this [nested](http://nested.com)](http://outer.com)"
        expected = "Check [this [nested]]"
        self.assertEqual(strip_markdown_links(text), expected)


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
