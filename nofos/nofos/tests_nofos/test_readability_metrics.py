import json
from importlib.util import find_spec
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup
from constance.test import override_config
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from users.models import BloomUser

from nofos.models import Nofo, NofoReadabilityScore, Section, Subsection
from nofos.readability import (
    GOAL_METRIC_IDS,
    PROFILE_REFERENCE,
    ReadabilityMetricsAnalysisError,
    ReadabilityMetricsUnavailable,
    analyze_nofo_readability,
    normalize_readability_metric_goals,
    record_readability_snapshot,
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

    @override_config(HHS_NOFO_METRICS_ENABLED=True)
    @override_settings(HHS_NOFO_METRIC_GOALS={})
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
        self.assertEqual(len(panel.select("[data-metric-id]")), 6)
        self.assertIsNone(panel.select_one('[data-metric-id="characters_per_word"]'))
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

    @override_config(HHS_NOFO_METRICS_ENABLED=True)
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
                    "operator": "at_most_by_category",
                    "minimum": 11.5,
                    "maximum": 12.5,
                }
            ],
        )
        self.assertNotIn("characters_per_word", goals)
        self.assertEqual(goals["flesch_reading_ease"][0]["value"], 39)

    @override_config(HHS_NOFO_METRICS_ENABLED=True)
    @override_settings(
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
                    "label": "Example category-dependent target",
                    "operator": "at_most_by_category",
                    "minimum": 10,
                    "maximum": 12,
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
                        "label": "Example category-dependent target",
                        "operator": "at_most_by_category",
                        "minimum": 10,
                        "maximum": 12,
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
                    "operator": "at_most_by_category",
                    "minimum": 1,
                }
            },
            {
                "word_count": {
                    "label": "Example",
                    "operator": "at_most_by_category",
                    "minimum": 2,
                    "maximum": 1,
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

    @override_config(HHS_NOFO_METRICS_ENABLED=False)
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

    @override_config(HHS_NOFO_METRICS_ENABLED=False)
    @patch("nofos.readability.analyze_nofo_readability")
    def test_disabled_endpoint_fails_closed(self, analyze):
        response = self.client.get(self.metrics_url)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "readability_metrics_disabled")
        analyze.assert_not_called()

    @override_config(HHS_NOFO_METRICS_ENABLED=True)
    @patch("nofos.readability.analyze_nofo_readability")
    def test_endpoint_returns_the_complete_package_result_verbatim(self, analyze):
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

    @override_config(HHS_NOFO_METRICS_ENABLED=True)
    @patch("nofos.readability.analyze_nofo_readability")
    def test_missing_package_is_reported_as_unavailable(self, analyze):
        analyze.side_effect = ReadabilityMetricsUnavailable("Package is missing.")

        response = self.client.get(self.metrics_url)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "readability_metrics_unavailable")

    @override_config(HHS_NOFO_METRICS_ENABLED=True)
    @patch("nofos.readability.analyze_nofo_readability")
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

    @override_config(HHS_NOFO_METRICS_ENABLED=True)
    @patch("nofos.readability.analyze_nofo_readability", new=Mock())
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


# The metric set hhs-nofo-metrics v0.5.2 actually returns. Deliberately not
# GOAL_METRIC_IDS: that constant is the set of metrics Builder allows goals to
# be configured for, and the two sets differ. The package returns
# characters_per_word and does not return sentences_per_paragraph.
PACKAGE_METRIC_IDS = (
    "word_count",
    "words_per_sentence",
    "characters_per_word",
    "flesch_reading_ease",
    "flesch_kincaid_grade_level",
    "passive_sentence_percentage",
)


def build_payload(statuses=None, metric_ids=PACKAGE_METRIC_IDS):
    """A package-shaped payload, calculated for every returned metric by default."""

    statuses = statuses or {}
    return {
        "schema_version": "1.1.0",
        "result_basis": "structured_estimate",
        "source": {"document_id": "doc", "revision": "rev"},
        "coverage": {"segments_total": 4, "unknown_role_count": 0},
        "metrics": {
            metric_id: (
                {"status": "unavailable", "reason": "Not enough text."}
                if statuses.get(metric_id) == "unavailable"
                else {"status": "calculated", "value": 42}
            )
            for metric_id in metric_ids
        },
    }


@override_config(HHS_NOFO_METRICS_ENABLED=True)
@patch("nofos.readability.get_metrics_package_version", return_value="0.5.2")
class NofoReadabilityScorePersistenceTests(TestCase):
    """Durable, append-only snapshots for calculated readability metrics."""

    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="snapshots@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.nofo = Nofo.objects.create(
            title="Snapshot test NOFO",
            short_name="snapshot-test",
            number="TEST-SNAP-001",
            opdiv="TEST",
            group="bloom",
            status="draft",
        )
        self.section = Section.objects.create(
            nofo=self.nofo,
            name="Step 1: Review the Opportunity",
            html_id="step-1-review-the-opportunity",
            order=1,
        )
        self.subsection = Subsection.objects.create(
            section=self.section,
            name="Summary",
            tag="h4",
            body="Applicants describe their proposed work.",
            order=1,
        )
        self.nofo.refresh_from_db()
        self.client = Client()
        self.client.force_login(self.user)
        self.metrics_url = reverse(
            "nofos:nofo_readability_metrics", kwargs={"pk": self.nofo.pk}
        )

    def edit_the_nofo_body(self):
        """Edit a subsection so the NOFO moves to a new content revision."""

        self.subsection.body = "Applicants describe the work they propose to do."
        self.subsection.save()
        self.nofo.refresh_from_db()

    # -- creating snapshots -------------------------------------------------

    @patch("nofos.readability.analyze_nofo_readability")
    def test_successful_calculation_creates_a_snapshot_for_the_nofo(
        self, analyze, _version
    ):
        analyze.return_value = build_payload()

        response = self.client.get(self.metrics_url)

        self.assertEqual(response.status_code, 200)
        snapshot = NofoReadabilityScore.objects.get()
        self.assertEqual(snapshot.nofo, self.nofo)
        self.assertEqual(snapshot.created_by, self.user)
        self.assertEqual(snapshot.nofo_revision, self.nofo.updated)
        self.assertEqual(snapshot.result, analyze.return_value)
        self.assertTrue(snapshot.is_complete)
        self.assertTrue(snapshot.is_current)

    @patch("nofos.readability.analyze_nofo_readability")
    def test_snapshot_records_the_measurement_contract_and_goals(
        self, analyze, _version
    ):
        analyze.return_value = build_payload()

        self.client.get(self.metrics_url)

        snapshot = NofoReadabilityScore.objects.get()
        self.assertEqual(snapshot.profile_reference, PROFILE_REFERENCE)
        self.assertEqual(snapshot.package_version, "0.5.2")
        self.assertEqual(snapshot.schema_version, "1.1.0")
        self.assertEqual(snapshot.result_basis, "structured_estimate")
        self.assertEqual(
            snapshot.goals,
            normalize_readability_metric_goals(settings.HHS_NOFO_METRIC_GOALS),
        )

    # -- repeated calculations ----------------------------------------------

    @patch("nofos.readability.analyze_nofo_readability")
    def test_recalculating_the_same_revision_reuses_the_stored_snapshot(
        self, analyze, _version
    ):
        analyze.return_value = build_payload()

        first = self.client.get(self.metrics_url)
        second = self.client.get(self.metrics_url)

        self.assertEqual(first.json(), second.json())
        self.assertEqual(NofoReadabilityScore.objects.count(), 1)
        # The package is the expensive part: an unchanged revision must not re-run it.
        analyze.assert_called_once()

    @patch("nofos.readability.analyze_nofo_readability")
    def test_editing_the_nofo_adds_a_snapshot_without_destroying_the_earlier_one(
        self, analyze, _version
    ):
        analyze.return_value = build_payload()
        self.client.get(self.metrics_url)
        first_revision = self.nofo.updated

        self.edit_the_nofo_body()
        self.assertNotEqual(self.nofo.updated, first_revision)
        self.client.get(self.metrics_url)

        self.assertEqual(NofoReadabilityScore.objects.count(), 2)
        self.assertEqual(analyze.call_count, 2)
        revisions = set(
            NofoReadabilityScore.objects.values_list("nofo_revision", flat=True)
        )
        self.assertEqual(revisions, {first_revision, self.nofo.updated})

    @patch("nofos.readability.analyze_nofo_readability")
    def test_a_new_package_version_measures_the_same_revision_again(
        self, analyze, version
    ):
        analyze.return_value = build_payload()
        self.client.get(self.metrics_url)

        # Same content, different measurement contract: not the same measurement.
        version.return_value = "0.6.0"
        self.client.get(self.metrics_url)

        self.assertEqual(NofoReadabilityScore.objects.count(), 2)
        self.assertEqual(
            set(NofoReadabilityScore.objects.values_list("package_version", flat=True)),
            {"0.5.2", "0.6.0"},
        )

    # -- failed and incomplete calculations ----------------------------------

    @patch("nofos.readability.analyze_nofo_readability")
    def test_unavailable_package_writes_no_snapshot(self, analyze, _version):
        analyze.side_effect = ReadabilityMetricsUnavailable("Package is missing.")

        response = self.client.get(self.metrics_url)

        self.assertEqual(response.status_code, 503)
        self.assertFalse(NofoReadabilityScore.objects.exists())

    @patch("nofos.readability.analyze_nofo_readability")
    def test_analysis_error_leaves_the_last_successful_snapshot_in_place(
        self, analyze, _version
    ):
        analyze.return_value = build_payload()
        self.client.get(self.metrics_url)
        successful = NofoReadabilityScore.objects.get()

        self.edit_the_nofo_body()
        analyze.side_effect = ReadabilityMetricsAnalysisError(
            {"code": "analysis_error", "message": "Could not classify source."}
        )
        response = self.client.get(self.metrics_url)

        self.assertEqual(response.status_code, 422)
        self.assertEqual(NofoReadabilityScore.objects.count(), 1)
        self.assertEqual(NofoReadabilityScore.objects.latest_for(self.nofo), successful)

    @patch("nofos.readability.analyze_nofo_readability")
    def test_incomplete_metrics_are_stored_but_do_not_become_the_latest(
        self, analyze, _version
    ):
        analyze.return_value = build_payload()
        self.client.get(self.metrics_url)
        complete = NofoReadabilityScore.objects.get()

        self.edit_the_nofo_body()
        analyze.return_value = build_payload(
            statuses={"passive_sentence_percentage": "unavailable"}
        )
        response = self.client.get(self.metrics_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(NofoReadabilityScore.objects.count(), 2)
        incomplete = NofoReadabilityScore.objects.exclude(pk=complete.pk).get()
        self.assertFalse(incomplete.is_complete)
        # The newest snapshot is retained, but the last complete one still stands.
        self.assertEqual(NofoReadabilityScore.objects.latest_for(self.nofo), complete)

    @patch("nofos.readability.analyze_nofo_readability")
    def test_a_metric_builder_configures_goals_for_but_the_package_omits_is_not_missing_data(
        self, analyze, _version
    ):
        """
        Completeness follows the package's own metric set.

        GOAL_METRIC_IDS lists the metrics Builder allows goals to be configured
        for; the package returns a different set. A result where every returned
        metric was calculated is complete even though sentences_per_paragraph
        never appears in it.
        """
        analyze.return_value = build_payload()
        self.assertNotIn("sentences_per_paragraph", analyze.return_value["metrics"])
        self.assertIn("sentences_per_paragraph", GOAL_METRIC_IDS)

        self.client.get(self.metrics_url)

        snapshot = NofoReadabilityScore.objects.get()
        self.assertTrue(snapshot.is_complete)
        self.assertEqual(NofoReadabilityScore.objects.latest_for(self.nofo), snapshot)

    # -- retrieval and permissions -------------------------------------------

    @patch("nofos.readability.analyze_nofo_readability")
    def test_latest_for_returns_the_most_recent_complete_snapshot(
        self, analyze, _version
    ):
        analyze.return_value = build_payload()
        self.client.get(self.metrics_url)

        self.edit_the_nofo_body()
        self.client.get(self.metrics_url)

        latest = NofoReadabilityScore.objects.latest_for(self.nofo)
        self.assertEqual(latest.nofo_revision, self.nofo.updated)
        self.assertTrue(latest.is_current)

    @patch("nofos.readability.analyze_nofo_readability")
    def test_current_for_misses_once_the_nofo_is_edited(self, analyze, _version):
        analyze.return_value = build_payload()
        self.client.get(self.metrics_url)

        self.assertIsNotNone(
            NofoReadabilityScore.objects.current_for(
                self.nofo, PROFILE_REFERENCE, "0.5.2"
            )
        )

        self.edit_the_nofo_body()
        self.assertIsNone(
            NofoReadabilityScore.objects.current_for(
                self.nofo, PROFILE_REFERENCE, "0.5.2"
            )
        )

    @patch("nofos.readability.analyze_nofo_readability")
    def test_a_user_outside_the_group_cannot_calculate_or_store(
        self, analyze, _version
    ):
        analyze.return_value = build_payload()
        other_user = BloomUser.objects.create_user(
            email="other-group-snapshots@example.com",
            password="testpass123",
            group="hrsa",
            force_password_reset=False,
        )
        self.client.force_login(other_user)

        response = self.client.get(self.metrics_url)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(NofoReadabilityScore.objects.exists())
        analyze.assert_not_called()

    # -- retention ------------------------------------------------------------

    @patch("nofos.readability.analyze_nofo_readability")
    def test_archiving_a_nofo_keeps_its_snapshots(self, analyze, _version):
        analyze.return_value = build_payload()
        self.client.get(self.metrics_url)

        Nofo.objects.filter(pk=self.nofo.pk).update(archived=timezone.now().date())

        self.assertEqual(NofoReadabilityScore.objects.count(), 1)

    @patch("nofos.readability.analyze_nofo_readability")
    def test_deleting_a_nofo_deletes_its_snapshots(self, analyze, _version):
        analyze.return_value = build_payload()
        self.client.get(self.metrics_url)

        self.nofo.delete()

        self.assertFalse(NofoReadabilityScore.objects.exists())
