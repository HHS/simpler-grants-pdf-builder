import csv

from django.core.management.base import BaseCommand
from guides.models import ContentGuide
from nofos.models import Nofo


class Command(BaseCommand):
    help = (
        "Export NOFOs and ContentGuides with UUIDs and future URL links to a CSV file."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-file",
            type=str,
            default="nofos_and_guides.csv",
            help="Output file name for the CSV (default: nofos_and_guides.csv)",
        )

    def handle(self, *args, **options):
        output_file = options["output_file"]

        with open(output_file, mode="w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                [
                    "type",
                    "id",
                    "id_url",
                    "uuid",
                    "uuid_url",
                    "number",
                    "title",
                    "status",
                    "created",
                    "updated",
                    "archived",
                ]
            )

            # Export NOFOs
            self.export_nofos(writer)
            # Export ContentGuides
            self.export_content_guides(writer)

        self.stdout.write(self.style.SUCCESS(f"Data exported to {output_file}"))

    def export_nofos(self, writer):
        self.stdout.write("Exporting NOFOs...")
        nofos = Nofo.objects.all().order_by("created")

        for nofo in nofos:
            print("NOFO: {}".format(nofo.id))
            writer.writerow(
                [
                    "Nofo",
                    nofo.id,
                    f"https://nofo.rodeo/nofos/{nofo.id}/edit",
                    nofo.uuid,
                    f"https://nofo.rodeo/nofos/{nofo.uuid}/edit",
                    nofo.number,
                    nofo.title,
                    nofo.status,
                    nofo.created,
                    nofo.updated,
                    nofo.archived,
                ]
            )
        self.stdout.write(self.style.SUCCESS("NOFOs exported."))

    def export_content_guides(self, writer):
        self.stdout.write("Exporting ContentGuides...")
        guides = ContentGuide.objects.all().order_by("created")

        for guide in guides:
            print("ContentGuide: {}".format(guide.id))
            writer.writerow(
                [
                    "ContentGuide",
                    guide.id,
                    f"https://nofo.rodeo/guides/{guide.id}/edit",
                    guide.uuid,
                    f"https://nofo.rodeo/guides/{guide.uuid}/edit",
                    "",
                    guide.title,
                    guide.status,
                    guide.created,
                    guide.updated,
                    guide.archived,
                ]
            )
        self.stdout.write(self.style.SUCCESS("ContentGuides exported."))
