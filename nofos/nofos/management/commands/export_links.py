import csv

from django.core.management.base import BaseCommand
from nofos.models import Nofo
from nofos.nofo import find_external_links


class Command(BaseCommand):
    help = "Extracts external links from NOFO documents and outputs them."

    def add_arguments(self, parser):
        parser.add_argument(
            "nofo_id", nargs="?", type=int, help="ID of the NOFO to extract links from"
        )
        parser.add_argument(
            "--all", action="store_true", help="Extract links from all NOFOs"
        )
        parser.add_argument(
            "--output",
            type=str,
            default="export_links.csv",
            help="Output file name for the CSV (default: nofo_links.csv)",
        )
        parser.add_argument(
            "--live",
            type=bool,
            default=False,
            help="Specify if links are live",
        )

    def handle(self, *args, **options):
        output_file = options["output"]
        domain = "https://nofo.rodeo" if options["live"] else "http://localhost:8000"

        # Determine which NOFOs to process
        if options["all"]:
            nofos = Nofo.objects.all()
        else:
            nofo_id = options.get("nofo_id")
            if nofo_id is None:
                self.stdout.write(self.style.ERROR("No NOFO ID provided"))
                return
            nofos = Nofo.objects.filter(id=nofo_id)

        if not nofos.exists():
            self.stdout.write(self.style.ERROR("No NOFOs found."))
            return

        links_count = 0

        # Write the output to a CSV file
        with open(output_file, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "nofo_id",
                    "nofo_number",
                    "nofo_status",
                    "url",
                    "section_name",
                    "subsection_name",
                    "link_to_subsection",
                ]
            )

            print("---")
            print("All nofos: {}".format(len(nofos)))
            print(
                "All non-archived nofos: {}".format(
                    len(nofos.exclude(archived__isnull=False))
                )
            )

            for nofo in nofos.exclude(archived__isnull=False):
                print("---")
                print("NOFO: {}".format(nofo.number))
                links = find_external_links(nofo)
                print("Links in this NOFO: {}".format(len(links)))
                links_count += len(links)

                for link in links:
                    writer.writerow(
                        [
                            nofo.id,
                            nofo.number,
                            nofo.status,
                            link["url"],
                            (
                                link["section"].name if link["section"] else ""
                            ),  # Section name
                            (
                                link["subsection"].name if link["subsection"] else ""
                            ),  # Subsection name
                            (
                                "{}/nofos/{}/section/{}/subsection/{}/edit".format(
                                    domain,
                                    nofo.id,
                                    link["section"].id,
                                    link["subsection"].id,
                                )
                            ),
                        ]
                    )

        print("---")
        print("Total links in all NOFOs: {}".format(links_count))
        self.stdout.write(self.style.SUCCESS(f"Links extracted to {output_file}"))
