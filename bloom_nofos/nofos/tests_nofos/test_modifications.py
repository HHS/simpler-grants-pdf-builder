from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse
from nofos.models import Nofo, Section
from users.models import BloomUser


class NofoEditModificationViewTest(TestCase):
    def setUp(self):
        """Set up test data before each test"""
        self.user = BloomUser.objects.create_user(
            email="test@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client = Client()
        self.client.login(email="test@example.com", password="testpass123")

        self.nofo = Nofo.objects.create(
            title="Test NOFO",
            short_name="test-nofo",
            number="NOFO-ACF-001",
            opdiv="ACF",
            group="bloom",
        )

        self.section = Section.objects.create(
            nofo=self.nofo,
            name="Test Section 1",
            order=1,
        )

        self.url = reverse("nofos:nofo_modifications", kwargs={"pk": self.nofo.id})

    def test_get_request_renders_template(self):
        """Ensure the GET request returns a 200 and renders the correct template."""
        # currently there is no problem with loading this template from any status
        # we just don't show you the button unless your nofo is published
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "nofos/nofo_edit_modifications.html")

    def test_post_valid_date_format_yyyy_mm_dd(self):
        """Ensure a valid YYYY-MM-DD date updates the Nofo modifications field."""
        # modifications is not set
        self.assertIsNone(self.nofo.modifications)

        # set a modified value
        self.client.post(self.url, {"modifications": "2025-02-07"})
        self.nofo.refresh_from_db()
        self.assertEqual(str(self.nofo.modifications), "2025-02-07")

    def test_post_valid_date_format_mm_dd_yyyy(self):
        """Ensure a valid MM/DD/YYYY date is converted and saved correctly."""
        # modifications is not set
        self.assertIsNone(self.nofo.modifications)

        # set a modified value
        self.client.post(self.url, {"modifications": "02/07/2025"})
        self.nofo.refresh_from_db()
        self.assertEqual(str(self.nofo.modifications), "2025-02-07")

    def test_post_invalid_date_format(self):
        """Ensure an invalid date format does not modify the NOFO and raises an error."""
        # modifications is not set
        self.assertIsNone(self.nofo.modifications)

        # set a modified value that doesn't pass validation
        # Suppress "WARNING:django.request:Bad Request: /nofos/1/edit/modifications" in Django test logs
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.post(self.url, {"modifications": "February 7, 2025"})
        self.assertEqual(response.status_code, 400)

        messages = [msg.message for msg in get_messages(response.wsgi_request)]
        self.assertIn("Invalid date format.", messages)

        # modifications is still not set
        self.nofo.refresh_from_db()
        self.assertIsNone(self.nofo.modifications)

    def test_post_creates_modifications_section_if_missing(self):
        """Ensure a 'Modifications' section is created if it does not exist."""
        modifications_section = self.nofo.sections.filter(name="Modifications").first()
        # Modifications section does not exist
        self.assertIsNone(modifications_section)

        # Create modifications value
        self.client.post(self.url, {"modifications": "2025-02-07"})
        self.nofo.refresh_from_db()

        # Now, Modifications section does exist
        modifications_section = self.nofo.sections.filter(name="Modifications").first()
        self.assertIsNotNone(modifications_section)
        self.assertEqual(modifications_section.name, "Modifications")

        # Update modifications value again
        self.client.post(self.url, {"modifications": "2025-03-07"})
        self.nofo.refresh_from_db()

        # Only 1 Modifications section exists
        modification_sections = self.nofo.sections.filter(name="Modifications")
        self.assertEqual(modification_sections.count(), 1)

        # Ensure it still has only one subsection with the expected content
        subsections = modification_sections[0].subsections.all()
        self.assertEqual(subsections.count(), 1)
        self.assertEqual(
            subsections[0].body,
            (
                "| Modification description | Date updated |\n"
                "|--------------------------|--------------|\n"
                "|                          |              |\n"
                "|                          |              |\n"
                "|                          |              |\n"
            ),
        )

    def test_post_does_not_duplicate_modifications_section(self):
        """Ensure an existing 'Modifications' section is not duplicated on repeated requests."""
        # Manually create a "Modifications" section
        Section.objects.create(
            nofo=self.nofo, name="Modifications", html_id="modifications", order=2
        )

        self.client.post(self.url, {"modifications": "2025-02-07"})
        self.nofo.refresh_from_db()

        # Should still be only one Modifications section
        modification_sections = self.nofo.sections.filter(name="Modifications")
        self.assertEqual(modification_sections.count(), 1)
