from importlib.util import find_spec
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, Section, Subsection
from nofos.readability import (
    PROFILE_REFERENCE,
    ReadabilityMetricsAnalysisError,
    ReadabilityMetricsUnavailable,
    analyze_nofo_readability,
    render_nofo_export_document,
)


class NofoReadabilityMetricsTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="readability@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.nofo = Nofo.objects.create(
            title="Readability test NOFO",
            short_name="readability-test",
            number="TEST-READ-001",
            opdiv="TEST",
            group="bloom",
            status="draft",
        )
        section = Section.objects.create(
            nofo=self.nofo,
            name="Step 1: Review the Opportunity",
            html_id="step-1-review-the-opportunity",
            order=1,
        )
        Subsection.objects.create(
            section=section,
            name="Summary",
            tag="h4",
            body="Applicants describe their proposed work. We review each application.",
            order=1,
        )
        self.client = Client()
        self.client.force_login(self.user)
        self.metrics_url = reverse(
            "nofos:nofo_readability_metrics", kwargs={"pk": self.nofo.pk}
        )

    def test_metrics_fragment_is_the_same_fragment_used_by_word_export(self):
        fragment = BeautifulSoup(
            render_nofo_export_document(self.nofo), "html.parser"
        ).select_one("#download_target")
        export_response = self.client.get(
            reverse("nofos:nofo_export", kwargs={"pk": self.nofo.pk})
        )
        exported = BeautifulSoup(export_response.content, "html.parser").select_one(
            "#download_target"
        )

        self.assertEqual(str(fragment), str(exported))
        self.assertIsNone(fragment.select_one("input[name=csrfmiddlewaretoken]"))
        self.assertIsNone(fragment.select_one("header"))
        self.assertIn("Applicants describe their proposed work.", fragment.get_text())

    @override_settings(HHS_NOFO_METRICS_ENABLED=True)
    def test_edit_page_offers_on_demand_metrics_when_enabled(self):
        response = self.client.get(
            reverse("nofos:nofo_edit", kwargs={"pk": self.nofo.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="readability-metrics-panel"')
        self.assertContains(response, self.metrics_url)
        self.assertContains(response, "not saved and do not determine")
        self.assertContains(response, "data-metrics-scope-summary")
        panel = BeautifulSoup(response.content, "html.parser").select_one(
            "#readability-metrics-panel"
        )
        self.assertEqual(panel.name, "details")
        self.assertNotIn("open", panel.attrs)

    @override_settings(HHS_NOFO_METRICS_ENABLED=False)
    def test_edit_page_omits_metrics_panel_when_disabled(self):
        response = self.client.get(
            reverse("nofos:nofo_edit", kwargs={"pk": self.nofo.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="readability-metrics-panel"')

    @patch("nofos.readability.import_module")
    def test_package_call_uses_the_versioned_html_contract(self, import_module):
        captured = {}

        class FakeSourceBundle:
            @staticmethod
            def from_html(source):
                captured["source"] = source
                return "html-source-bundle"

        class FakeResult:
            def to_dict(self):
                return {
                    "schema_version": "1.1.0",
                    "result_basis": "structured_estimate",
                }

        def fake_analyze(source, **kwargs):
            captured["bundle"] = source
            captured["kwargs"] = kwargs
            return FakeResult()

        import_module.return_value = SimpleNamespace(
            SourceBundle=FakeSourceBundle,
            NofoMetricsError=RuntimeError,
            analyze=fake_analyze,
        )

        result = analyze_nofo_readability(self.nofo)

        self.assertEqual(
            result,
            {"schema_version": "1.1.0", "result_basis": "structured_estimate"},
        )
        self.assertEqual(captured["bundle"], "html-source-bundle")
        self.assertIn(b'id="download_target"', captured["source"])
        self.assertEqual(captured["kwargs"]["profile"], PROFILE_REFERENCE)
        self.assertEqual(
            captured["kwargs"]["adapter_config"], {"root_id": "download_target"}
        )
        self.assertEqual(
            captured["kwargs"]["production_path"], "nofo_builder_export_html"
        )
        self.assertEqual(captured["kwargs"]["document_id"], str(self.nofo.pk))
        self.assertEqual(captured["kwargs"]["revision"], self.nofo.updated.isoformat())

    @skipUnless(
        find_spec("hhs_nofo_metrics"),
        "hhs-nofo-metrics is not installed in this environment",
    )
    def test_real_package_analyzes_the_builder_fragment(self):
        result = analyze_nofo_readability(self.nofo)

        self.assertEqual(result["result_basis"], "structured_estimate")
        self.assertEqual(result["source"]["document_id"], str(self.nofo.pk))
        self.assertEqual(result["source"]["revision"], self.nofo.updated.isoformat())
        self.assertEqual(result["coverage"]["unknown_role_count"], 0)
        self.assertGreater(result["coverage"]["segments_total"], 0)
        self.assertEqual(result["metrics"]["word_count"]["status"], "calculated")
        self.assertGreater(result["metrics"]["word_count"]["value"], 0)

    @override_settings(HHS_NOFO_METRICS_ENABLED=False)
    @patch("nofos.views.analyze_nofo_readability")
    def test_disabled_endpoint_fails_closed(self, analyze):
        response = self.client.get(self.metrics_url)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "readability_metrics_disabled")
        analyze.assert_not_called()

    @override_settings(HHS_NOFO_METRICS_ENABLED=True)
    @patch("nofos.views.analyze_nofo_readability")
    def test_endpoint_returns_complete_package_result_without_caching(self, analyze):
        analyze.return_value = {
            "schema_version": "1.1.0",
            "result_basis": "structured_estimate",
            "metrics": {"word_count": {"status": "calculated", "value": 42}},
        }

        response = self.client.get(self.metrics_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), analyze.return_value)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        analyze.assert_called_once_with(self.nofo)

    @override_settings(HHS_NOFO_METRICS_ENABLED=True)
    @patch("nofos.views.analyze_nofo_readability")
    def test_missing_package_is_reported_as_unavailable(self, analyze):
        analyze.side_effect = ReadabilityMetricsUnavailable("Package is missing.")

        response = self.client.get(self.metrics_url)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "readability_metrics_unavailable")

    @override_settings(HHS_NOFO_METRICS_ENABLED=True)
    @patch("nofos.views.analyze_nofo_readability")
    def test_expected_analysis_error_preserves_package_error_code(self, analyze):
        analyze.side_effect = ReadabilityMetricsAnalysisError(
            {"code": "analysis_error", "message": "Could not classify source."}
        )

        response = self.client.get(self.metrics_url)

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {"code": "analysis_error", "message": "Could not classify source."},
        )

    @override_settings(HHS_NOFO_METRICS_ENABLED=True)
    @patch("nofos.views.analyze_nofo_readability", new=Mock())
    def test_group_permissions_apply_to_metrics_endpoint(self):
        other_user = BloomUser.objects.create_user(
            email="other-group@example.com",
            password="testpass123",
            group="hrsa",
            force_password_reset=False,
        )
        self.client.force_login(other_user)

        response = self.client.get(self.metrics_url)

        self.assertEqual(response.status_code, 403)
