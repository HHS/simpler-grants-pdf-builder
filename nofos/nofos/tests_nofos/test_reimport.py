from bs4 import BeautifulSoup
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from nofos.models import Nofo, Section, Subsection
from nofos.views import duplicate_nofo
from users.models import BloomUser


def create_test_html_file(opportunity_number="NOFO-ACF-001"):
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


class DuplicateNofoTests(TestCase):
    def setUp(self):
        """Set up test data: Create a NOFO with sections and subsections."""
        self.original_nofo = Nofo.objects.create(
            title="Test NOFO",
            short_name="test-nofo",
            number="NOFO-ACF-001",
            opdiv="ACF",
            group="bloom",
            status="active",
        )

        self.section = Section.objects.create(
            nofo=self.original_nofo, name="Test Section", order=1
        )

        self.subsection = Subsection.objects.create(
            section=self.section,
            name="Test Subsection",
            order=1,
            tag="h3",
            body="Test Subsection content",
        )

    def test_duplicate_nofo_creates_new_instance(self):
        """Test that duplicating a NOFO creates a new instance with a different ID."""
        new_nofo = duplicate_nofo(self.original_nofo)

        # New "copy" NOFO is created
        self.assertNotEqual(new_nofo.id, self.original_nofo.id)
        self.assertEqual(new_nofo.title, "Test NOFO (copy)")
        self.assertEqual(new_nofo.short_name, "test-nofo (copy)")
        self.assertEqual(new_nofo.status, "draft")
        self.assertEqual(new_nofo.opdiv, self.original_nofo.opdiv)

        # since this is not a "successor" nofo, successor and archived fields are None
        self.assertIsNone(new_nofo.successor)
        self.assertIsNone(new_nofo.archived)

    def test_duplicate_nofo_keeps_original_unchanged(self):
        """Ensure the original NOFO remains unchanged after duplication."""
        duplicate_nofo(self.original_nofo)

        # Refresh original NOFO from DB
        self.original_nofo.refresh_from_db()

        self.assertEqual(self.original_nofo.title, "Test NOFO")  # No change
        self.assertEqual(self.original_nofo.status, "active")  # No change
        self.assertIsNone(self.original_nofo.successor)
        self.assertIsNone(self.original_nofo.archived)

    def test_duplicate_nofo_is_successor_creates_new_successor_instance(self):
        """Test that duplicating a NOFO creates a new instance with a different ID."""
        new_nofo = duplicate_nofo(self.original_nofo, is_successor=True)

        # New "copy" NOFO is created
        self.assertNotEqual(new_nofo.id, self.original_nofo.id)
        # copy is NOT included in the title or short name
        self.assertEqual(new_nofo.title, "Test NOFO")
        self.assertEqual(new_nofo.short_name, "test-nofo")
        # status is NOT changed to draft
        self.assertEqual(new_nofo.status, "active")
        self.assertEqual(new_nofo.opdiv, self.original_nofo.opdiv)
        # archived is set
        self.assertIsNotNone(new_nofo.archived)

        # Set successor on new NOFO
        self.assertEqual(new_nofo.successor, self.original_nofo)

    def test_duplicate_nofo_copies_sections(self):
        """Test that duplicating a NOFO also duplicates its sections."""
        new_nofo = duplicate_nofo(self.original_nofo)

        self.assertEqual(new_nofo.sections.count(), 1)  # Section copied
        new_section = new_nofo.sections.first()
        self.assertEqual(new_section.name, "Test Section")
        self.assertNotEqual(new_section.id, self.section.id)  # New instance
        self.assertEqual(new_section.order, self.section.order)

    def test_duplicate_nofo_copies_subsections(self):
        """Ensure subsections are also duplicated."""
        new_nofo = duplicate_nofo(self.original_nofo)

        new_section = new_nofo.sections.first()
        self.assertEqual(new_section.subsections.count(), 1)

        new_subsection = new_section.subsections.first()
        self.assertEqual(new_subsection.name, "Test Subsection")
        self.assertEqual(new_subsection.body, "Test Subsection content")
        self.assertNotEqual(new_subsection.id, self.subsection.id)  # New instance


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

    def test_reimport_preserves_page_breaks_when_checked(self):
        """Test that page breaks are preserved when checkbox is checked while content is updated."""
        # Add page breaks to simulate manual addition
        self.subsections[0].html_class = "page-break-before"
        self.subsections[0].save()
        self.subsections[1].html_class = "custom-class page-break-before"
        self.subsections[1].save()

        test_file = create_test_html_file()

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

        test_file = create_test_html_file()

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
        test_file = create_test_html_file()

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

    def test_reimport_creates_archived_copy(self):
        """Test that reimport creates an archived copy of the existing NOFO."""
        test_file = create_test_html_file()

        # Perform reimport
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

        # Fetch the NOFOs after reimport
        nofos = Nofo.objects.filter(number=self.nofo.number)

        # Ensure we now have 2 NOFOs
        self.assertEqual(nofos.count(), 2)

        # Identify the original and new NOFOs
        original_nofo = nofos.filter(id=self.nofo.id).first()
        copied_nofo = nofos.exclude(id=self.nofo.id).first()

        # Ensure original NOFO is NOT archived
        self.assertIsNotNone(original_nofo)
        self.assertIsNone(original_nofo.archived)

        # Ensure new NOFO is archived and has the original nofo as its successor
        self.assertIsNotNone(copied_nofo)
        self.assertIsNotNone(copied_nofo.archived)
        self.assertEqual(copied_nofo.successor, original_nofo)

        # Ensure sections and subsections were copied
        self.assertEqual(copied_nofo.sections.count(), self.nofo.sections.count())
        for section in self.nofo.sections.all():
            copied_section = copied_nofo.sections.filter(name=section.name).first()
            self.assertIsNotNone(copied_section)
            self.assertEqual(
                copied_section.subsections.count(), section.subsections.count()
            )


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

        self.section = Section.objects.create(
            nofo=self.nofo, name="Test Section", order=1
        )

        self.subsection = Subsection.objects.create(
            section=self.section,
            name="Test Subsection",
            order=1,
            tag="h3",
            body="Test Subsection content",
        )

        self.import_url = reverse(
            "nofos:nofo_import_overwrite", kwargs={"pk": self.nofo.pk}
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
        test_file = create_test_html_file(opportunity_number=self.nofo.number)

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
        test_file = create_test_html_file(opportunity_number="NOFO-ACF-002")

        response = self.client.post(
            self.import_url,
            {
                "nofo-import": test_file,
                "preserve_page_breaks": "on",
                "csrfmiddlewaretoken": "dummy",
            },
            follow=False,  # don't follow redirect yet
        )

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
