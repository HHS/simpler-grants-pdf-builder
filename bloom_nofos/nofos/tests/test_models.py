import os
import json
from django.urls import reverse
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.conf import settings

from users.models import BloomUser
from nofos.models import Nofo, Section, Subsection, HeadingValidationError


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
        with self.assertRaises(ValidationError):
            section.full_clean()

    def test_valid_section_with_subsection(self):
        section = Section.objects.create(**self.valid_section_data)
        subsection = Subsection.objects.create(
            name="Test Subsection",
            order=1,
            section=section,  # Use section instance
            tag="h2",
            html_id="1--test-section--test-subsection",
        )
        section.full_clean()  # Should not raise ValidationError


class SubsectionModelTest(TestCase):
    def setUp(self):
        # Create required parent objects
        self.nofo = Nofo.objects.create(title="Test NOFO", opdiv="Test OpDiv")
        self.section = Section.objects.create(
            name="Test Section", order=1, nofo=self.nofo
        )

        # Update valid_subsection_data to use Section instance
        self.valid_subsection_data = {
            "name": "Test Subsection",
            "order": 1,
            "section": self.section,  # Use section instance instead of ID
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
            "'Test Section' section (subsection #1).\n\n"
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

        response = self.client.post(
            reverse("nofos:nofo_archive", kwargs={"pk": self.nofo.pk})
        )

        self.assertEqual(response.status_code, 400)

        # Verify the NOFO was not archived
        self.nofo.refresh_from_db()
        self.assertIsNone(self.nofo.archived)
