import base64
import os
from unittest.mock import patch

from bs4 import BeautifulSoup
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, Section, Subsection
from nofos.nofo import parse_uploaded_file_as_html_string
from nofos.template_versions import (
    TemplateVersionDetection,
    detect_template_version,
    detect_template_version_with_evidence,
)
from nofos.views import BaseNofoImportView, NofosImportNewView


class TemplateVersionDetectionTest(TestCase):
    def fixture_soup(self, filename):
        path = os.path.join(settings.BASE_DIR, "nofos", "fixtures", "html", filename)
        with open(path) as fixture:
            return BeautifulSoup(fixture.read(), "html.parser")

    def test_detects_fy27_master_structure(self):
        soup = self.fixture_soup("template-version--fy27-master-structure.html")

        self.assertEqual(detect_template_version(soup), "fy27")

    def test_detects_fy27_structure_after_real_docx_conversion(self):
        path = os.path.join(
            settings.BASE_DIR,
            "nofos",
            "fixtures",
            "docx",
            "template-version--fy27-master-structure.docx.b64",
        )
        with open(path) as fixture:
            docx_bytes = base64.b64decode(fixture.read())
        uploaded_file = SimpleUploadedFile(
            "template-version--fy27-master-structure.docx",
            docx_bytes,
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
        )

        converted_html = parse_uploaded_file_as_html_string(uploaded_file)
        soup = BeautifulSoup(converted_html, "html.parser")

        self.assertIsNotNone(soup.find("h1", string="Before You Get Started"))
        self.assertEqual(detect_template_version(soup), "fy27")

    def test_shared_older_structure_remains_unknown(self):
        soup = self.fixture_soup("template-version--older-content-guide-structure.html")

        self.assertEqual(detect_template_version(soup), "unknown")

    def test_requires_a_supporting_signal(self):
        soup = BeautifulSoup(
            "<h1>Before You Get Started</h1><p>Other content</p>", "html.parser"
        )

        self.assertEqual(detect_template_version(soup), "unknown")

    def test_detects_modified_template_without_expected_heading(self):
        soup = BeautifulSoup(
            """
            <h1>Start here</h1>
            <p>Application submission deadline: January 1, 2027</p>
            <p>See other key dates in the executive summary.</p>
            """,
            "html.parser",
        )

        self.assertEqual(detect_template_version(soup), "fy27")

    def test_returns_stable_diagnostic_evidence(self):
        soup = self.fixture_soup("template-version--fy27-master-structure.html")

        detection = detect_template_version_with_evidence(soup)

        self.assertEqual(detection.version, "fy27")
        self.assertEqual(detection.diagnostics["source"], "detected")
        self.assertEqual(detection.diagnostics["matched_rule"], "fy27-structure-v1")
        evaluated_rule = detection.diagnostics["evaluated_rules"][0]
        self.assertGreaterEqual(len(evaluated_rule["matched_signals"]), 2)
        self.assertEqual(evaluated_rule["minimum_matches"], 2)

    @override_settings(
        NOFO_TEMPLATE_VERSION_RULES=[
            {
                "id": "custom-rule",
                "version": "fy27",
                "signals": [
                    {
                        "id": "custom-heading",
                        "type": "heading",
                        "text": "Configurable marker",
                    }
                ],
                "minimum_matches": 1,
            }
        ]
    )
    def test_rules_are_configurable(self):
        soup = BeautifulSoup("<h2> configurable   MARKER </h2>", "html.parser")

        self.assertEqual(detect_template_version(soup), "fy27")

    def test_invalid_rule_configuration_fails_clearly(self):
        soup = BeautifulSoup("<h2>Any document</h2>", "html.parser")
        rules = [
            {
                "id": "invalid-rule",
                "version": "fy27",
                "signals": [],
                "minimum_matches": 1,
            }
        ]

        with self.assertRaisesMessage(ImproperlyConfigured, "non-empty signals"):
            detect_template_version(soup, rules=rules)

    @patch("nofos.views.detect_template_version_with_evidence")
    def test_shared_base_importer_does_not_run_nofo_detection(self, detector):
        soup = BeautifulSoup("<h1>Any document</h1>", "html.parser")

        version = BaseNofoImportView().get_imported_template_version(soup)

        self.assertEqual(version, "unknown")
        detector.assert_not_called()

    @patch(
        "nofos.views.detect_template_version_with_evidence",
        return_value=TemplateVersionDetection("fy27", {"source": "detected"}),
    )
    def test_nofo_importer_runs_detection(self, detector):
        soup = BeautifulSoup("<h1>Any document</h1>", "html.parser")

        version = NofosImportNewView().get_imported_template_version(soup)

        self.assertEqual(version, "fy27")
        detector.assert_called_once_with(soup)


class TemplateVersionLifecycleTest(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="template-version@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client.force_login(self.user)

    def uploaded_fixture(self, filename):
        path = os.path.join(settings.BASE_DIR, "nofos", "fixtures", "html", filename)
        with open(path, "rb") as fixture:
            return SimpleUploadedFile(
                filename, fixture.read(), content_type="text/html"
            )

    def test_new_nofo_defaults_to_unknown_without_import_detection(self):
        nofo = Nofo.objects.create(title="Manual NOFO", opdiv="HHS")

        self.assertEqual(nofo.template_version, "unknown")
        self.assertEqual(nofo.template_version_detection, {})

    def test_import_persists_detected_version(self):
        response = self.client.post(
            reverse("nofos:nofo_import"),
            {
                "nofo-import": self.uploaded_fixture(
                    "template-version--fy27-master-structure.html"
                )
            },
        )

        self.assertEqual(response.status_code, 302)
        nofo = Nofo.objects.latest("created")
        self.assertEqual(nofo.template_version, "fy27")
        self.assertEqual(nofo.template_version_detection["source"], "detected")
        self.assertEqual(
            nofo.template_version_detection["matched_rule"], "fy27-structure-v1"
        )

    def test_reimport_updates_version_and_preserves_historical_version(self):
        nofo = Nofo.objects.create(
            title="Existing NOFO",
            number="TEST-FY27",
            opdiv="HHS",
            group="bloom",
            template_version="pre_fy27",
            template_version_detection={"source": "manual_override"},
        )
        section = Section.objects.create(
            nofo=nofo, name="Existing section", html_id="existing-section", order=1
        )
        Subsection.objects.create(
            section=section,
            name="Existing subsection",
            html_id="existing-subsection",
            order=1,
            tag="h2",
            body="Existing body",
        )

        response = self.client.post(
            reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.id}),
            {
                "nofo-import": self.uploaded_fixture(
                    "template-version--fy27-master-structure.html"
                )
            },
        )

        self.assertEqual(response.status_code, 302)
        nofo.refresh_from_db()
        self.assertEqual(nofo.template_version, "fy27")
        historical = Nofo.objects.exclude(pk=nofo.pk).get(successor=nofo)
        self.assertEqual(historical.template_version, "pre_fy27")
        self.assertEqual(
            historical.template_version_detection, {"source": "manual_override"}
        )
        self.assertEqual(nofo.template_version_detection["source"], "detected")

    def test_user_can_correct_detected_version(self):
        nofo = Nofo.objects.create(
            title="Detected NOFO",
            opdiv="HHS",
            group="bloom",
            template_version="fy27",
            template_version_detection={
                "source": "detected",
                "matched_rule": "fy27-structure-v1",
                "evaluated_rules": [{"id": "fy27-structure-v1", "version": "fy27"}],
            },
        )

        response = self.client.post(
            reverse("nofos:nofo_edit_template_version", kwargs={"pk": nofo.id}),
            {"template_version": "pre_fy27"},
        )

        self.assertRedirects(
            response, reverse("nofos:nofo_edit", kwargs={"pk": nofo.id})
        )
        nofo.refresh_from_db()
        self.assertEqual(nofo.template_version, "pre_fy27")
        self.assertEqual(
            nofo.template_version_detection,
            {
                "source": "manual_override",
                "matched_rule": "fy27-structure-v1",
                "evaluated_rules": [{"id": "fy27-structure-v1", "version": "fy27"}],
                "detected_version": "fy27",
            },
        )
