from django.db import connection
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class HandoffResultMigrationTests(TransactionTestCase):
    """Exercise the real 0143-to-0144 migration, including legacy tombstones."""

    def test_preserves_live_shared_and_deleted_links(self):
        executor = MigrationExecutor(connection)
        old = [("nofos", "0143_externalsourcehandoff")]
        new = [("nofos", "0144_remove_externalsourcehandoff_linked_nofo_uuid_and_more")]
        executor.migrate(old)
        try:
            old_apps = executor.loader.project_state(old).apps
            Receipt = old_apps.get_model("nofos", "ExternalSourceHandoff")
            Nofo = old_apps.get_model("nofos", "Nofo")
            shared = Nofo.objects.create(
                title="Shared synthetic", opdiv="HRSA", group="hrsa"
            )
            deleted = Nofo.objects.create(
                title="Deleted synthetic", opdiv="HRSA", group="hrsa"
            )
            linked_receipts = []
            for number in range(2):
                linked_receipts.append(
                    Receipt.objects.create(
                        source_system="synthetic",
                        source_record_id=f"shared-{number}",
                        source_version="opaque",
                        group="hrsa",
                        nofo_id=shared.pk,
                        linked_nofo_uuid=shared.pk,
                    )
                )
            deleted_receipt = Receipt.objects.create(
                source_system="synthetic",
                source_record_id="deleted",
                source_version="opaque",
                group="hrsa",
                nofo_id=deleted.pk,
                linked_nofo_uuid=deleted.pk,
            )
            deleted_uuid = deleted.pk
            deleted.delete()
            executor = MigrationExecutor(connection)
            executor.migrate(new)
            new_apps = executor.loader.project_state(new).apps
            Result = new_apps.get_model("nofos", "ExternalSourceHandoffResult")
            Current = new_apps.get_model("nofos", "ExternalSourceHandoffCurrent")
            for receipt in linked_receipts:
                result = Result.objects.get(handoff_id=receipt.pk)
                self.assertEqual(result.nofo_id, shared.pk)
                self.assertEqual(result.linked_nofo_uuid, shared.pk)
                self.assertEqual(
                    Current.objects.get(handoff_id=receipt.pk).result_id, result.pk
                )
            result = Result.objects.get(handoff_id=deleted_receipt.pk)
            self.assertIsNone(result.nofo_id)
            self.assertEqual(result.linked_nofo_uuid, deleted_uuid)
            self.assertEqual(
                Current.objects.get(handoff_id=deleted_receipt.pk).result_id, result.pk
            )
            with self.assertRaises(IrreversibleError):
                MigrationExecutor(connection).migrate(old)
            self.assertEqual(Result.objects.count(), 3)
        finally:
            MigrationExecutor(connection).migrate(new)
