"""
Query layer behind the NOFO Builder usage & quality metrics page (see #865).

Each function takes a list of (month_start, month_end) tuples - see
`months_from()` - and returns one value per month. There's no hardcoded date
range anywhere in this module: callers decide how far back to look and how
far forward to go, so new months just show up as they happen.
"""

from datetime import datetime
from statistics import median

from django.db.models import Avg
from django.utils import timezone

from .models import ImportAttempt, MetricsActivity, MetricsActor, MetricsNofo


def month_boundaries(start, count):
    """
    Return `count` consecutive (month_start, month_end) tz-aware datetime
    tuples, beginning with the calendar month containing `start`.
    """
    boundaries = []
    year, month = start.year, start.month
    for _ in range(count):
        month_start = timezone.make_aware(datetime(year, month, 1))
        if month == 12:
            next_year, next_month = year + 1, 1
        else:
            next_year, next_month = year, month + 1
        month_end = timezone.make_aware(datetime(next_year, next_month, 1))
        boundaries.append((month_start, month_end))
        year, month = next_year, next_month
    return boundaries


def months_from(start, end=None):
    """
    Build the (month_start, month_end) list from `start`'s month through
    `end`'s month inclusive (defaults to now) - the open-ended range the
    metrics page and management command both use. The final tuple is the
    current, still-in-progress month.
    """
    end = end or timezone.now()
    count = (end.year - start.year) * 12 + (end.month - start.month) + 1
    return month_boundaries(start, count)


def total_users_by_month(months):
    """Eligible signups, retaining deleted accounts and signup-time eligibility."""
    return [
        MetricsActor.objects.filter(included=True, joined_at__lt=end).count()
        for _, end in months
    ]


def active_users_by_month(months):
    """Actors with eligible activity in each month, classified at activity time."""
    return [
        MetricsActivity.objects.filter(
            month__gte=start.date(), month__lt=end.date()
        ).count()
        for start, end in months
    ]


def nofos_created_by_month(months):
    """Creation facts survive deletion and retain creation-time eligibility."""
    return [
        MetricsNofo.objects.filter(
            included=True, created_at__gte=start, created_at__lt=end
        ).count()
        for start, end in months
    ]


def time_to_first_live_pdf_by_month(months):
    """Median elapsed hours for each creation cohort, including later first prints."""
    results = []
    for start, end in months:
        facts = MetricsNofo.objects.filter(
            included=True,
            created_at__gte=start,
            created_at__lt=end,
            first_live_at__isnull=False,
        ).values_list("created_at", "first_live_at")
        hours = [
            (printed - created).total_seconds() / 3600 for created, printed in facts
        ]
        results.append(median(hours) if hours else None)
    return results


def import_error_rate_by_month(months):
    """% of import attempts (new imports + reimports) that failed outright.
    Excludes attempts by Bloomworks/staging accounts."""
    results = []
    for start, end in months:
        attempts = ImportAttempt.objects.filter(
            created_at__gte=start, created_at__lt=end
        ).filter(metrics_included=True)
        total = attempts.count()
        if not total:
            results.append(None)
            continue
        failed = attempts.exclude(error_code="").count()
        results.append(round(100 * failed / total, 1))
    return results


def avg_warnings_by_month(months):
    """Average mammoth warning count across successful import attempts.
    Excludes attempts by Bloomworks/staging accounts."""
    results = []
    for start, end in months:
        avg = (
            ImportAttempt.objects.filter(
                created_at__gte=start, created_at__lt=end, error_code=""
            )
            .filter(metrics_included=True)
            .aggregate(avg=Avg("warning_count"))["avg"]
        )
        results.append(round(avg, 2) if avg is not None else None)
    return results
