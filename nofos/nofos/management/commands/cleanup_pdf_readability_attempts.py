"""Manually invocable cleanup; scheduling requires the privacy retention decision."""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from nofos.models import PdfReadabilityAttempt
from nofos.pdf_readability_metrics import retention_days


class Command(BaseCommand):
    help = (
        "Delete pilot outcomes older than the explicitly configured retention window."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--source", choices=("public", "authenticated", "unknown"), default="public"
        )

    def handle(self, *args, **options):
        source = options["source"]
        days = retention_days(source)
        if type(days) is not int or days <= 0:
            raise CommandError(
                "Configure an approved positive retention window for this source first."
            )
        rows = PdfReadabilityAttempt.objects.filter(
            source__in=["public", "unknown"] if source == "public" else [source],
            created_at__lt=timezone.now() - timedelta(days=days),
        )
        count = rows.count()
        if not options["dry_run"]:
            rows.delete()
        self.stdout.write(
            f"{'Would delete' if options['dry_run'] else 'Deleted'} {count} pilot outcome rows."
        )
