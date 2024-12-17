from django.test import TestCase, override_settings
from django.conf import settings
from nofos.models import Nofo, Section, Subsection
import json
import os


@override_settings(API_TOKEN="test-token-for-ci")
class NofoAPITest(TestCase):
    def setUp(self):
        self.valid_token = "test-token-for-ci"
        self.headers = {
            "HTTP_AUTHORIZATION": f"Bearer {self.valid_token}",
        }

        # Create test NOFO for export tests
        self.nofo = Nofo.objects.create(
            title="API Test NOFO",
            number="00000",
            tagline="Test me via API!",
            theme="landscape-cdc-blue",
            group="bloom",
        )
        self.section = Section.objects.create(
            nofo=self.nofo, name="API Test NOFO: Section 1", order=1
        )
        self.subsection = Subsection.objects.create(
            section=self.section,
            name="API Test NOFO: Subsection 1",
            order=1,
            tag="h3",
        )

        # Load fixture data for import tests
        fixture_path = os.path.join(
            settings.BASE_DIR, "nofos", "fixtures", "json", "cms-u2u-25-001.json"
        )
        with open(fixture_path, "r") as f:
            self.fixture_data = json.load(f)

    def test_export_nofo(self):
        """Test exporting a NOFO via API"""
        response = self.client.get(f"/api/nofo/{self.nofo.id}", **self.headers)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], self.nofo.id)
        self.assertEqual(data["title"], self.nofo.title)
        self.assertEqual(data["sections"][0]["name"], self.section.name)
        self.assertEqual(
            data["sections"][0]["subsections"][0]["name"], self.subsection.name
        )

    def test_export_archived_nofo_returns_404(self):
        """Test that archived NOFOs return 404"""
        self.nofo.archived = "2024-01-01"
        self.nofo.save()

        response = self.client.get(f"/api/nofo/{self.nofo.id}", **self.headers)

        self.assertEqual(response.status_code, 404)

    def test_export_nonexistent_nofo(self):
        """Test exporting a non-existent NOFO"""
        response = self.client.get("/api/nofo/99999", **self.headers)

        self.assertEqual(response.status_code, 404)

    def test_unauthorized_export(self):
        """Test exporting without authorization"""
        response = self.client.get(f"/api/nofo/{self.nofo.id}")
        self.assertEqual(response.status_code, 401)

    def test_import_nofo(self):
        """Test importing a valid NOFO using fixture data"""
        # Prepare fixture data by removing fields we don't want
        import_data = self.fixture_data.copy()
        excluded_fields = ["id", "archived", "status", "group"]
        for field in excluded_fields:
            import_data.pop(field, None)

        response = self.client.post(
            "/api/nofo/import",
            data=json.dumps(import_data),
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 201)

        # Verify NOFO was created with correct data
        nofo = Nofo.objects.get(number="CMS-2U2-25-001")
        self.assertEqual(
            nofo.title,
            "EHB-Benchmark Plan Modernization Grant for States with a Federally-facilitated Exchange",
        )
        self.assertEqual(nofo.group, "bloom")

        # Verify sections and subsections
        self.assertEqual(len(nofo.sections.all()), len(self.fixture_data["sections"]))
        first_section = nofo.sections.first()
        self.assertEqual(first_section.name, "Step 1: Review the Opportunity")
        self.assertEqual(first_section.subsections.first().name, "Basic information")

    def test_import_nofo_without_sections(self):
        """Test importing a NOFO without sections"""
        payload = {"title": "No Sections NOFO", "number": "TEST-002", "sections": []}

        response = self.client.post(
            "/api/nofo/import",
            data=json.dumps(payload),
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 400)

    def test_import_nofo_with_id(self):
        """Test that providing an ID is ignored during import"""
        # Use fixture data but modify the ID
        import_data = self.fixture_data.copy()
        import_data["id"] = 999

        # Remove fields we don't want
        excluded_fields = ["archived", "status", "group"]
        for field in excluded_fields:
            import_data.pop(field, None)

        response = self.client.post(
            "/api/nofo/import",
            data=json.dumps(import_data),
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 201)

        # Verify NOFO was created with a different ID
        nofo = Nofo.objects.get(number="CMS-2U2-25-001")
        self.assertNotEqual(nofo.id, 999)
