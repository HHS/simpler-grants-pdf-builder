from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TransactionTestCase
from django.urls import reverse
from nofos.models import Nofo, Section, Subsection
from users.models import BloomUser


class NofoReimportTests(TransactionTestCase):
    def setUp(self):
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
            opdiv="ACF",
            group="bloom",
        )

        self.section = Section.objects.create(
            nofo=self.nofo,
            name="Test Section 1",
            order=1,
        )

        # Create test subsections with initial content and classes
        self.subsections = []
        subsection_data = [
            {
                "name": "Eligibility Information",
                "html_class": "",
                "body": "Original eligibility content",
                "order": 10,  # Using larger intervals to avoid conflicts
            },
            {
                "name": "Program Requirements",
                "html_class": "custom-class",
                "body": "Original program requirements",
                "order": 20,
            },
            {
                "name": "Award Information",
                "html_class": "",
                "body": "Original award information",
                "order": 30,
            },
        ]

        # Create subsections one at a time
        for data in subsection_data:
            subsection = Subsection.objects.create(
                section=self.section,
                name=data["name"],
                order=data["order"],
                html_class=data["html_class"],
                tag="h2",
                body=data["body"],
            )
            self.subsections.append(subsection)

    def create_test_file(self, with_page_breaks=False):
        """Create a test HTML file for reimporting with optional page breaks in content."""
        html_content = """
        <html>
        <head><title>Test NOFO</title></head>
        <body>
            <p>Opdiv: ACF</p>
            <h1>Test Section 1</h1>
            <h2 data-order="10">Eligibility Information</h2>
            <p>Updated eligibility content with new requirements</p>
            <h2 class="custom-class" data-order="20">Program Requirements</h2>
            <p>Updated program requirements with new guidelines</p>
            <h2 data-order="30">Award Information</h2>
            <p>Updated award information with new amounts</p>
        </body>
        </html>
        """
        return SimpleUploadedFile(
            "test.html", html_content.encode("utf-8"), content_type="text/html"
        )

    def test_reimport_preserves_page_breaks_when_checked(self):
        """Test that page breaks are preserved when checkbox is checked while content is updated."""
        # Add page breaks to simulate manual addition
        self.subsections[0].html_class = "page-break-before"
        self.subsections[0].save()
        self.subsections[1].html_class = "custom-class page-break-before"
        self.subsections[1].save()

        test_file = self.create_test_file()

        # Verify initial state
        self.assertEqual(self.subsections[0].body, "Original eligibility content")
        self.assertTrue("page-break-before" in self.subsections[0].html_class)
        self.assertTrue("page-break-before" in self.subsections[1].html_class)
        self.assertTrue("custom-class" in self.subsections[1].html_class)

        response = self.client.post(
            reverse("nofos:nofo_import_overwrite", kwargs={"pk": self.nofo.id}),
            {
                "nofo-import": test_file,
                "preserve_page_breaks": "on",
                "csrfmiddlewaretoken": "dummy",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        # Verify content was updated but page breaks were preserved
        updated_nofo = Nofo.objects.get(id=self.nofo.id)
        updated_subsections = (
            updated_nofo.sections.first().subsections.all().order_by("order")
        )

        self.assertEqual(
            updated_subsections[0].body.strip(),
            "Updated eligibility content with new requirements",
        )
        self.assertTrue("page-break-before" in updated_subsections[0].html_class)
        self.assertTrue("page-break-before" in updated_subsections[1].html_class)

    def test_reimport_does_not_preserve_page_breaks_when_unchecked(self):
        """Test that page breaks are removed when checkbox is unchecked."""
        # Add page breaks to simulate manual addition
        self.subsections[0].html_class = "page-break-before"
        self.subsections[0].save()
        self.subsections[1].html_class = "custom-class page-break-before"
        self.subsections[1].save()

        test_file = self.create_test_file()

        # Verify initial state
        self.assertEqual(self.subsections[0].body, "Original eligibility content")
        self.assertTrue("page-break-before" in self.subsections[0].html_class)
        self.assertTrue("page-break-before" in self.subsections[1].html_class)
        self.assertTrue("custom-class" in self.subsections[1].html_class)

        response = self.client.post(
            reverse("nofos:nofo_import_overwrite", kwargs={"pk": self.nofo.id}),
            {
                "nofo-import": test_file,
                "csrfmiddlewaretoken": "dummy",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        updated_nofo = Nofo.objects.get(id=self.nofo.id)
        updated_subsections = (
            updated_nofo.sections.first().subsections.all().order_by("order")
        )

        self.assertEqual(
            updated_subsections[0].body.strip(),
            "Updated eligibility content with new requirements",
        )
        self.assertFalse("page-break-before" in updated_subsections[0].html_class)
        self.assertFalse("page-break-before" in updated_subsections[1].html_class)

    def test_reimport_success_behavior(self):
        """Test success message and redirect behavior for reimport."""
        test_file = self.create_test_file()

        response = self.client.post(
            reverse("nofos:nofo_import_overwrite", kwargs={"pk": self.nofo.id}),
            {
                "nofo-import": test_file,
                "preserve_page_breaks": "on",
                "csrfmiddlewaretoken": "dummy",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(
            response.redirect_chain[0][0],
            reverse("nofos:nofo_edit", kwargs={"pk": self.nofo.id}),
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Re-imported NOFO from file: test.html")
