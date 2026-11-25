"""Optional cleanup for an explicit retention policy; unused by default."""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from nofos.models import WordDownloadAttempt
from nofos.word_download_metrics import retention_days


class Command(BaseCommand):
    help = "Delete Word download outcomes older than the configured retention window."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        days = retention_days()
        if type(days) is not int or days <= 0:
            raise CommandError(
                "Set WORD_DOWNLOAD_ATTEMPT_RETENTION_DAYS to a positive number of days first."
            )
        rows = WordDownloadAttempt.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=days)
        )
        count = rows.count()
        if not options["dry_run"]:
            rows.delete()
        self.stdout.write(
            f"{'Would delete' if options['dry_run'] else 'Deleted'} {count} Word download outcome rows."
        )
