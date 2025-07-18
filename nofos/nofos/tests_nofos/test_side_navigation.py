from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, Section, Subsection

User = get_user_model()


class SideNavigationTemplateTest(TestCase):
    """Test suite for side navigation template functionality."""

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

        # Create sections with h2 headings for navigation
        self.section1 = Section.objects.create(
            nofo=self.nofo,
            name="Section 1: Overview",
            html_id="section-1-overview",
            order=1,
        )
        self.section2 = Section.objects.create(
            nofo=self.nofo,
            name="Section 2: Requirements",
            html_id="section-2-requirements",
            order=2,
        )
        self.section3 = Section.objects.create(
            nofo=self.nofo,
            name="Section 3: Application Process",
            html_id="section-3-application-process",
            order=3,
        )

        # Create subsections
        self.subsection1 = Subsection.objects.create(
            section=self.section1,
            name="Test Subsection 1",
            order=1,
            body="Test content for subsection 1",
            tag="h3",
        )

        self.url = reverse("nofos:nofo_edit", kwargs={"pk": self.nofo.id})

    def test_side_navigation_template_included(self):
        """Test that the side navigation template is included in the NOFO edit page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "nofos/nofo_edit.html")

        # Check that the side navigation HTML structure is present
        soup = BeautifulSoup(response.content, "html.parser")
        side_nav_container = soup.find("div", {"id": "side-nav-container"})
        self.assertIsNotNone(side_nav_container)

    def test_side_navigation_html_structure(self):
        """Test that the side navigation has the correct HTML structure."""
        response = self.client.get(self.url)
        soup = BeautifulSoup(response.content, "html.parser")

        # Check main container
        side_nav_container = soup.find("div", {"id": "side-nav-container"})
        self.assertIsNotNone(side_nav_container)
        if side_nav_container:
            self.assertIn("side-nav-container", side_nav_container.get("class", []))

        # Check toggle button
        toggle_button = soup.find("button", {"id": "side-nav-toggle"})
        self.assertIsNotNone(toggle_button)
        if toggle_button:
            self.assertEqual(toggle_button.get("aria-expanded"), "false")
            self.assertEqual(toggle_button.get("aria-controls"), "side-nav-content")

        # Check navigation content
        nav_content = soup.find("div", {"id": "side-nav-content"})
        self.assertIsNotNone(nav_content)

        # Check navigation list
        nav_list = soup.find("ul", {"id": "side-nav-list"})
        self.assertIsNotNone(nav_list)
        if nav_list:
            self.assertIn("usa-sidenav", nav_list.get("class", []))

        # Check close button
        close_button = soup.find("button", {"id": "side-nav-close"})
        self.assertIsNotNone(close_button)

    def test_side_navigation_accessibility_attributes(self):
        """Test that the side navigation has proper accessibility attributes."""
        response = self.client.get(self.url)
        soup = BeautifulSoup(response.content, "html.parser")

        # Check ARIA attributes
        side_nav_content = soup.find("div", {"id": "side-nav-content"})
        self.assertEqual(side_nav_content.get("aria-hidden"), "true")

        toggle_button = soup.find("button", {"id": "side-nav-toggle"})
        self.assertEqual(toggle_button.get("aria-expanded"), "false")
        self.assertEqual(toggle_button.get("aria-controls"), "side-nav-content")
        self.assertIsNotNone(toggle_button.get("aria-label"))

        close_button = soup.find("button", {"id": "side-nav-close"})
        self.assertIsNotNone(close_button.get("aria-label"))

        # Check navigation label
        nav_element = soup.find("nav", {"aria-label": "Table of contents navigation"})
        self.assertIsNotNone(nav_element)

    def test_side_navigation_html_elements(self):
        """Test that side navigation HTML elements are generated correctly."""
        response = self.client.get(self.url)
        soup = BeautifulSoup(response.content, "html.parser")

        # Test pipe characters and links are generated correctly
        pipes = soup.find_all("span", {"class": "side-nav-pipe"})
        nav_links = soup.select("#side-nav-list a")

        # Should have 4 pipes  and 4 links (summary + 3 sections)
        self.assertEqual(len(pipes), 4)
        self.assertEqual(len(nav_links), 4)

        # Should populate attributes for each pipe and link
        for heading, pipe, link in zip(
            response.context["side_nav_headings"], pipes, nav_links
        ):
            self.assertEqual(pipe.get("data-section-id"), heading["id"])
            self.assertEqual(pipe.get("title"), heading["name"])
            self.assertEqual(link.get("href"), f"#{heading['id']}")
            self.assertEqual(link.get("data-section-id"), heading["id"])
            self.assertEqual(link.get("tabindex"), "-1")

    def test_side_navigation_with_no_sections(self):
        """Test side navigation behavior when NOFO has no sections."""
        # Create a NOFO with no sections
        empty_nofo = Nofo.objects.create(
            title="Empty NOFO",
            short_name="empty-nofo",
            number="NOFO-EMPTY-001",
            opdiv="TEST",
            group="bloom",
            status="draft",
        )

        empty_nofo_url = reverse("nofos:nofo_edit", kwargs={"pk": empty_nofo.id})
        response = self.client.get(empty_nofo_url)
        self.assertEqual(response.status_code, 200)

        # Check that side_nav_headings is empty
        side_nav_headings = response.context["side_nav_headings"]
        self.assertEqual(len(side_nav_headings), 0)

        # Assert that there is no element with id "side-nav-container"
        soup = BeautifulSoup(response.content, "html.parser")
        self.assertIsNone(soup.find("div", {"id": "side-nav-container"}))
