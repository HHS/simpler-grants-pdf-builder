import json
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from nofos.models import HeadingValidationError, Nofo, Section, Subsection
from users.models import BloomUser


class NofoModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Load fixture data directly
        fixture_path = os.path.join(
            settings.BASE_DIR, "nofos", "fixtures", "json", "cms-u2u-25-001.json"
        )
        with open(fixture_path, "r") as f:
            cls.fixture_data = json.load(f)

        # Create NOFO from fixture data
        cls.valid_nofo_data = {
            "title": cls.fixture_data["title"],
            "filename": cls.fixture_data["filename"],
            "short_name": cls.fixture_data["short_name"],
            "number": cls.fixture_data["number"],
            "opdiv": cls.fixture_data["opdiv"],
            "agency": cls.fixture_data["agency"],
            "application_deadline": cls.fixture_data["application_deadline"],
            "tagline": cls.fixture_data["tagline"],
        }

    def test_nofo_requires_opdiv(self):
        """Test that a NOFO requires an Operating Division"""
        nofo_data = self.valid_nofo_data.copy()
        nofo_data.pop("opdiv")  # Remove opdiv
        nofo = Nofo(**nofo_data)

        with self.assertRaises(ValidationError) as context:
            nofo.full_clean()
        self.assertIn("opdiv", context.exception.message_dict)

    def test_nofo_requires_title_or_number(self):
        """Test that a NOFO requires either a title or number"""
        nofo_data = self.valid_nofo_data.copy()
        nofo_data.pop("title")
        nofo_data.pop("number")
        nofo = Nofo(**nofo_data)

        with self.assertRaises(ValidationError) as context:
            nofo.full_clean()
        self.assertIn("title", context.exception.message_dict)
        self.assertIn("number", context.exception.message_dict)

    def test_nofo_title_max_length(self):
        """Test that a NOFO title cannot exceed 250 characters"""
        nofo_data = self.valid_nofo_data.copy()
        nofo_data["title"] = "a" * 251  # One character too long
        nofo = Nofo(**nofo_data)

        with self.assertRaises(ValidationError) as context:
            nofo.full_clean()
        self.assertIn("title", context.exception.message_dict)

    def test_valid_nofo_data(self):
        """Test that our fixture data is valid"""
        nofo = Nofo(**self.valid_nofo_data)
        try:
            nofo.full_clean()
        except ValidationError as e:
            self.fail(f"Valid NOFO data raised ValidationError: {e}")


class NofoArchiveTest(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.nofo = Nofo.objects.create(
            title="Test NOFO", opdiv="Test OpDiv", status="draft"
        )

    def test_can_archive_nofo_without_sections(self):
        """Test that a NOFO can be archived even when it has no sections (which would normally fail validation)"""
        self.client.force_login(self.user)

        # Verify the NOFO has no sections
        self.assertEqual(self.nofo.sections.count(), 0)

        response = self.client.post(
            reverse("nofos:nofo_archive", kwargs={"pk": self.nofo.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("nofos:nofo_index"))

        # Verify the NOFO was archived
        self.nofo.refresh_from_db()
        self.assertIsNotNone(self.nofo.archived)

    def test_cannot_archive_published_nofo(self):
        """Test that a published NOFO cannot be archived"""
        self.client.force_login(self.user)

        # Set NOFO to published using update() to bypass validation
        Nofo.objects.filter(pk=self.nofo.pk).update(status="published")

        # Suppress "WARNING:django.request:Bad Request: /nofos/1/delete" in Django test logs
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.post(
                reverse("nofos:nofo_archive", kwargs={"pk": self.nofo.pk})
            )

        self.assertEqual(response.status_code, 400)

        # Verify the NOFO was not archived
        self.nofo.refresh_from_db()
        self.assertIsNone(self.nofo.archived)


class SectionModelTest(TestCase):
    def setUp(self):
        # Create a NOFO instance first
        self.nofo = Nofo.objects.create(title="Test NOFO", opdiv="Test OpDiv")

        # Update valid_section_data to use NOFO instance
        self.valid_section_data = {
            "name": "Test Section",
            "order": 1,
            "nofo": self.nofo,  # Use NOFO instance instead of ID
            "html_id": "1--test-section",  # Add default html_id
        }

    def test_section_name_max_length(self):
        section_data = self.valid_section_data.copy()
        section_data["name"] = "x" * 251  # One character more than max_length
        section = Section(**section_data)
        with self.assertRaises(ValidationError):
            section.full_clean()

    def test_empty_section_is_okay(self):
        section = Section.objects.create(**self.valid_section_data)
        section.full_clean()
        self.assertEqual(section.subsections.count(), 0)

    def test_automatic_order_assignment(self):
        # Create first section without order
        section1_data = self.valid_section_data.copy()
        section1_data.pop("order")
        section1 = Section.objects.create(**section1_data)
        self.assertEqual(section1.order, 1)

        # Create second section without order
        section2_data = self.valid_section_data.copy()
        section2_data.pop("order")
        section2_data["name"] = "Second Section"
        section2_data["html_id"] = "2--second-section"
        section2 = Section.objects.create(**section2_data)
        self.assertEqual(section2.order, 2)

    def test_order_preserved_with_explicit_value(self):
        # Create section with explicit order
        section = Section.objects.create(**self.valid_section_data)
        self.assertEqual(section.order, 1)  # Should keep the explicit order value

    def test_get_next_order_with_no_sections(self):
        # Test get_next_order when no sections exist
        next_order = Section.get_next_order(self.nofo)
        self.assertEqual(next_order, 1)

    def test_get_next_order_with_existing_sections(self):
        # Create a section with order=5
        section_data = self.valid_section_data.copy()
        section_data["order"] = 5
        Section.objects.create(**section_data)

        # Next order should be 6
        next_order = Section.get_next_order(self.nofo)
        self.assertEqual(next_order, 6)


class SectionModelInsertOrderSpaceTests(TestCase):
    def setUp(self):
        """Set up test data for each test case."""
        self.nofo = Nofo.objects.create(title="Test NOFO", opdiv="Test OpDiv")
        self.section = Section.objects.create(name="Test Section", nofo=self.nofo)

        # Create subsections with orders 1, 2, 3
        self.sub1 = Subsection.objects.create(
            section=self.section, name="Subsection 1", tag="h3", order=1
        )

        self.sub2 = Subsection.objects.create(
            section=self.section, name="Subsection 2", tag="h3", order=2
        )
        self.sub3 = Subsection.objects.create(
            section=self.section, name="Subsection 3", tag="h3", order=3
        )

    def test_insert_at_middle(self):
        """Test inserting space at order 2 shifts subsections 2 and 3 down."""
        self.section.insert_order_space(2)

        self.sub1.refresh_from_db()
        self.sub2.refresh_from_db()
        self.sub3.refresh_from_db()

        self.assertEqual(self.sub1.order, 1)  # Unchanged
        self.assertEqual(self.sub2.order, 3)  # Shifted from 2 → 3
        self.assertEqual(self.sub3.order, 4)  # Shifted from 3 → 4

    def test_insert_at_start(self):
        """Test inserting space at order 1 shifts all subsections down."""
        self.section.insert_order_space(1)

        self.sub1.refresh_from_db()
        self.sub2.refresh_from_db()
        self.sub3.refresh_from_db()

        self.assertEqual(self.sub1.order, 2)  # Shifted from 1 → 2
        self.assertEqual(self.sub2.order, 3)  # Shifted from 2 → 3
        self.assertEqual(self.sub3.order, 4)  # Shifted from 3 → 4

    def test_insert_at_end(self):
        """Test inserting space at order 5 (end) should have no effect."""
        self.section.insert_order_space(5)

        self.sub1.refresh_from_db()
        self.sub2.refresh_from_db()
        self.sub3.refresh_from_db()

        self.assertEqual(self.sub1.order, 1)  # Unchanged
        self.assertEqual(self.sub2.order, 2)  # Unchanged
        self.assertEqual(self.sub3.order, 3)  # Unchanged

    def test_multiple_insertions(self):
        """Test inserting space multiple times at different positions."""
        self.section.insert_order_space(2)  # First shift at order 2
        self.section.insert_order_space(3)  # Second shift at order 3

        self.sub1.refresh_from_db()
        self.sub2.refresh_from_db()
        self.sub3.refresh_from_db()

        self.assertEqual(self.sub1.order, 1)  # Unchanged
        self.assertEqual(self.sub2.order, 4)  # Shifted from 2 → 3 → 4
        self.assertEqual(self.sub3.order, 5)  # Shifted from 3 → 4 → 5


class SubsectionModelTest(TestCase):
    def setUp(self):
        self.nofo = Nofo.objects.create(title="Test NOFO", opdiv="Test OpDiv")
        self.section = Section.objects.create(
            name="Test Section", order=1, nofo=self.nofo, html_id="1--test-section"
        )

        # when sections are created, an empty subsection is created at "order=1"
        self.valid_subsection_data = {
            "name": "Test Subsection",
            "order": 2,
            "section": self.section,
            "tag": "h2",
        }

    def test_subsection_name_max_length(self):
        subsection_data = self.valid_subsection_data.copy()
        subsection_data["name"] = "x" * 401  # One character more than max_length
        subsection = Subsection(**subsection_data)

        with self.assertRaises(HeadingValidationError) as cm:
            subsection.full_clean()

        expected_message = (
            "Heading too long: Found a heading exceeding 400 characters in the "
            "'Test Section' section (subsection #2).\n\n"
            "This often means a paragraph was incorrectly styled as a heading. "
            "Please check this section and ensure only actual headings are marked as headings."
        )
        self.assertEqual(str(cm.exception), expected_message)

    def test_subsection_tag_required_with_name(self):
        subsection_data = self.valid_subsection_data.copy()
        subsection_data.pop("tag")  # Remove tag
        subsection = Subsection(**subsection_data)
        with self.assertRaises(ValidationError):
            subsection.full_clean()

    def test_valid_subsection_data(self):
        subsection = Subsection(**self.valid_subsection_data)
        subsection.full_clean()  # Should not raise ValidationError

    def test_subsection_get_next(self):
        subsection_data_2 = self.valid_subsection_data.copy()
        subsection_data_2["name"] = "Test Subsection"
        subsection_data_2["order"] = 3

        subsection = Subsection.objects.create(**self.valid_subsection_data)
        subsection_2 = Subsection.objects.create(**subsection_data_2)

        self.assertEqual(subsection.get_next_subsection(), subsection_2)

    def test_subsection_get_next_when_no_next(self):
        subsection = Subsection.objects.create(**self.valid_subsection_data)

        self.assertEqual(subsection.get_next_subsection(), None)

    def test_subsection_get_previous(self):
        # when a section is created, an empty subsection is created at "order=1"
        first_subsection = self.section.subsections.first()
        subsection = Subsection.objects.create(**self.valid_subsection_data)

        self.assertEqual(subsection.get_previous_subsection(), first_subsection)


class SubsectionMatchingTest(TestCase):
    def setUp(self):
        """Set up test NOFOs, sections, and subsections."""
        self.nofo1 = Nofo.objects.create(title="NOFO 1", opdiv="OpDiv 1")
        self.nofo2 = Nofo.objects.create(title="NOFO 2", opdiv="OpDiv 2")

        self.section1_nofo1 = Section.objects.create(
            name="Section 1", order=1, nofo=self.nofo1, html_id="s1"
        )
        self.section1_nofo2 = Section.objects.create(
            name="Section 1", order=1, nofo=self.nofo2, html_id="s1"
        )

        # Create an empty subsection for each section
        self.sub1_nofo1 = Subsection.objects.create(
            section=self.section1_nofo1,
            name="",
            order=1,
            body="",
        )
        self.sub1_nofo2 = Subsection.objects.create(
            section=self.section1_nofo2,
            name="",
            order=1,
            body="",
        )

    def test_same_section_same_name(self):
        """Subsections with the same name but in different sections should not match."""
        sub1 = Subsection.objects.create(
            name="Key Facts", order=2, section=self.section1_nofo1, tag="h4"
        )
        sub2 = Subsection.objects.create(
            name="Key Facts", order=2, section=self.section1_nofo2, tag="h4"
        )

        self.assertTrue(sub1.is_matching_subsection(sub2))

    def test_different_section_same_name(self):
        """Subsections in the same section but with different names should not match."""
        # section.name == "Section 1"
        sub1 = Subsection.objects.create(
            name="Key Facts", order=2, section=self.section1_nofo1, tag="h4"
        )

        # create same subsection in differently-named section
        section2_nofo2 = Section.objects.create(
            name="Section 2: new section", order=2, nofo=self.nofo2, html_id="s2"
        )
        sub2 = Subsection.objects.create(
            name="Key Facts", order=2, section=section2_nofo2, tag="h4"
        )

        self.assertFalse(sub1.is_matching_subsection(sub2))

    def test_same_section_different_name(self):
        """Subsections in the same section but with different names should not match."""
        sub1 = Subsection.objects.create(
            name="Overview", order=2, section=self.section1_nofo1, tag="h3"
        )
        sub2 = Subsection.objects.create(
            name="Summary", order=2, section=self.section1_nofo2, tag="h3"
        )

        self.assertFalse(sub1.is_matching_subsection(sub2))

    def test_same_subsection_from_same_nofo(self):
        """A section with only one subsection should match if both NOFOs have only one unnamed subsection."""
        self.assertFalse(self.sub1_nofo1.is_matching_subsection(self.sub1_nofo1))

    def test_section_with_one_subsection(self):
        """A section with only one subsection should match if both NOFOs have only one unnamed subsection."""
        self.assertTrue(self.sub1_nofo1.is_matching_subsection(self.sub1_nofo2))

    def test_sections_with_lopsided_unnamed_subsections(self):
        """A section with only one unnamed subsection should match if the other NOFO also has only one unnamed subsection."""
        sub1 = Subsection.objects.create(name="", order=2, section=self.section1_nofo1)
        sub2 = Subsection.objects.create(name="", order=3, section=self.section1_nofo1)

        # first nofo.section has 3 unnamed subsections, second nofo.section has 1 unnamed subsection
        self.assertFalse(sub2.is_matching_subsection(self.sub1_nofo2))

    def test_section_with_multiple_unnamed_subsections(self):
        """Sections with multiple unnamed subsections should match only if their relative positions align."""
        sub1_a = Subsection.objects.create(
            name="", order=2, section=self.section1_nofo1
        )
        sub1_b = Subsection.objects.create(
            name="", order=3, section=self.section1_nofo1
        )

        sub2_a = Subsection.objects.create(
            name="", order=2, section=self.section1_nofo2
        )
        sub2_b = Subsection.objects.create(
            name="", order=3, section=self.section1_nofo2
        )

        self.assertTrue(sub1_a.is_matching_subsection(sub2_a))
        self.assertTrue(sub1_b.is_matching_subsection(sub2_b))

    def test_both_previous_and_next_must_match(self):
        """If both previous and next subsections match, the unnamed subsection should match."""
        prev1 = Subsection.objects.create(
            name="Prev", tag="h3", order=2, section=self.section1_nofo1
        )
        target1 = Subsection.objects.create(
            name="", order=3, section=self.section1_nofo1
        )
        next1 = Subsection.objects.create(
            name="Next", tag="h3", order=4, section=self.section1_nofo1
        )

        prev2 = Subsection.objects.create(
            name="Prev", tag="h3", order=2, section=self.section1_nofo2
        )
        target2 = Subsection.objects.create(
            name="", order=3, section=self.section1_nofo2
        )
        # Different name
        next2 = Subsection.objects.create(
            name="Next", tag="h3", order=4, section=self.section1_nofo2
        )

        # all true
        self.assertTrue(prev1.is_matching_subsection(prev2))
        self.assertTrue(next1.is_matching_subsection(next2))
        self.assertTrue(target1.is_matching_subsection(target2))

    def test_previous_and_next_must_match(self):
        """If only one of previous/next subsections match, the unnamed subsection should not match."""
        prev1 = Subsection.objects.create(
            name="Prev", tag="h3", order=2, section=self.section1_nofo1
        )
        target1 = Subsection.objects.create(
            name="", order=3, section=self.section1_nofo1
        )
        next1 = Subsection.objects.create(
            name="Next", tag="h3", order=4, section=self.section1_nofo1
        )

        prev2 = Subsection.objects.create(
            name="Prev", tag="h3", order=2, section=self.section1_nofo2
        )
        target2 = Subsection.objects.create(
            name="", order=3, section=self.section1_nofo2
        )
        # Different name
        next2 = Subsection.objects.create(
            name="Changed Next", tag="h3", order=4, section=self.section1_nofo2
        )

        # true because everything matches about these specific subsections
        self.assertTrue(prev1.is_matching_subsection(prev2))

        # false because the names don't match
        self.assertFalse(next1.is_matching_subsection(next2))

        # false because adjacent subsection (next) doesn't match
        self.assertFalse(target1.is_matching_subsection(target2))

    def test_section_with_multiple_unnamed_subsections(self):
        """Sections with multiple unnamed subsections should match only if their relative positions align."""
        sub1_a = Subsection.objects.create(
            name="", order=2, section=self.section1_nofo1
        )
        sub1_b = Subsection.objects.create(
            name="Nofo 1 ABC", tag="h3", order=3, section=self.section1_nofo1
        )

        sub2_a = Subsection.objects.create(
            name="", order=2, section=self.section1_nofo2
        )
        sub2_b = Subsection.objects.create(
            name="Nofo 2 DEF", tag="h3", order=3, section=self.section1_nofo2
        )

        # all of these are false because the final subsection names don't match
        self.assertFalse(self.sub1_nofo1.is_matching_subsection(self.sub1_nofo2))
        self.assertFalse(sub1_a.is_matching_subsection(sub2_a))
        self.assertFalse(sub1_b.is_matching_subsection(sub2_b))
