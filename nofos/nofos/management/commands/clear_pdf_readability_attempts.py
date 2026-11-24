"""One-off reset of readability checker usage records, regardless of age."""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from nofos.models import PdfReadabilityAttempt

SOURCES = ("public", "authenticated", "unknown")


class Command(BaseCommand):
    help = (
        "Delete all readability checker usage records (PdfReadabilityAttempt), "
        "or only one source's records. Dry run unless --confirm is passed. "
        "Saved Word comparisons are never touched."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            choices=SOURCES,
            help="Only clear records with this source. Omit to clear every source.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Actually delete the records. Without it, only the count is shown.",
        )

    def handle(self, *args, **options):
        source = options["source"]
        # call_command(source=...) bypasses argparse choices, so check here too.
        if source is not None and source not in SOURCES:
            raise CommandError(f"--source must be one of: {', '.join(SOURCES)}.")
        rows = PdfReadabilityAttempt.objects.all()
        if source:
            rows = rows.filter(source=source)
        scope = f"{source} " if source else ""

        if not options["confirm"]:
            self.stdout.write(
                f"Dry run: would delete {rows.count()} {scope}readability checker "
                "usage rows. Re-run with --confirm to delete them."
            )
            return

        with transaction.atomic():
            # QuerySet.delete() counts cascades too; this model has none, so
            # the per-model count is the number of usage rows removed.
            _, per_model = rows.delete()
        deleted = per_model.get(PdfReadabilityAttempt._meta.label, 0)
        self.stdout.write(f"Deleted {deleted} {scope}readability checker usage rows.")
