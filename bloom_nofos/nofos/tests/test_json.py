import json
import logging
import os

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from nofos.models import Nofo, Section, Subsection
from users.models import BloomUser as User


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

    def _load_json_fixture(self, file_name):
        """
        Internal helper method to load JSON fixtures.
        Returns a tuple: (json_data, uploaded_json_file).
        """
        # Get the absolute path to the JSON fixture file
        json_file_path = os.path.join(
            settings.BASE_DIR, "nofos", "fixtures", "json", file_name
        )

        # Load the file content as a Python dictionary
        with open(json_file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        # Read the file content for upload
        with open(json_file_path, "rb") as f:
            file_content = f.read()

        # Create the uploaded file object
        uploaded_json_file = SimpleUploadedFile(
            file_name,
            file_content,
            content_type="application/json",
        )

        return json_data, uploaded_json_file

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

    def test_import_valid_nofo_json_file(self):
        self.client.login(email="admin@groundhog-day.com", password="superpassword")

        json_data, uploaded_json_file = self._load_json_fixture("cms-u2u-25-001.json")
        response = self.client.post(
            self.import_url,
            {"nofo-import-json": uploaded_json_file},
        )

        # Redirect on successful import
        self.assertEqual(response.status_code, 302)

        # Check that the NOFO was created in the database
        nofo = Nofo.objects.get(number="CMS-2U2-25-001")
        self.assertEqual(
            nofo.title,
            "EHB-Benchmark Plan Modernization Grant for States with a Federally-facilitated Exchange",
        )
        self.assertEqual(nofo.number, "CMS-2U2-25-001")

        # Check name of first section
        self.assertEqual(
            nofo.sections.first().name,
            "Step 1: Review the Opportunity",
        )

        # Check name of first subsection
        self.assertEqual(
            nofo.sections.first().subsections.all()[0].name,
            "Basic information",
        )

        # Check equal number of sections in json data vs imported NOFO
        sections = Section.objects.filter(nofo=nofo)
        self.assertEqual(len(json_data["sections"]), len(sections))

        # Check equal number of sections in json data vs imported NOFO
        subsection_count = sum(
            len(section["subsections"]) for section in json_data["sections"]
        )
        subsections = Subsection.objects.filter(section__nofo=nofo)
        self.assertEqual(subsection_count, len(subsections))

    def test_import_valid_nofo_json_file_with_published_coach_designer(self):
        self.client.login(email="admin@groundhog-day.com", password="superpassword")

        json_data, uploaded_json_file = self._load_json_fixture(
            "published-cms-u2u-25-001.json"
        )
        response = self.client.post(
            self.import_url,
            {"nofo-import-json": uploaded_json_file},
        )

        # Redirect on successful import
        self.assertEqual(response.status_code, 302)

        # Check that the NOFO was created in the database
        nofo = Nofo.objects.get(number="CMS-2U2-25-001")

        # check that status is "published" in JSON, "draft" in object
        self.assertEqual(json_data["status"], "published")
        self.assertEqual(nofo.status, "draft")

        # check coach is "aarti" in JSON, empty string in object
        self.assertEqual(json_data["coach"], "aarti")
        self.assertEqual(nofo.coach, "")

        # check designer is "abbey" in JSON, empty string in object
        self.assertEqual(json_data["designer"], "bloom-abbey")
        self.assertEqual(nofo.designer, "")

    def test_import_valid_nofo_json_file_with_hrsa_active_designer(self):
        self.client.login(email="admin@groundhog-day.com", password="superpassword")

        json_data, uploaded_json_file = self._load_json_fixture(
            "hrsa-cms-u2u-25-001.json"
        )
        response = self.client.post(
            self.import_url,
            {"nofo-import-json": uploaded_json_file},
        )

        # Redirect on successful import
        self.assertEqual(response.status_code, 302)

        # Check that the NOFO was created in the database
        nofo = Nofo.objects.get(number="CMS-2U2-25-001")

        # check that status is "active" in JSON, "draft" in object
        self.assertEqual(json_data["status"], "active")
        self.assertEqual(nofo.status, "draft")

        # check designer is "betty" in JSON, empty string in object
        self.assertEqual(json_data["designer"], "hrsa-betty")
        self.assertEqual(nofo.designer, "")

        # check group is "hrsa" in JSON, empty string in object
        self.assertEqual(json_data["group"], "hrsa")
        self.assertEqual(nofo.group, "bloom")
