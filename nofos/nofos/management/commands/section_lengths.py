import csv

from django.core.management.base import BaseCommand
from nofos.models import Nofo


class Command(BaseCommand):
    help = "Export NOFO sections and subsections to a CSV file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-file",
            type=str,
            default="section_lengths.csv",
            help="Output file name for the CSV (default: section_lengths.csv)",
        )

        parser.add_argument(
            "--nofo-id", nargs="?", type=int, help="ID of a single NOFO to process."
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Process all NOFOs (excluding archived ones).",
        )

    def handle(self, *args, **options):
        output_file = options["output_file"]

        if options["all"]:
            nofos = Nofo.objects.filter(archived__isnull=True).order_by("created")
        elif options["nofo_id"]:
            nofos = Nofo.objects.filter(pk=options["nofo_id"])
        else:
            self.stdout.write(
                self.style.ERROR("Provide either a NOFO ID or --all flag.")
            )
            return

        # Open the CSV file for writing
        with open(output_file, mode="w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                ["id", "url", "number", "section_or_subsection", "name", "char_length"]
            )

            for nofo in nofos:
                sections = nofo.sections.all()
                section_count = 0
                subsection_count = 0

                for section in sections:
                    section_count += 1
                    section_row = [
                        nofo.id,
                        f"https://nofo.rodeo/nofos/{nofo.id}/edit",
                        nofo.number,
                        "section",
                        section.name,
                        len(section.name) if section.name else 0,
                    ]
                    writer.writerow(section_row)

                    subsections = section.subsections.all()
                    for subsection in subsections:
                        if subsection.name:  # Only include subsections with a name
                            subsection_count += 1
                            subsection_row = [
                                nofo.id,
                                f"https://nofo.rodeo/nofos/{nofo.id}/edit",
                                nofo.number,
                                "subsection",
                                subsection.name,
                                len(subsection.name),
                            ]
                            writer.writerow(subsection_row)

                # Print summary for this NOFO
                self.stdout.write(
                    self.style.SUCCESS(
                        f"NOFO {nofo.id}, {nofo.number}, Sections: {section_count}, Subsections: {subsection_count}"
                    )
                )

        self.stdout.write(self.style.SUCCESS(f"Data exported to {output_file}"))
