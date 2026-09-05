"""
Query layer behind the NOFO Builder usage & quality metrics page (see #865).

Each function takes a list of (month_start, month_end) tuples - see
`months_from()` - and returns one value per month. There's no hardcoded date
range anywhere in this module: callers decide how far back to look and how
far forward to go, so new months just show up as they happen.
"""

import json
from datetime import datetime
from statistics import median

from django.db.models import Avg
from django.utils import timezone
from easyaudit.models import CRUDEvent
from users.models import BloomUser

from .models import ImportAttempt, Nofo

# Content types whose CRUDEvents count as "the user did something in NOFO
# Builder" for the active-users metric.
ACTIVITY_CONTENT_TYPES = ["nofo", "section", "subsection"]

# BloomUser.group / Nofo.group values that represent internal Bloomworks
# staff/admin accounts and the staging test environment, not real OpDiv
# end-users - excluded from every metric below so internal activity doesn't
# inflate numbers meant to describe actual product usage.
EXCLUDED_GROUPS = ["bloom", "staging"]


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
    """Cumulative BloomUser count as of the end of each month, excluding
    Bloomworks/staging accounts."""
    return [
        BloomUser.objects.exclude(group__in=EXCLUDED_GROUPS)
        .filter(date_joined__lt=end)
        .count()
        for _, end in months
    ]


def active_users_by_month(months):
    """
    Distinct users with >=1 CRUDEvent on a Nofo, Section, or Subsection within
    each month (import, edit, print - logging in alone doesn't create one).
    Excludes Bloomworks/staging accounts.
    """
    results = []
    for start, end in months:
        count = (
            CRUDEvent.objects.filter(
                content_type__model__in=ACTIVITY_CONTENT_TYPES,
                datetime__gte=start,
                datetime__lt=end,
                user_id__isnull=False,
            )
            .exclude(user__group__in=EXCLUDED_GROUPS)
            .values("user_id")
            .distinct()
            .count()
        )
        results.append(count)
    return results


def nofos_created_by_month(months):
    """New NOFO records first imported in each month, excluding
    Bloomworks/staging NOFOs."""
    return [
        Nofo.objects.exclude(group__in=EXCLUDED_GROUPS)
        .filter(created__gte=start, created__lt=end)
        .count()
        for start, end in months
    ]


def _first_live_print_by_nofo():
    """Map of {str(nofo_id): earliest 'live' nofo_print CRUDEvent datetime}."""
    events = (
        CRUDEvent.objects.filter(
            content_type__model="nofo",
            event_type=CRUDEvent.UPDATE,
            changed_fields__contains='"nofo_print"',
        )
        .order_by("datetime")
        .values("object_id", "changed_fields", "datetime")
    )

    first_live = {}
    for event in events:
        nofo_id = str(event["object_id"])
        if nofo_id in first_live:
            continue  # already have an earlier one for this NOFO

        try:
            changed_fields = json.loads(event["changed_fields"])
        except (TypeError, ValueError):
            continue
        if not changed_fields or changed_fields.get("action") != "nofo_print":
            continue
        if changed_fields.get("print_mode", ["unknown"])[0] != "live":
            continue

        first_live[nofo_id] = event["datetime"]

    return first_live


def time_to_first_live_pdf_by_month(months):
    """
    Median hours from Nofo.created to that NOFO's first live (non-watermarked)
    PDF download, for NOFOs first imported in each month. This is full
    calendar time, including any time spent waiting on outside review - not
    just active editing. NOFOs never downloaded aren't counted (there's
    nothing to average), so this only reflects NOFOs that reached a finished
    PDF. Excludes Bloomworks/staging NOFOs.
    """
    first_live_by_nofo = _first_live_print_by_nofo()
    nofos = list(
        Nofo.objects.exclude(group__in=EXCLUDED_GROUPS)
        .filter(created__isnull=False)
        .values("id", "created")
    )

    results = []
    for start, end in months:
        hours = []
        for nofo in nofos:
            if not (start <= nofo["created"] < end):
                continue
            live_at = first_live_by_nofo.get(str(nofo["id"]))
            if live_at:
                hours.append((live_at - nofo["created"]).total_seconds() / 3600)
        results.append(median(hours) if hours else None)
    return results


def import_error_rate_by_month(months):
    """% of import attempts (new imports + reimports) that failed outright.
    Excludes attempts by Bloomworks/staging accounts."""
    results = []
    for start, end in months:
        attempts = ImportAttempt.objects.filter(
            created_at__gte=start, created_at__lt=end
        ).exclude(user__group__in=EXCLUDED_GROUPS)
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
            .exclude(user__group__in=EXCLUDED_GROUPS)
            .aggregate(avg=Avg("warning_count"))["avg"]
        )
        results.append(round(avg, 2) if avg is not None else None)
    return results
