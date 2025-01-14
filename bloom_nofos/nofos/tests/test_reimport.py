from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages import get_messages
from nofos.models import Nofo, Section, Subsection
from users.models import BloomUser
from django.urls import reverse


class NofoReimportTests(TestCase):
    def setUp(self):
        # Create test user with required group
        self.user = BloomUser.objects.create_user(
            email="test@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client = Client()
        self.client.login(email="test@example.com", password="testpass123")

        # Create test NOFO with required fields
        self.nofo = Nofo.objects.create(
            title="Test NOFO",
            short_name="test-nofo",
            opdiv="ACF",
            group="bloom",
        )

        # Create test section
        self.section = Section.objects.create(
            nofo=self.nofo,
            name="Test Section 1",
            order=1,
        )

        # Create test subsections with different page break classes
        self.subsections = []
        subsection_data = [
            ("Subsection 1", "page-break-before"),
            ("Subsection 2", "page-break-after"),
            ("Subsection 3", "page-break"),
            ("Subsection 4", "no-page-break"),
        ]

        for i, (name, html_class) in enumerate(subsection_data):
            subsection = Subsection.objects.create(
                section=self.section,
                name=name,
                order=i + 1,
                html_class=html_class,
                tag="h2",
                body=f"Content for {name}",
            )
            self.subsections.append(subsection)

    def create_test_file(self):
        """Create a test HTML file for reimporting."""
        html_content = """
        <html>
        <head>
            <title>Test NOFO</title>
        </head>
        <body>
            <p>Opdiv: ACF</p>
            <h1>Test Section 1</h1>
            <h2>Subsection 1</h2>
            <p>Content for Subsection 1</p>
            <h2>Subsection 2</h2>
            <p>Content for Subsection 2</p>
            <h2>Subsection 3</h2>
            <p>Content for Subsection 3</p>
            <h2>Subsection 4</h2>
            <p>Content for Subsection 4</p>
        </body>
        </html>
        """
        return SimpleUploadedFile(
            "test.html", html_content.encode("utf-8"), content_type="text/html"
        )

    def test_reimport_preserves_page_breaks_when_checked(self):
        """Test that page breaks are preserved when the checkbox is checked."""
        # Create a test file with HTML content
        test_file = self.create_test_file()

        # Make the POST request to reimport
        response = self.client.post(
            reverse("nofos:nofo_import_overwrite", kwargs={"pk": self.nofo.id}),
            {
                "nofo-import": test_file,
                "preserve_page_breaks": "on",
                "csrfmiddlewaretoken": "dummy",
            },
            follow=True,
        )

        # Check response
        self.assertEqual(response.status_code, 200)

        # Get the updated NOFO and its sections/subsections
        updated_nofo = Nofo.objects.get(id=self.nofo.id)
        updated_sections = updated_nofo.sections.all()

        # Verify page breaks were preserved
        found_page_break = False
        for section in updated_sections:
            for subsection in section.subsections.all():
                if "page-break" in subsection.html_class:
                    found_page_break = True
                    break
            if found_page_break:
                break

        self.assertTrue(
            found_page_break,
            "Expected to find at least one subsection with page-break class",
        )

    def test_reimport_does_not_preserve_page_breaks_when_unchecked(self):
        """Test that page breaks are not preserved when the checkbox is unchecked."""
        # Verify initial state has page breaks
        initial_has_page_break = False
        for section in self.nofo.sections.all():
            for subsection in section.subsections.all():
                if "page-break" in subsection.html_class:
                    initial_has_page_break = True
                    break
            if initial_has_page_break:
                break

        self.assertTrue(
            initial_has_page_break,
            "Test setup should include at least one subsection with page-break class",
        )

        # Create a test file with HTML content
        test_file = self.create_test_file()

        # Make the POST request to reimport
        response = self.client.post(
            reverse("nofos:nofo_import_overwrite", kwargs={"pk": self.nofo.id}),
            {
                "nofo-import": test_file,
                "preserve_page_breaks": "off",
                "csrfmiddlewaretoken": "dummy",
            },
            follow=True,
        )

        # Check response
        self.assertEqual(response.status_code, 200)

        # Get the updated NOFO and its sections/subsections
        updated_nofo = Nofo.objects.get(id=self.nofo.id)
        updated_sections = updated_nofo.sections.all()

        # Verify no page breaks were preserved
        for section in updated_sections:
            for subsection in section.subsections.all():
                self.assertNotIn("page-break", subsection.html_class)

    def test_reimport_success_behavior(self):
        """Test success message and redirect behavior for reimport."""
        # Create a test file with HTML content
        test_file = self.create_test_file()

        # Make the POST request to reimport
        response = self.client.post(
            reverse("nofos:nofo_import_overwrite", kwargs={"pk": self.nofo.id}),
            {
                "nofo-import": test_file,
                "preserve_page_breaks": "on",
                "csrfmiddlewaretoken": "dummy",
            },
            follow=True,
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(
            response.redirect_chain[0][0],
            reverse("nofos:nofo_edit", kwargs={"pk": self.nofo.id}),
        )

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Re-imported NOFO from file: test.html")
