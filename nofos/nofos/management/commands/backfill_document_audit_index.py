from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from easyaudit.models import CRUDEvent

from nofos.history_index import ROOTS, SECTIONS, SUBSECTIONS, backfill_history_index
from nofos.models import DocumentAuditEvent


class Command(BaseCommand):
    help = "Populate missing document audit index rows after rollout or bulk imports."

    def add_arguments(self, parser):
        parser.add_argument("--database", default="default")
        parser.add_argument("--chunk-size", type=int, default=100)
        parser.add_argument(
            "--check",
            action="store_true",
            help="Read-only completeness check; fail if any relevant event is not indexed.",
        )

    def handle(self, *args, **options):
        size = options["chunk_size"]
        if not 1 <= size <= 1000:
            raise CommandError("--chunk-size must be between 1 and 1000")
        if options["check"]:
            relevant = Q()
            for app_label, model in sorted(ROOTS | SECTIONS | SUBSECTIONS):
                relevant |= Q(
                    content_type__app_label=app_label, content_type__model=model
                )
            alias = options["database"]
            missing = (
                CRUDEvent.objects.using(alias)
                .filter(relevant)
                .exclude(
                    pk__in=DocumentAuditEvent.objects.using(alias).values("event_id")
                )
                .count()
            )
            if missing:
                raise CommandError(
                    f"Document audit index incomplete: {missing} events missing. Keep indexed reads disabled."
                )
            self.stdout.write("Document audit index complete: 0 events missing.")
            return
        result = backfill_history_index(using=options["database"], chunk_size=size)
        self.stdout.write(
            f"Document audit index: {result['indexed']} resolved, {result['unresolved']} unresolved ownership."
        )
