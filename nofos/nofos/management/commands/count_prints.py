import json

from django.core.management.base import BaseCommand
from easyaudit.models import CRUDEvent
from nofos.models import Nofo


class Command(BaseCommand):
    help = "Fetches print events for a specific NOFO or all NOFOs."

    def add_arguments(self, parser):
        parser.add_argument(
            "nofo_id",
            nargs="?",
            type=int,
            help="ID of the NOFO to fetch print events for (optional if using --all)",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Fetch print events for all NOFOs (skipping archived ones).",
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
        nofos = Nofo.objects.filter(archived__isnull=True).order_by(
            "created"
        )  # no archived nofos, earliest creation date appears first
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

        print_events = []
        last_live_print = None

        # Filter events where "action" in changed_fields is "nofo_print"
        for event in events:
            try:
                changed_fields = json.loads(event.changed_fields)
                if changed_fields and changed_fields.get("action") == "nofo_print":
                    print_mode = changed_fields.get("print_mode", ["unknown"])[0]
                    print_events.append(event)

                    # Track the latest "live" print event
                    if print_mode == "live":
                        if last_live_print is None or event.datetime > last_live_print:
                            last_live_print = event.datetime

            except json.JSONDecodeError:
                # TODO remove this
                print("json.JSONDecodeError:", event.changed_fields)
                self.stdout.write(
                    self.style.ERROR(
                        f"Invalid JSON in changed_fields for event ID {event.id}"
                    )
                )
                continue

        # Calculate time difference in hours
        time_diff = None
        if last_live_print:
            time_diff = (last_live_print - nofo.created).total_seconds() / 3600

        # Tab-separated output
        self.stdout.write(
            f"{nofo.id}\thttps://nofo.rodeo/nofos/{nofo.id}/edit\t{nofo.number}\t{nofo.status}\t{nofo.created}\t{nofo.updated}\t{len(print_events)}\t{last_live_print or 'None'}\t{round(time_diff, 2) if time_diff else 'N/A'}"
        )
