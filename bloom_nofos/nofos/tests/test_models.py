import json
import logging
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
            "subagency": cls.fixture_data["subagency"],
            "subagency2": cls.fixture_data["subagency2"],
            "application_deadline": cls.fixture_data["application_deadline"],
            "tagline": cls.fixture_data["tagline"],
            "author": cls.fixture_data["author"],
            "subject": cls.fixture_data["subject"],
            "keywords": cls.fixture_data["keywords"],
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

    def test_section_requires_subsection(self):
        section = Section.objects.create(**self.valid_section_data)
        self.assertEqual(section.subsections.count(), 1)
        section.subsections.all().delete()
        with self.assertRaises(ValidationError):
            section.full_clean()

    def test_valid_section_with_subsection(self):
        section = Section.objects.create(**self.valid_section_data)
        subsection = Subsection.objects.create(
            name="Test Subsection",
            order=2,
            section=section,
            tag="h2",
            html_id="1--test-section--test-subsection",
        )
        section.full_clean()

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

    def test_automatic_subsection_creation(self):
        # Create section without subsection
        section_data = self.valid_section_data.copy()
        section = Section.objects.create(**section_data)

        # Verify a default subsection was created
        self.assertEqual(section.subsections.count(), 1)
        default_subsection = section.subsections.first()
        self.assertEqual(default_subsection.order, 1)

        # Verify section passes validation
        section.full_clean()  # Should not raise ValidationError

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


class SubsectionModelTest(TestCase):
    def setUp(self):
        self.nofo = Nofo.objects.create(title="Test NOFO", opdiv="Test OpDiv")
        self.section = Section.objects.create(
            name="Test Section", order=1, nofo=self.nofo, html_id="1--test-section"
        )
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
