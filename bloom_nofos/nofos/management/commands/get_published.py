import json

from django.core.management.base import BaseCommand
from easyaudit.models import CRUDEvent
from nofos.models import Nofo


class Command(BaseCommand):
    help = "Find NOFOs published status timestamps."

    def add_arguments(self, parser):
        parser.add_argument(
            "nofo_id", nargs="?", type=int, help="ID of the NOFO to process"
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Process all NOFOs that are published (excluding archived ones).",
        )

    def handle(self, *args, **options):
        if options["all"]:
            self.process_all_nofo_statuses()
        elif options["nofo_id"]:
            self.process_nofo_status(options["nofo_id"])
        else:
            self.stdout.write(self.style.ERROR("No NOFO ID or --all flag provided."))

    def process_all_nofo_statuses(self):
        # Fetch all published NOFOs excluding archived ones
        nofos = Nofo.objects.filter(status="published", archived__isnull=True).order_by(
            "created"
        )
        for nofo in nofos:
            self.process_nofo_status(nofo.id)

    def process_nofo_status(self, nofo_id):
        try:
            nofo = Nofo.objects.get(pk=nofo_id)
        except Nofo.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"NOFO with ID {nofo_id} does not exist.")
            )
            return

        # Find all CRUDEvents for this NOFO with a status change to "published"
        events = CRUDEvent.objects.filter(
            content_type__model="nofo",
            object_id=nofo_id,
            changed_fields__icontains='"status":',  # Look for status changes
        )

        published_timestamps = []

        for event in events:
            try:
                changed_fields = json.loads(event.changed_fields)
                if (
                    "status" in changed_fields
                    and isinstance(changed_fields["status"], list)
                    and changed_fields["status"][-1] == "published"
                ):
                    published_timestamps.append(event.datetime)
            except json.JSONDecodeError:
                self.stdout.write(
                    self.style.WARNING(
                        f"Invalid JSON in changed_fields for event ID {event.id}"
                    )
                )

        if published_timestamps:
            earliest_timestamp = min(published_timestamps)
            self.stdout.write(
                f"{nofo.id}\thttps://nofo.rodeo/nofos/{nofo.id}/edit\t{nofo.number}\t{nofo.status}\t{nofo.created}\t{nofo.updated}\t{earliest_timestamp}"
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"No published status found for NOFO ID {nofo.id}.")
            )
