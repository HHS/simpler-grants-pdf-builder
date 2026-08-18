import json
from importlib.util import find_spec
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, Section, Subsection
from nofos.readability import (
    PROFILE_REFERENCE,
    ReadabilityMetricsAnalysisError,
    ReadabilityMetricsUnavailable,
    analyze_nofo_readability,
    normalize_readability_metric_goals,
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

    @override_settings(
        HHS_NOFO_METRICS_ENABLED=True,
        HHS_NOFO_METRIC_GOALS={},
    )
    def test_edit_page_offers_revision_scoped_metrics_when_enabled(self):
        response = self.client.get(
            reverse("nofos:nofo_edit", kwargs={"pk": self.nofo.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="readability-metrics-panel"')
        self.assertContains(response, self.metrics_url)
        self.assertContains(response, ">Beta</span>", html=False)
        self.assertContains(response, "Metrics reflect the current revision only")
        self.assertContains(response, "Editing the NOFO clears them")
        self.assertNotContains(response, "data-metrics-profile")
        self.assertContains(response, "data-metrics-scope-summary")
        self.assertNotContains(response, 'id="readability-metric-goals"')
        panel = BeautifulSoup(response.content, "html.parser").select_one(
            "#readability-metrics-panel"
        )
        self.assertEqual(panel.name, "details")
        self.assertNotIn("open", panel.attrs)
        self.assertEqual(len(panel.select("[data-metric-id]")), 7)
        paragraph_card = panel.select_one(
            '[data-metric-id="sentences_per_paragraph"]'
        ).parent
        self.assertIn("hidden", paragraph_card.attrs)
        self.assertIn("data-optional-metric-card", paragraph_card.attrs)
        self.assertTrue(
            all(
                "bg-base-lightest" in metric.get("class", [])
                for metric in panel.select("[data-metric-id]")
            )
        )
        self.assertFalse(panel.select(".text-base"))
        self.assertTrue(panel.select(".text-base-dark"))

    @override_settings(HHS_NOFO_METRICS_ENABLED=True)
    def test_edit_page_embeds_default_presentation_targets(self):
        response = self.client.get(
            reverse("nofos:nofo_edit", kwargs={"pk": self.nofo.pk})
        )

        self.assertEqual(response.status_code, 200)
        policy_element = BeautifulSoup(response.content, "html.parser").select_one(
            "#readability-metric-goals"
        )
        self.assertIsNotNone(policy_element)
        goals = json.loads(policy_element.string)
        self.assertEqual(goals["word_count"][0]["value"], 13_500)
        self.assertEqual(goals["words_per_sentence"][0]["value"], 15)
        self.assertEqual(goals["sentences_per_paragraph"][0]["value"], 3)
        self.assertEqual(goals["passive_sentence_percentage"][0]["value"], 8)
        self.assertEqual(
            goals["flesch_kincaid_grade_level"],
            [
                {
                    "label": "Target range, depending on NOFO type",
                    "operator": "between",
                    "minimum": 11.5,
                    "maximum": 12.5,
                    "assess": False,
                }
            ],
        )
        self.assertEqual(
            goals["characters_per_word"],
            [
                {
                    "label": "Target range",
                    "operator": "between",
                    "minimum": 5,
                    "maximum": 6,
                }
            ],
        )
        self.assertEqual(goals["flesch_reading_ease"][0]["value"], 39)

    @override_settings(
        HHS_NOFO_METRICS_ENABLED=True,
        HHS_NOFO_METRIC_GOALS={
            "word_count": {
                "label": "Example goal",
                "operator": "at_most",
                "value": 100,
            },
            "flesch_reading_ease": {
                "label": "Example goal",
                "operator": "at_least",
                "value": 50,
            },
            "flesch_kincaid_grade_level": [
                {
                    "label": "Example display range",
                    "operator": "between",
                    "minimum": 10,
                    "maximum": 12,
                    "assess": False,
                },
            ],
        },
    )
    def test_edit_page_embeds_only_configured_presentation_goals(self):
        response = self.client.get(
            reverse("nofos:nofo_edit", kwargs={"pk": self.nofo.pk})
        )

        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, "html.parser")
        policy_element = soup.select_one("#readability-metric-goals")
        self.assertIsNotNone(policy_element)
        self.assertEqual(
            json.loads(policy_element.string),
            {
                "word_count": [
                    {
                        "label": "Example goal",
                        "operator": "at_most",
                        "value": 100,
                    }
                ],
                "flesch_reading_ease": [
                    {
                        "label": "Example goal",
                        "operator": "at_least",
                        "value": 50,
                    }
                ],
                "flesch_kincaid_grade_level": [
                    {
                        "label": "Example display range",
                        "operator": "between",
                        "minimum": 10,
                        "maximum": 12,
                        "assess": False,
                    },
                ],
            },
        )

    def test_goal_configuration_fails_closed_when_invalid(self):
        invalid_configurations = (
            [],
            {"word_count": []},
            {
                "unsupported_metric": {
                    "label": "Example",
                    "operator": "at_most",
                    "value": 1,
                }
            },
            {"word_count": {"label": "Example", "operator": "equals", "value": 1}},
            {"word_count": {"label": "Example", "operator": "at_most", "value": True}},
            {
                "word_count": {
                    "label": "Example",
                    "operator": "between",
                    "minimum": 1,
                }
            },
            {
                "word_count": {
                    "label": "Example",
                    "operator": "between",
                    "minimum": 2,
                    "maximum": 1,
                }
            },
            {
                "word_count": {
                    "label": "Example",
                    "operator": "at_most",
                    "value": 1,
                    "assess": "no",
                }
            },
            {
                "word_count": {
                    "label": "Example",
                    "operator": "at_most",
                    "value": 1,
                    "private_note": "not supported",
                }
            },
        )

        for configuration in invalid_configurations:
            with self.subTest(configuration=configuration):
                with self.assertRaises(ImproperlyConfigured):
                    normalize_readability_metric_goals(configuration)

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
