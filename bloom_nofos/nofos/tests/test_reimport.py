from bs4 import BeautifulSoup
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, TransactionTestCase
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
            number="NOFO-ACF-001",
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
        <body>
            <p>Opportunity name: Test NOFO</p>
            <p>Opdiv: ACF</p>
            <p>Opportunity number: NOFO-ACF-001</p>
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


class NofosImportOverwriteViewTests(TestCase):
    def setUp(self):
        """
        Create a test client and a sample NOFO object.
        """
        self.user = BloomUser.objects.create_user(
            email="test@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client = Client()
        self.client.login(email="test@example.com", password="testpass123")

        # Create an existing NOFO with a known ID
        self.nofo = Nofo.objects.create(
            title="Test NOFO",
            short_name="test-nofo",
            number="NOFO-ACF-001",
            opdiv="ACF",
            group="bloom",
        )

        self.import_url = reverse(
            "nofos:nofo_import_overwrite", kwargs={"pk": self.nofo.pk}
        )

    def create_test_html_file(self, opportunity_number="NOFO-ACF-001"):
        """Create a test HTML file for reimporting with a given opportunity number."""
        html_content = f"""
        <html>
        <head><title>Test NOFO</title></head>
        <body>
            <p>Opportunity name: Test NOFO</p>
            <p>Opdiv: ACF</p>
            <p>Opportunity number: {opportunity_number}</p>
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

    def test_import_overwrite_view_get(self):
        """
        Test that the GET request for the NOFO import overwrite view returns a 200 status
        and contains an <h1> tag.
        """
        response = self.client.get(self.import_url)

        self.assertEqual(response.status_code, 200)

        # Check that the page contains an <h1> tag (assuming the page renders correctly)
        soup = BeautifulSoup(response.content, "html.parser")
        h1_tag = soup.find("h1")
        self.assertEqual(h1_tag.text, "Re-import “{}”".format(self.nofo.short_name))

    def test_import_overwrite_view_post(self):
        """
        Test that POSTing an HTML file with a the same NOFO ID works as expected
        """
        # Create a test HTML file with the same NOFO id
        test_file = self.create_test_html_file(opportunity_number=self.nofo.number)

        response = self.client.post(
            self.import_url,
            {
                "nofo-import": test_file,
                "preserve_page_breaks": "on",
                "csrfmiddlewaretoken": "dummy",
            },
            follow=False,  # don't follow redirect yet
        )

        # confirm it redirects back to the NOFO edit page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, reverse("nofos:nofo_edit", kwargs={"pk": self.nofo.pk})
        )

        # follow the response
        response_followed = self.client.get(response.url)
        soup = BeautifulSoup(response_followed.content, "html.parser")
        # h1 is short_name of nofo
        self.assertEqual(soup.find("h1").text, self.nofo.short_name)
        # h4 heading is the success message
        self.assertEqual(
            soup.find("h4", class_="usa-alert__heading").text, "NOFO saved successfully"
        )
        # p inside alert box tells us what NOFO was imported
        self.assertEqual(
            soup.find("p", class_="usa-alert__text").text.strip(),
            "Re-imported NOFO from file: test.html",
        )

    def test_import_overwrite_view_post_redirects_to_confirm(self):
        """
        Test that POSTing an HTML file with a different NOFO ID redirects to the nofo edit page
        """
        # Create a test HTML file with the same NOFO id
        test_file = self.create_test_html_file(opportunity_number="NOFO-ACF-002")

        response = self.client.post(
            self.import_url,
            {
                "nofo-import": test_file,
                "preserve_page_breaks": "on",
                "csrfmiddlewaretoken": "dummy",
            },
            follow=False,  # don't follow redirect yet
        )

        # confirm it redirects to to the NOFO edit page
        # confirm it redirects to the confirm-import page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("nofos:nofo_import_confirm_overwrite", kwargs={"pk": self.nofo.pk}),
        )

        # follow the response
        response_followed = self.client.get(response.url)
        soup = BeautifulSoup(response_followed.content, "html.parser")

        # Find the <h1> element
        h1_tag = soup.find("h1")
        p_after_h1 = h1_tag.find_next_sibling("p")

        # h1 asks to confirm intent to overwrite
        self.assertEqual(
            h1_tag.text,
            "Confirm re-import for “{}”".format(self.nofo.short_name),
        )
        # p following the h1 warns you that IDs are different
        self.assertEqual(
            p_after_h1.text.strip(),
            "The document you uploaded has a different opportunity number than the current NOFO.",
        )
