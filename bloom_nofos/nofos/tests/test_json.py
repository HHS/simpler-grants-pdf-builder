from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from users.models import BloomUser as User
from nofos.models import Nofo, Section, Subsection


import logging


class NofoExportJsonViewTest(TestCase):

    def setUp(self):
        # disable logging otherwise test_regular_user_cannot_export_nofo emits a PermissionDenied stack trace
        logging.disable(logging.CRITICAL)

        # Create a superuser
        self.superuser = User.objects.create_superuser(
            email="admin@groundhog-day.com",
            password="superpassword",
            group="bloom",
            force_password_reset=False,
        )

        # Create a regular user
        self.regular_user = User.objects.create_user(
            email="regular@groundhog-day.com",
            password="password",
            group="bloom",
            force_password_reset=False,
        )

        # Create test NOFO object
        self.nofo = Nofo.objects.create(
            title="JSON Export NOFO",
            number="00000",
            tagline="Export me as data!",
            theme="landscape-cdc-blue",
        )

        # Create related Sections and Subsections
        self.section = Section.objects.create(
            nofo=self.nofo, name="JSON Export NOFO: Section 1", order=1
        )
        self.subsection = Subsection.objects.create(
            section=self.section,
            name="JSON Export NOFO: Subsection 1",
            order=1,
            tag="h3",
        )

    def tearDown(self):
        # enable logging again
        logging.disable(logging.NOTSET)

    def test_superuser_can_export_nofo(self):
        self.client.login(email="admin@groundhog-day.com", password="superpassword")

        # Make request to export NOFO
        response = self.client.get(
            reverse("nofos:export_nofo_json", args=[self.nofo.id])
        )

        # Assert success response and JSON structure
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        data = response.json()
        self.assertEqual(data["id"], self.nofo.id)
        self.assertEqual(data["title"], self.nofo.title)
        self.assertEqual(data["sections"][0]["name"], self.section.name)
        self.assertEqual(
            data["sections"][0]["subsections"][0]["name"], self.subsection.name
        )

    def test_regular_user_cannot_export_nofo(self):
        # Log in as regular user
        self.client.login(username="regular@groundhog-day.com", password="password")

        # Make request to export NOFO
        response = self.client.get(
            reverse("nofos:export_nofo_json", args=[self.nofo.id])
        )

        # Assert forbidden response
        self.assertEqual(response.status_code, 403)

    def test_export_nonexistent_nofo(self):
        self.client.login(email="admin@groundhog-day.com", password="superpassword")

        # Make request to export a NOFO that doesn't exist
        response = self.client.get(reverse("nofos:export_nofo_json", args=[9999]))

        # Assert 404 response
        self.assertEqual(response.status_code, 404)

    def test_archived_nofo_returns_404(self):
        self.client.login(email="admin@groundhog-day.com", password="superpassword")

        # Archive the NOFO
        self.nofo.archived = "2024-01-01"
        self.nofo.save()

        # Attempt to export the NOFO
        response = self.client.get(
            reverse("nofos:export_nofo_json", args=[self.nofo.id])
        )

        # Assert that a 404 is returned
        self.assertEqual(response.status_code, 404)


# TODO: Import a real file
class NofoImportJsonViewTest(TestCase):

    def setUp(self):
        # disable logging otherwise test_import_empty_json_file (etc) emits a WARNING stack trace
        logging.disable(logging.CRITICAL)

        # Create a superuser
        self.superuser = User.objects.create_superuser(
            email="admin@groundhog-day.com",
            password="superpassword",
            group="bloom",
            force_password_reset=False,
        )

        self.nofo_empty = "{}"
        self.nofo_no_sections = '{"title": "No sections NOFO","sections": []}'
        self.nofo_no_subsections = '{"title":"NOFO missing subsection","sections":[{"id":595,"nofo":105,"name":"Step 1: Review the Opportunity","order":1,"subsections":[{"id":9175,"section":595,"name":"Basic information","tag":"h3","body":"This is the basic information"}]},{"id":596,"nofo":105,"name":"Step 2: Something else","order":2,"subsections":[]}]}'

        # Set up the URL for the import view
        self.import_url = reverse("nofos:import_nofo_json")  # Update with your URL name

    def tearDown(self):
        # enable logging again
        logging.disable(logging.NOTSET)

    def test_import_empty_json_file(self):
        self.client.login(email="admin@groundhog-day.com", password="superpassword")

        # Upload an empty JSON file
        empty_json = SimpleUploadedFile(
            "test_import_empty_json_file.json",
            self.nofo_empty.encode("utf-8"),
            content_type="application/json",
        )

        response = self.client.post(
            self.import_url,
            {"nofo-import-json": empty_json},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Empty NOFO file.", status_code=400)

    def test_import_nofo_no_sections_json_file(self):
        self.client.login(email="admin@groundhog-day.com", password="superpassword")

        # Upload an empty JSON file
        empty_json = SimpleUploadedFile(
            "test_import_nofo_no_sections_json_file.json",
            self.nofo_no_sections.encode("utf-8"),
            content_type="application/json",
        )

        response = self.client.post(
            self.import_url,
            {"nofo-import-json": empty_json},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "NOFO must contain sections.", status_code=400)

    def test_import_nofo_no_subsections_json_file(self):
        self.client.login(email="admin@groundhog-day.com", password="superpassword")

        # Upload an empty JSON file
        empty_json = SimpleUploadedFile(
            "test_import_nofo_no_subsections_json_file.json",
            self.nofo_no_subsections.encode("utf-8"),
            content_type="application/json",
        )

        response = self.client.post(
            self.import_url,
            {"nofo-import-json": empty_json},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Sections must contain subsections.", status_code=400
        )
