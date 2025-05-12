import json

from django.core.management.base import BaseCommand
from easyaudit.models import CRUDEvent
from nofos.models import Nofo
from users.models import BloomUser


class Command(BaseCommand):
    help = "Fetches 'nofo_reimport' events for a specific NOFO or all NOFOs."

    def add_arguments(self, parser):
        parser.add_argument(
            "nofo_id",
            nargs="?",
            type=int,
            help="ID of the NOFO to fetch 'nofo_reimport' events for (optional if using --all)",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Fetch 'nofo_reimport' events for all NOFOs (skipping archived ones).",
        )

    def handle(self, *args, **options):
        nofo_id = options.get("nofo_id")
        all_nofos = options.get("all")

        if all_nofos:
            self.handle_all()
        elif nofo_id is not None:
            self.handle_single(nofo_id)
        else:
            self.stdout.write(
                self.style.ERROR("Please provide a NOFO ID or use --all.")
            )

    def handle_all(self):
        # Fetch all non-archived NOFOs
        nofos = Nofo.objects.filter(archived__isnull=True).order_by("created")
        for nofo in nofos:
            self.process_nofo(nofo)

    def handle_single(self, nofo_id):
        try:
            nofo = Nofo.objects.get(pk=nofo_id)
            self.process_nofo(nofo)
        except Nofo.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"NOFO with ID {nofo_id} does not exist.")
            )

    def process_nofo(self, nofo):
        # Fetch all update events for this NOFO
        events = CRUDEvent.objects.filter(
            content_type__model="nofo",
            object_id=nofo.id,
            event_type=2,  # Update events
        )

        reimport_events = []

        # Filter events where "action" in changed_fields is "nofo_reimport"
        for event in events:
            try:
                changed_fields = json.loads(event.changed_fields)
                if changed_fields and changed_fields.get("action") == "nofo_reimport":
                    reimport_events.append(event)
            except json.JSONDecodeError:
                self.stdout.write(
                    self.style.ERROR(
                        f"Invalid JSON in changed_fields for event ID {event.id}"
                    )
                )
                continue

        # Tab-separated output for each reimport event
        for event in reimport_events:
            try:
                user = BloomUser.objects.get(pk=event.user_id)
                user_email = user.email
            except BloomUser.DoesNotExist:
                user_email = "Unknown"

            self.stdout.write(
                f"{nofo.id}\thttps://nofo.rodeo/nofos/{nofo.id}/edit\t{nofo.number}\t{nofo.status}\t{nofo.created}\t{nofo.updated}\t{user_email}\t{event.datetime}"
            )

        # Summary for the NOFO
        self.stdout.write(
            self.style.SUCCESS(
                f"NOFO {nofo.id}, {nofo.number}: {len(reimport_events)} reimport events."
            )
        )
