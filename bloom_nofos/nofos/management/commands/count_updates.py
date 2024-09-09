import json

from django.core.management.base import BaseCommand
from easyaudit.models import CRUDEvent
from nofos.models import Nofo, Subsection
from users.models import BloomUser


class Command(BaseCommand):
    help = "Counts updates for a specific NOFO or all NOFOs"

    def add_arguments(self, parser):
        parser.add_argument(
            "nofo_id", nargs="?", type=int, help="ID of the NOFO to count updates for"
        )
        parser.add_argument(
            "--all", action="store_true", help="Count updates for all NOFOs"
        )
        parser.add_argument(
            "--with-users",
            action="store_true",
            help="Include user emails in the output (only valid when a single NOFO ID is provided)",
        )

    def handle(self, *args, **options):
        if options["all"]:
            self.count_updates_all()
        else:
            nofo_id = options.get("nofo_id")
            if nofo_id is not None:
                self.count_updates(nofo_id, with_users=options["with_users"])
            else:
                self.stdout.write(self.style.ERROR("No NOFO ID provided"))

    def count_updates_all(self):
        nofos = Nofo.objects.all()
        for nofo in nofos:
            self.count_updates(nofo.pk)

    def count_updates(self, nofo_id, with_users=False):
        nofo = Nofo.objects.get(pk=nofo_id)

        subsection_ids = Subsection.objects.filter(section__nofo=nofo).values_list(
            "id", flat=True
        )

        events = CRUDEvent.objects.filter(
            event_type=2,
            content_type__model__in=["nofo", "subsection"],
            object_id__in=[nofo_id] + list(subsection_ids),
        )

        edit_count = 0

        for event in events:
            try:
                changed_fields = json.loads(event.changed_fields)
                if not changed_fields:
                    continue  # Skip this event if changed_fields is None
                if "updated" in changed_fields and len(changed_fields) == 1:
                    continue  # Skip this event if 'updated' is the only key in changed fields

                edit_count += 1

                if with_users:
                    user = BloomUser.objects.get(pk=event.user_id)
                    self.stdout.write("Update #{}: {}".format(edit_count, user))

            except json.JSONDecodeError:
                # Handle cases where changed_fields is not a valid JSON string
                self.stdout.write(self.style.ERROR("Invalid JSON in changed_fields"))
                continue

        self.stdout.write(
            self.style.SUCCESS(
                f"{nofo_id}\thttps://nofo.rodeo/nofos/{nofo_id}/edit\t{nofo.number}\t{nofo.status}\t{nofo.created}\t{nofo.updated}\t{edit_count}"
            )
        )
