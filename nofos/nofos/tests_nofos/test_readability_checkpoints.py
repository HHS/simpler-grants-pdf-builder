from copy import deepcopy
from unittest.mock import patch

from constance.test import override_config
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from users.models import BloomUser

from nofos.models import Nofo, NofoReadabilityCheckpoint, NofoReadabilityScore
from nofos.readability import (
    INPUT_CONTRACT_VERSION,
    PROFILE_REFERENCE,
    ReadabilityRevisionChanged,
    record_readability_snapshot,
    save_readability_checkpoint,
)
from nofos.readability_history import (
    checkpoint_queryset,
    checkpoint_rows,
    project_checkpoint,
)
from nofos.tests_nofos.test_readability_metrics import build_payload


@override_config(HHS_NOFO_METRICS_ENABLED=True)
class ReadabilityCheckpointTests(TestCase):
    def setUp(self):
        self.version_patch = patch(
            "nofos.readability.get_metrics_package_version", return_value="0.5.2"
        )
        self.version_patch.start()
        self.addCleanup(self.version_patch.stop)
        self.history_version_patch = patch(
            "nofos.readability_history.get_metrics_package_version",
            return_value="0.5.2",
        )
        self.history_version_patch.start()
        self.addCleanup(self.history_version_patch.stop)
        self.analyze_patch = patch(
            "nofos.readability.analyze_nofo_readability", return_value=build_payload()
        )
        self.analyze = self.analyze_patch.start()
        self.addCleanup(self.analyze_patch.stop)
        self.user = BloomUser.objects.create_user(
            email="checkpoints@example.com",
            password="test",
            group="hrsa",
            force_password_reset=False,
        )
        self.nofo = Nofo.objects.create(
            title="Synthetic checkpoint", group="hrsa", status="review", opdiv="HRSA"
        )
        self.client.force_login(self.user)
        self.url = reverse(
            "nofos:nofo_readability_metrics_save", kwargs={"pk": self.nofo.pk}
        )

    def save(self):
        return save_readability_checkpoint(self.nofo, self.user)

    def test_calculation_is_not_a_checkpoint(self):
        record_readability_snapshot(self.nofo, self.user)
        self.assertEqual(NofoReadabilityScore.objects.count(), 1)
        self.assertEqual(checkpoint_rows(self.nofo), [])

    def test_save_reuses_result_records_status_without_touching_nofo(self):
        _, score = record_readability_snapshot(self.nofo, self.user)
        original = deepcopy(score.result)
        revision = self.nofo.updated
        _, checkpoint, created = self.save()
        self.nofo.refresh_from_db()
        score.refresh_from_db()
        self.assertTrue(created)
        self.assertEqual(checkpoint.score_id, score.pk)
        self.assertEqual(checkpoint.saved_by, self.user)
        self.assertEqual(checkpoint.nofo_status_at_save, "review")
        self.assertEqual(score.result, original)
        self.assertEqual(self.nofo.updated, revision)
        self.analyze.assert_called_once()

    def test_duplicate_preserves_first_save_user_and_time_and_status(self):
        _, first, _ = self.save()
        self.nofo.status = "doge"
        Nofo.objects.filter(pk=self.nofo.pk).update(status="doge")
        _, repeated, created = self.save()
        self.assertFalse(created)
        self.assertEqual(repeated.pk, first.pk)
        self.assertEqual(repeated.saved_at, first.saved_at)
        self.assertEqual(repeated.nofo_status_at_save, "review")
        self.assertEqual(NofoReadabilityCheckpoint.objects.count(), 1)

    def test_unique_score_constraint_is_database_enforced(self):
        _, checkpoint, _ = self.save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            NofoReadabilityCheckpoint.objects.create(
                score=checkpoint.score, nofo_status_at_save="draft"
            )

    def test_save_response_uses_previous_id_when_timestamps_tie(self):
        _, first, _ = self.save()
        Nofo.objects.filter(pk=self.nofo.pk).update(updated=timezone.now())
        self.nofo.refresh_from_db()
        self.analyze.return_value = build_payload()
        self.analyze.return_value["metrics"]["word_count"]["value"] = 17
        _, second, _ = self.save()
        NofoReadabilityCheckpoint.objects.filter(pk=second.pk).update(
            saved_at=first.saved_at
        )
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["already_saved"])
        self.assertNotEqual(
            response.json()["checkpoint"]["change_summary"]["label"],
            "First snapshot",
        )

    def test_save_after_edit_remeasures_server_content(self):
        record_readability_snapshot(self.nofo, self.user)
        Nofo.objects.filter(pk=self.nofo.pk).update(updated=timezone.now())
        self.analyze.return_value = build_payload()
        self.analyze.return_value["metrics"]["word_count"]["value"] = 17
        response = self.client.post(self.url, {"word_count": 999})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["result"]["metrics"]["word_count"]["value"], 17
        )
        self.assertEqual(self.analyze.call_count, 2)

    def test_midrun_revision_change_creates_no_checkpoint(self):
        def edit_during_analysis(nofo):
            Nofo.objects.filter(pk=nofo.pk).update(updated=timezone.now())
            return build_payload()

        self.analyze.side_effect = edit_during_analysis
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "readability_revision_changed")
        self.assertFalse(NofoReadabilityCheckpoint.objects.exists())

    def test_revision_change_after_snapshot_rechecked(self):
        payload, score = record_readability_snapshot(self.nofo, self.user)
        Nofo.objects.filter(pk=self.nofo.pk).update(updated=timezone.now())
        with patch(
            "nofos.readability.record_readability_snapshot",
            return_value=(payload, score),
        ):
            with self.assertRaises(ReadabilityRevisionChanged):
                self.save()
        self.assertFalse(NofoReadabilityCheckpoint.objects.exists())

    def test_group_change_after_snapshot_rechecked(self):
        payload, score = record_readability_snapshot(self.nofo, self.user)
        Nofo.objects.filter(pk=self.nofo.pk).update(group="cdc")
        with patch(
            "nofos.readability.record_readability_snapshot",
            return_value=(payload, score),
        ):
            with self.assertRaises(PermissionDenied):
                self.save()
        self.assertFalse(NofoReadabilityCheckpoint.objects.exists())

    def test_partial_record_can_be_saved_and_zero_is_not_unavailable(self):
        self.analyze.return_value = build_payload(
            {"flesch_kincaid_grade_level": "unavailable"}
        )
        self.analyze.return_value["metrics"]["word_count"]["value"] = 0
        self.save()
        row = checkpoint_rows(self.nofo)[0]
        self.assertFalse(row["is_complete"])
        self.assertEqual(row["metrics"][0]["display"], "0")
        self.assertEqual(row["metrics"][3]["display"], "Unavailable")

    def test_derived_paragraph_value_and_metric_change_text(self):
        self.analyze.return_value["metrics"]["words_per_sentence"]["components"] = {
            "sentences_per_paragraph": 3.25
        }
        self.save()
        Nofo.objects.filter(pk=self.nofo.pk).update(updated=timezone.now())
        self.nofo.refresh_from_db()
        self.analyze.return_value["metrics"]["word_count"]["value"] = 25
        self.save()
        rows = checkpoint_rows(self.nofo)
        self.assertEqual(rows[0]["metrics"][0]["change"], "Lower than previous")
        self.assertEqual(rows[0]["metrics"][2]["value"], 3.25)
        self.assertEqual(rows[0]["metrics"][2]["display"], "3.2")
        self.assertEqual(rows[0]["metrics"][2]["change"], "")

    def test_metrics_viewer_outside_group_cannot_save(self):
        from django.contrib.auth.models import Permission

        self.user.group = "cdc"
        self.user.save()
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_builder_metrics")
        )
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertFalse(NofoReadabilityCheckpoint.objects.exists())

    def test_deleted_user_label_and_archived_history_retained(self):
        self.save()
        self.user.delete()
        Nofo.objects.filter(pk=self.nofo.pk).update(archived=timezone.now())
        self.assertEqual(checkpoint_rows(self.nofo)[0]["saved_by"], "Deleted user")
        self.nofo.delete()
        self.assertFalse(NofoReadabilityCheckpoint.objects.exists())

    @override_config(HHS_NOFO_METRICS_ENABLED=False)
    def test_disabled_save_is_503_and_keeps_data(self):
        self.save()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(NofoReadabilityCheckpoint.objects.count(), 1)

    def test_get_not_allowed_and_save_no_store(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        response = self.client.post(self.url)
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertFalse(response.json()["already_saved"])
        self.assertTrue(self.client.post(self.url).json()["already_saved"])

    def test_other_group_cannot_save(self):
        self.user.group = "cdc"
        self.user.save()
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertFalse(NofoReadabilityScore.objects.exists())

    def test_csrf_required(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.url).status_code, 403)

    def test_profile_change_not_current(self):
        _, checkpoint, _ = self.save()
        NofoReadabilityScore.objects.filter(pk=checkpoint.score_id).update(
            profile_reference="old"
        )
        checkpoint.score.refresh_from_db()
        self.assertFalse(checkpoint.score.is_current)
        self.assertFalse(checkpoint_rows(self.nofo)[0]["is_current"])

    def test_projection_fetches_only_metric_json_and_bounded_predecessor(self):
        self.save()
        Nofo.objects.filter(pk=self.nofo.pk).update(updated=timezone.now())
        self.nofo.refresh_from_db()
        self.save()
        with self.assertNumQueries(1):
            rows = checkpoint_rows(self.nofo, limit=1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["change_summary"]["label"], "No change")
        row = checkpoint_queryset().first()
        self.assertNotIn("result", row)


class ReadabilityHistoryComparisonTests(TestCase):
    def row(self, **metrics):
        row = {
            name: "same"
            for name in (
                "profile_reference",
                "package_version",
                "input_contract_version",
                "schema_version",
                "result_basis",
            )
        }
        for metric_id, value in metrics.items():
            row[metric_id + "_status"] = "calculated"
            row[metric_id + "_value"] = value
        return row

    def compare(self, newer, older, goals=None):
        from nofos.readability import normalize_readability_metric_goals
        from nofos.readability_history import change_summary

        return change_summary(
            newer,
            older,
            (
                normalize_readability_metric_goals(settings.HHS_NOFO_METRIC_GOALS)
                if goals is None
                else goals
            ),
        )

    def test_lower_better_and_category_grade_lower_better(self):
        old = self.row(
            word_count=100, flesch_reading_ease=40, flesch_kincaid_grade_level=12
        )
        new = self.row(
            word_count=90, flesch_reading_ease=42, flesch_kincaid_grade_level=11
        )
        self.assertEqual(self.compare(new, old)["improved"], 2)

    def test_mixed_and_no_change(self):
        old = self.row(word_count=100, passive_sentence_percentage=4)
        new = self.row(word_count=90, passive_sentence_percentage=5)
        self.assertEqual(
            self.compare(new, old)["label"],
            "Improved on 1 metric · Worse on 1 metric",
        )
        self.assertEqual(self.compare(old, old)["label"], "No change")

    def test_no_values_or_targets_not_claimed_as_no_change(self):
        row = self.row(word_count=100)
        self.assertEqual(self.compare(row, row, {})["label"], "No comparable metrics")
        for bad in [True, float("nan"), float("inf"), "42", None]:
            self.assertEqual(
                self.compare(self.row(word_count=bad), row)["label"],
                "No comparable metrics",
            )

    def test_every_contract_field_blocks_comparison(self):
        old = self.row(word_count=100)
        for field in (
            "profile_reference",
            "package_version",
            "input_contract_version",
            "schema_version",
            "result_basis",
        ):
            new = self.row(word_count=90)
            new[field] = "changed"
            self.assertEqual(
                self.compare(new, old)["label"], "Measurement updated: not compared"
            )
        self.assertEqual(self.compare(old, None)["label"], "First snapshot")

    def test_hidden_reading_ease_does_not_affect_summary(self):
        old = self.row(word_count=100, flesch_reading_ease=40)
        new = self.row(word_count=100, flesch_reading_ease=80)
        self.assertEqual(self.compare(new, old)["label"], "No change")
