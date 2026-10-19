from django.core.management.base import BaseCommand, CommandError

from nofos.history_index import backfill_history_index


class Command(BaseCommand):
    help = "Populate missing document audit index rows after bulk audit imports."

    def add_arguments(self, parser):
        parser.add_argument("--database", default="default")
        parser.add_argument("--chunk-size", type=int, default=100)

    def handle(self, *args, **options):
        size = options["chunk_size"]
        if not 1 <= size <= 1000:
            raise CommandError("--chunk-size must be between 1 and 1000")
        result = backfill_history_index(using=options["database"], chunk_size=size)
        self.stdout.write(
            f"Document audit index: {result['indexed']} resolved, {result['unresolved']} unresolved ownership."
        )
