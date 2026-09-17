from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ReadabilityInputContractMigrationTests(TransactionTestCase):
    migrate_from = ("nofos", "0141_import_attempt_indexes")
    migrate_to = ("nofos", "0142_readability_input_contract")

    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        return executor.loader.project_state([target]).apps

    def tearDown(self):
        self.migrate(self.migrate_to)
        super().tearDown()

    def test_legacy_rows_survive_migration_and_new_contract_has_separate_identity(self):
        apps = self.migrate(self.migrate_from)
        Nofo = apps.get_model("nofos", "Nofo")
        Score = apps.get_model("nofos", "NofoReadabilityScore")
        nofo = Nofo.objects.create(title="Migration test", short_name="migration-test")
        result = {"metrics": {"word_count": {"value": 100, "status": "calculated"}}}
        legacy = Score.objects.create(
            nofo=nofo,
            nofo_revision=nofo.updated,
            profile_reference="hhs-nofo-fy27-html@0.4.0",
            package_version="0.5.2",
            result=result,
            is_complete=True,
        )

        apps = self.migrate(self.migrate_to)
        Score = apps.get_model("nofos", "NofoReadabilityScore")
        migrated = Score.objects.get(pk=legacy.pk)
        self.assertEqual(migrated.input_contract_version, "word-export-v1")
        self.assertEqual(migrated.result, result)

        # A legacy-only database can roll back without losing its snapshot.
        apps = self.migrate(self.migrate_from)
        Score = apps.get_model("nofos", "NofoReadabilityScore")
        self.assertEqual(Score.objects.get(pk=legacy.pk).result, result)
        apps = self.migrate(self.migrate_to)
        Score = apps.get_model("nofos", "NofoReadabilityScore")

        identity = dict(
            nofo_id=nofo.pk,
            nofo_revision=nofo.updated,
            profile_reference="hhs-nofo-fy27-html@0.4.0",
            package_version="0.5.2",
            input_contract_version="word-export-v2",
        )
        Score.objects.create(**identity, result=result, is_complete=True)
        self.assertEqual(Score.objects.count(), 2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Score.objects.create(**identity, result=result, is_complete=True)
