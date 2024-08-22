import json

from django.core.management.base import BaseCommand
from easyaudit.models import CRUDEvent
from nofos.models import Nofo, Subsection


class Command(BaseCommand):
    help = "Counts updates for a specific NOFO"

    def add_arguments(self, parser):
        parser.add_argument(
            "nofo_id", type=int, help="ID of the NOFO to count updates for"
        )

    def handle(self, *args, **options):
        self.count_updates(options["nofo_id"])

    def count_updates(self, nofo_id):
        nofo = Nofo.objects.get(pk=nofo_id)

        subsection_ids = Subsection.objects.filter(section__nofo=nofo).values_list(
            "id", flat=True
        )

        events = CRUDEvent.objects.filter(
            event_type=2,
            content_type__id__in=[7, 9],
            object_id__in=[nofo_id] + list(subsection_ids),
        )

        count = 0

        for event in events:
            try:
                changed_fields = json.loads(event.changed_fields)

                if not changed_fields:
                    continue  # Skip this event if changed_fields is None
                if "updated" in changed_fields and len(changed_fields) == 1:
                    continue  # Skip this event if 'updated' is the only key in changed fields

                count += 1
            except json.JSONDecodeError:
                # Handle cases where changed_fields is not a valid JSON string
                self.stdout.write(self.style.ERROR("Invalid JSON in changed_fields"))
                continue

        self.stdout.write(
            self.style.SUCCESS(f"Total updates for NOFO {nofo_id}: {count}")
        )
