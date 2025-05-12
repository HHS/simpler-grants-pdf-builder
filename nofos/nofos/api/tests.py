import json
import os

from django.conf import settings
from django.test import TestCase, override_settings
from nofos.models import Nofo, Section, Subsection


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
            opdiv="Test OpDiv",
        )
        self.section = Section.objects.create(
            nofo=self.nofo, name="API Test NOFO: Section 1", order=1
        )

        # Get the default subsection and update it
        self.default_subsection = Subsection.objects.create(
            section=self.section,
            name="API Test NOFO: Subsection 1",
            tag="h3",
            body="",
            order=1,
        )

        self.minimal_compliant_payload = {
            "title": "Minimal NOFO",
            "short_name": "",
            "tagline": "",
            "application_deadline": "",
            "agency": "",
            "number": "",
            "opdiv": "Test OpDiv",
            "sections": [
                {
                    "name": "Step 1",
                    "html_id": "1--step-1",
                    "order": 1,
                    "has_section_page": True,
                    "subsections": [],
                }
            ],
        }

        # Load fixture data for import tests
        fixture_path = os.path.join(
            settings.BASE_DIR, "nofos", "fixtures", "json", "cms-u2u-25-001.json"
        )
        with open(fixture_path, "r") as f:
            self.fixture_data = json.load(f)

    def test_export_nofo(self):
        """Test exporting a NOFO via API"""
        response = self.client.get(f"/api/nofos/{self.nofo.id}", **self.headers)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], str(self.nofo.id))
        self.assertEqual(data["title"], self.nofo.title)
        self.assertEqual(data["sections"][0]["name"], self.section.name)
        self.assertEqual(
            data["sections"][0]["subsections"][0]["name"], self.default_subsection.name
        )

    def test_export_nofo_no_subsections(self):
        """Test exporting a NOFO via API"""

        # Delete the default subsection before running assertions
        self.default_subsection.delete()
        self.assertEqual(len(self.section.subsections.all()), 0)

        response = self.client.get(f"/api/nofos/{self.nofo.id}", **self.headers)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], str(self.nofo.id))
        self.assertEqual(data["title"], self.nofo.title)
        self.assertEqual(data["sections"][0]["name"], self.section.name)
        self.assertEqual(data["sections"][0]["subsections"], [])

    def test_export_archived_nofo_returns_404(self):
        """Test that archived NOFOs return 404"""
        self.nofo.archived = "2024-01-01"
        self.nofo.save()

        response = self.client.get(f"/api/nofos/{self.nofo.id}", **self.headers)

        self.assertEqual(response.status_code, 404)

    def test_export_nonexistent_nofo(self):
        """Test exporting a non-existent NOFO"""
        response = self.client.get(
            "/api/nofos/00000000-0000-0000-0000-000000000000", **self.headers
        )

        self.assertEqual(response.status_code, 404)

    def test_unauthorized_export(self):
        """Test exporting without authorization"""
        response = self.client.get(f"/api/nofos/{self.nofo.id}")
        self.assertEqual(response.status_code, 401)

    def test_import_nofo(self):
        """Test importing a valid NOFO using fixture data"""

        import_data = self.fixture_data.copy()
        import_data["id"] = "00000000-0000-0000-0000-000000000000"
        import_data["status"] = "published"
        import_data["group"] = "different-group"
        import_data["archived"] = "2024-01-01"

        response = self.client.post(
            "/api/nofos",
            data=json.dumps(import_data),
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 201)

        # Verify NOFO was created with correct data
        nofo = Nofo.objects.get(number="CMS-2U2-25-001")

        self.assertNotEqual(str(nofo.id), "00000000-0000-0000-0000-000000000000")
        self.assertEqual(nofo.status, "draft")
        self.assertEqual(nofo.group, "bloom")
        self.assertIsNone(nofo.archived)

        # Verify sections and subsections
        self.assertEqual(len(nofo.sections.all()), len(self.fixture_data["sections"]))
        first_section = nofo.sections.first()
        self.assertEqual(first_section.name, "Step 1: Review the Opportunity")
        self.assertEqual(first_section.subsections.first().name, "Basic information")

    def test_import_nofo_without_sections(self):
        """Test importing a NOFO without sections"""
        payload = self.minimal_compliant_payload
        payload["sections"] = []  # empty sections array

        response = self.client.post(
            "/api/nofos",
            data=json.dumps(payload),
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.content)
        self.assertEqual(response_json["message"], "Model validation error")
        self.assertEqual(
            response_json["details"]["__all__"], ["NOFO must have at least one section"]
        )

    def test_import_nofo_without_subsections_is_okay(self):
        """Test importing a NOFO without subsections"""
        payload = self.minimal_compliant_payload

        response = self.client.post(
            "/api/nofos",
            data=json.dumps(payload),
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 201)

    def test_import_nofo_without_subsections_key_is_not_allowed(self):
        """Test importing a NOFO without subsections key"""
        payload = self.minimal_compliant_payload
        # delete "subsections" key
        del payload["sections"][0]["subsections"]

        response = self.client.post(
            "/api/nofos",
            data=json.dumps(payload),
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 422)
        response_json = json.loads(response.content)
        self.assertEqual(response_json["detail"][0]["msg"], "Field required")

    def test_import_nofo_with_non_array_subsections_key_is_not_allowed(self):
        """Test importing a NOFO without subsections key"""
        payload = self.minimal_compliant_payload
        # set subsections key to invalid value
        payload["sections"][0]["subsections"] = None

        response = self.client.post(
            "/api/nofos",
            data=json.dumps(payload),
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.content)
        self.assertEqual(response_json["message"], "'NoneType' object is not iterable")

    def test_import_nofo_with_id(self):
        """Test that providing an ID is ignored during import"""
        # Use fixture data but modify the ID
        import_data = self.fixture_data.copy()
        import_data["id"] = "00000000-0000-0000-0000-000000000000"

        # Remove fields we don't want
        excluded_fields = ["archived", "status", "group"]
        for field in excluded_fields:
            import_data.pop(field, None)

        response = self.client.post(
            "/api/nofos",
            data=json.dumps(import_data),
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 201)

        # Verify NOFO was created with a different ID
        nofo = Nofo.objects.get(number="CMS-2U2-25-001")
        self.assertNotEqual(str(nofo.id), "00000000-0000-0000-0000-000000000000")

    def test_export_nofo_ordering(self):
        """Test that sections and subsections are returned in order"""

        import_data = self.fixture_data.copy()
        for field in ["archived", "status", "group"]:
            import_data.pop(field, None)

        response = self.client.post(
            "/api/nofos",
            data=json.dumps(import_data),
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 201)

        nofo = Nofo.objects.get(number="CMS-2U2-25-001")

        # Get sections in reverse order
        sections = list(nofo.sections.order_by("-order"))
        self.assertGreater(len(sections), 0, "Need at least one section for this test")

        # Verify sections are actually in reverse order
        section_orders = [s.order for s in sections]
        self.assertEqual(
            section_orders,
            sorted(section_orders, reverse=True),
            "Test data sections should be in reverse order",
        )

        subsections = list(sections[0].subsections.order_by("-order"))
        self.assertGreater(
            len(subsections), 0, "Need at least one subsection for this test"
        )

        # Verify subsections are actually in reverse order
        subsection_orders = [s.order for s in subsections]
        self.assertEqual(
            subsection_orders,
            sorted(subsection_orders, reverse=True),
            "Test data subsections should be in reverse order",
        )

        # Verify API returns them in ascending order
        response = self.client.get(f"/api/nofos/{nofo.id}", **self.headers)
        data = response.json()

        # Returns sections in ascending order
        api_section_orders = [s["order"] for s in data["sections"]]
        self.assertEqual(api_section_orders, sorted(api_section_orders))

        # Returns subsections in ascending order
        api_subsection_orders = [s["order"] for s in data["sections"][0]["subsections"]]
        self.assertEqual(api_subsection_orders, sorted(api_subsection_orders))
