"""Exercise invented pilot sources through the existing Word upload boundary."""

import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "design_pilot"


class DesignPilotFixtureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = BloomUser.objects.create_user(
            email="design-pilot@example.com",
            password=None,
            group="bloom",
            force_password_reset=False,
            is_superuser=True,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_invented_sources_cross_the_existing_import_boundary(self):
        manifest = json.loads((FIXTURES / "manifest.json").read_text())
        self.assertTrue(manifest["invented_content_only"])
        for case in manifest["cases"]:
            with self.subTest(case=case["id"]):
                data = (FIXTURES / case["file"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), case["sha256"])
                count = Nofo.objects.count()
                response = self.client.post(
                    reverse("nofos:nofo_import"),
                    {
                        "nofo-import": SimpleUploadedFile(
                            case["file"],
                            data,
                            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        )
                    },
                )
                if case["expected"] == "ambiguous_heading_hierarchy":
                    self.assertEqual(response.status_code, 422)
                    self.assertEqual(Nofo.objects.count(), count)
                    self.assertContains(
                        response, "Premature subsection", status_code=422
                    )
                    continue
                self.assertEqual(response.status_code, 302)
                self.assertEqual(Nofo.objects.count(), count + 1)
                nofo = Nofo.objects.latest("created")
                self.assertTrue(nofo.has_imported_introduction)
                self.assertEqual(nofo.title, "Synthetic community support program")
                self.assertTrue(nofo.number.startswith("SYNTHETIC-"))
                bodies = "\n".join(
                    body
                    for section in nofo.sections.all()
                    for body in section.subsections.values_list("body", flat=True)
                )
                for text in case["preserve_text"]:
                    self.assertIn(text, bodies)
                self.assertNotIn("Metadata author:", bodies)
                if case["id"] == "tables":
                    preview = self.client.get(
                        reverse("nofos:nofo_view", args=[nofo.pk])
                    )
                    self.assertEqual(preview.status_code, 200)
                    soup = BeautifulSoup(preview.content, "html.parser")
                    table = soup.find("table")
                    self.assertIsNotNone(table)
                    rows = table.find_all("tr")
                    self.assertEqual(len(rows), 11)
                    for index, row in enumerate(rows[1:], start=1):
                        self.assertEqual(
                            [
                                cell.get_text(" ", strip=True)
                                for cell in row.find_all("td")
                            ],
                            [
                                f"Material {index}",
                                "Upload a separate file with the application.",
                                str(index + 2),
                            ],
                        )
                    self.assertIn(
                        [
                            "Prepare the narrative.",
                            "Prepare the budget.",
                            "Submit both files.",
                        ],
                        [
                            [
                                item.get_text(" ", strip=True)
                                for item in ordered.find_all("li")
                            ]
                            for ordered in soup.find_all("ol")
                        ],
                    )
                if case["id"] == "judgment":
                    # Import preserves conflicting source facts, not a decision.
                    self.assertEqual(nofo.application_deadline, "December 1, 2026")
