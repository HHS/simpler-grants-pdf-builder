from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class ClearPdfReadabilityAttemptsMigrationTests(TransactionTestCase):
    """Exercise the real 0167-to-0168 one-time reset (#1427)."""

    old = [("nofos", "0167_add_oash_group_and_theme")]
    new = [("nofos", "0168_clear_pdf_readability_attempts")]

    def test_clears_every_attempt_and_keeps_word_comparisons(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.old)
        try:
            old_apps = executor.loader.project_state(self.old).apps
            Attempt = old_apps.get_model("nofos", "PdfReadabilityAttempt")
            Comparison = old_apps.get_model("nofos", "WordComparison")
            for source in ("public", "authenticated", "unknown"):
                Attempt.objects.create(
                    outcome="success", http_status=200, duration_ms=1, source=source
                )
            comparison = Comparison.objects.create(
                filename="Synthetic.docx",
                fingerprint="a" * 64,
                analyzed_at=timezone.now(),
                version="synthetic-1",
                checker={},
                passive=1,
                word_passive=2,
            )

            executor = MigrationExecutor(connection)
            executor.migrate(self.new)
            new_apps = executor.loader.project_state(self.new).apps
            self.assertFalse(
                new_apps.get_model("nofos", "PdfReadabilityAttempt").objects.exists()
            )
            self.assertEqual(
                list(
                    new_apps.get_model("nofos", "WordComparison").objects.values_list(
                        "pk", flat=True
                    )
                ),
                [comparison.pk],
            )

            # Reversible as a no-op, so rolling back the deploy isn't blocked.
            MigrationExecutor(connection).migrate(self.old)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())

    def test_runs_cleanly_on_an_empty_table(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.old)
        try:
            executor = MigrationExecutor(connection)
            executor.migrate(self.new)
            Attempt = executor.loader.project_state(self.new).apps.get_model(
                "nofos", "PdfReadabilityAttempt"
            )
            self.assertFalse(Attempt.objects.exists())
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
