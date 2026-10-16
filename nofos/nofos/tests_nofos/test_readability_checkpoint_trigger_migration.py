from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ReadabilityCheckpointTriggerMigrationTests(TransactionTestCase):
    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([("nofos", target)])
        return executor.loader.project_state([("nofos", target)]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_existing_checkpoint_and_measurement_survive_with_original_provenance(self):
        apps = self.migrate("0151_introductory_page_family")
        Nofo = apps.get_model("nofos", "Nofo")
        Score = apps.get_model("nofos", "NofoReadabilityScore")
        Checkpoint = apps.get_model("nofos", "NofoReadabilityCheckpoint")
        nofo = Nofo.objects.create(title="Synthetic migration")
        score = Score.objects.create(
            nofo=nofo,
            nofo_revision=nofo.updated,
            profile_reference="synthetic",
            package_version="0.5.4",
            result={"synthetic": True},
        )
        imported = Checkpoint.objects.create(
            score=score, trigger="import", nofo_status_at_save="draft"
        )

        apps = self.migrate("0152_readability_checkpoint_per_trigger")
        Checkpoint = apps.get_model("nofos", "NofoReadabilityCheckpoint")
        Score = apps.get_model("nofos", "NofoReadabilityScore")
        preserved = Checkpoint.objects.get(pk=imported.pk)
        self.assertEqual(preserved.saved_at, imported.saved_at)
        self.assertEqual(preserved.trigger, "import")
        self.assertEqual(preserved.nofo_status_at_save, "draft")
        self.assertEqual(Score.objects.get(pk=score.pk).result, {"synthetic": True})
        Checkpoint.objects.create(
            score_id=score.pk, trigger="download", nofo_status_at_save="draft"
        )
        self.assertEqual(Checkpoint.objects.count(), 2)
        self.assertEqual(Score.objects.count(), 1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Checkpoint.objects.create(
                score_id=score.pk, trigger="download", nofo_status_at_save="draft"
            )
