import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from users.models import BloomUser

from nofos.models import Nofo, Section, Subsection

User = get_user_model()


class SectionToggleTablesViewTest(TestCase):
    """Test suite for section table toggle functionality."""

    def setUp(self):
        """Set up test data before each test"""
        self.user = BloomUser.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client = Client()
        self.client.login(email="test@example.com", password="testpass123")

        self.nofo = Nofo.objects.create(
            title="Test NOFO",
            short_name="test-nofo",
            number="NOFO-TEST-001",
            opdiv="TEST",
            group="bloom",
            status="draft",
        )

        # Create test section
        self.section = Section.objects.create(
            nofo=self.nofo,
            name="Test Section",
            html_id="test-section",
            order=1,
        )

        # Create subsection with table content
        self.subsection = Subsection.objects.create(
            section=self.section,
            name="Test Subsection",
            order=1,
            body="<table><tr><td>Test table content</td></tr></table>",
            tag="h3",
        )

        self.url = reverse(
            "nofos:section_toggle_tables",
            kwargs={"pk": self.nofo.id, "section_pk": self.section.id},
        )

    def test_toggle_tables_from_default_to_full_width(self):
        """Test toggling tables from default width to full width."""
        # Ensure section starts without the full-width class
        self.assertEqual(self.section.html_class, "")

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)

        # Check JSON response
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["state"], "full-width")
        self.assertIn("expanded to full width", data["message"])
        self.assertIn(self.section.name, data["message"])

        # Check database update
        self.section.refresh_from_db()
        self.assertEqual(self.section.html_class, "section--tables-full-width")

    def test_toggle_tables_from_full_width_to_default(self):
        """Test toggling tables from full width back to default."""
        # Set section to have full-width tables initially
        self.section.html_class = "section--tables-full-width"
        self.section.save()

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)

        # Check JSON response
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["state"], "default")
        self.assertIn("default widths", data["message"])
        self.assertIn(self.section.name, data["message"])

        # Check database update
        self.section.refresh_from_db()
        self.assertEqual(self.section.html_class, "")

    def test_toggle_tables_requires_authentication(self):
        """Test that the view requires user authentication."""
        self.client.logout()
        response = self.client.post(self.url)

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_toggle_tables_requires_post_method(self):
        """Test that only POST method is allowed."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)  # Method not allowed

    def test_toggle_tables_with_invalid_section_id(self):
        """Test behavior with non-existent but valid UUID section ID."""
        import uuid

        invalid_section_id = uuid.uuid4()  # Valid UUID format but doesn't exist

        invalid_url = reverse(
            "nofos:section_toggle_tables",
            kwargs={"pk": self.nofo.id, "section_pk": invalid_section_id},
        )

        response = self.client.post(invalid_url)
        # Should return 404 when section doesn't exist
        self.assertEqual(response.status_code, 404)

    def test_toggle_tables_with_mismatched_nofo_and_section(self):
        """Test behavior when section doesn't belong to the specified NOFO."""
        # Create another NOFO and section
        other_nofo = Nofo.objects.create(
            title="Other NOFO",
            short_name="other-nofo",
            number="NOFO-OTHER-001",
            opdiv="TEST",
            group="bloom",
            status="draft",
        )

        other_section = Section.objects.create(
            nofo=other_nofo,
            name="Other Section",
            html_id="other-section",
            order=1,
        )

        # Try to toggle tables using mismatched IDs
        mismatched_url = reverse(
            "nofos:section_toggle_tables",
            kwargs={"pk": self.nofo.id, "section_pk": other_section.id},
        )

        response = self.client.post(mismatched_url)
        self.assertEqual(response.status_code, 404)

    def test_toggle_tables_prevents_published_nofo_edit(self):
        """Test that published NOFOs cannot be edited."""
        self.nofo.status = "published"
        self.nofo.save()

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 400)

        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Published NOFOs can't be edited", data["message"])

        # Ensure section wasn't modified
        self.section.refresh_from_db()
        self.assertEqual(self.section.html_class, "")

    def test_toggle_tables_prevents_cancelled_nofo_edit(self):
        """Test that cancelled NOFOs cannot be edited."""
        self.nofo.status = "cancelled"
        self.nofo.save()

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 400)

        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("This NOFO was cancelled and can't be changed.", data["message"])

        # Ensure section wasn't modified
        self.section.refresh_from_db()
        self.assertEqual(self.section.html_class, "")

    def test_toggle_tables_requires_group_permission(self):
        """Test that user must have proper group permissions."""
        # Create user with different group
        other_user = BloomUser.objects.create_user(
            email="other@example.com",
            password="testpass123",
            group="other_group",
            force_password_reset=False,
        )

        self.client.logout()
        self.client.login(email="other@example.com", password="testpass123")

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)  # Forbidden


class NofoSectionDetailViewTest(TestCase):
    """Test suite for section detail view functionality."""

    def setUp(self):
        """Set up test data before each test"""
        self.user = BloomUser.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client = Client()
        self.client.login(email="test@example.com", password="testpass123")

        self.nofo = Nofo.objects.create(
            title="Test NOFO",
            short_name="test-nofo",
            number="NOFO-TEST-001",
            opdiv="TEST",
            group="bloom",
            status="draft",
        )

        self.section = Section.objects.create(
            nofo=self.nofo,
            name="Test Section",
            html_id="test-section",
            order=1,
        )

        self.url = reverse(
            "nofos:section_detail",
            kwargs={"pk": self.nofo.id, "section_pk": self.section.id},
        )

    def test_section_detail_view_loads_successfully(self):
        """Test that section detail view loads with correct template."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "nofos/section_detail.html")

    def test_section_detail_view_context_data(self):
        """Test that section detail view provides correct context."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Check context contains required objects
        self.assertIn("subsection", response.context)
        self.assertIn("nofo", response.context)
        self.assertEqual(response.context["subsection"], self.section)
        self.assertEqual(response.context["nofo"], self.nofo)

    def test_section_detail_view_requires_authentication(self):
        """Test that section detail view requires authentication."""
        self.client.logout()
        response = self.client.get(self.url)

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_section_detail_view_with_invalid_nofo_section_mismatch(self):
        """Test behavior when section doesn't belong to specified NOFO."""
        # Create another NOFO
        other_nofo = Nofo.objects.create(
            title="Other NOFO",
            short_name="other-nofo",
            number="NOFO-OTHER-001",
            opdiv="TEST",
            group="bloom",
            status="draft",
        )

        # Try to access section with wrong NOFO ID
        invalid_url = reverse(
            "nofos:section_detail",
            kwargs={"pk": other_nofo.id, "section_pk": self.section.id},
        )

        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, 400)  # Bad request

    def test_section_detail_view_with_subsections(self):
        """Test section detail view displays subsections correctly."""
        # Create some subsections
        subsection1 = Subsection.objects.create(
            section=self.section,
            name="Subsection 1",
            order=1,
            body="Content 1",
            tag="h3",
        )
        subsection2 = Subsection.objects.create(
            section=self.section,
            name="Subsection 2",
            order=2,
            body="Content 2",
            tag="h3",
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Check that subsections are displayed
        self.assertContains(response, "Subsection 1")
        self.assertContains(response, "Subsection 2")
        self.assertContains(response, "Content 1")
        self.assertContains(response, "Content 2")
