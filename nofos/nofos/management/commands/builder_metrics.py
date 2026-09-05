from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from nofos.metrics import (
    active_users_by_month,
    avg_warnings_by_month,
    import_error_rate_by_month,
    months_from,
    nofos_created_by_month,
    time_to_first_live_pdf_by_month,
    total_users_by_month,
)

# When NOFO Builder metrics tracking started (see #865) - not a hard cutoff,
# just this command's default starting point if --since isn't passed.
DEFAULT_SINCE = "2026-09"


class Command(BaseCommand):
    help = (
        "Prints the NOFO Builder usage & quality metrics (see #865) as one "
        "tab-separated row per month. Meant for validating the query layer "
        "by hand before it's wired into the metrics page itself."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            default=DEFAULT_SINCE,
            help=f"First month to include, as YYYY-MM (default: {DEFAULT_SINCE}).",
        )

    def handle(self, *args, **options):
        start = timezone.make_aware(datetime.strptime(options["since"], "%Y-%m"))
        months = months_from(start)

        total_users = total_users_by_month(months)
        active_users = active_users_by_month(months)
        nofos_created = nofos_created_by_month(months)
        time_to_pdf = time_to_first_live_pdf_by_month(months)
        error_rate = import_error_rate_by_month(months)
        avg_warnings = avg_warnings_by_month(months)

        self.stdout.write(
            "month\ttotal_users\tactive_users\tnofos_created\t"
            "median_hours_to_live_pdf\terror_rate_pct\tavg_warnings_per_import"
        )
        for i, (month_start, _) in enumerate(months):
            self.stdout.write(
                "{}\t{}\t{}\t{}\t{}\t{}\t{}".format(
                    month_start.strftime("%Y-%m"),
                    total_users[i],
                    active_users[i],
                    nofos_created[i],
                    (round(time_to_pdf[i], 1) if time_to_pdf[i] is not None else "N/A"),
                    error_rate[i] if error_rate[i] is not None else "N/A",
                    avg_warnings[i] if avg_warnings[i] is not None else "N/A",
                )
            )
