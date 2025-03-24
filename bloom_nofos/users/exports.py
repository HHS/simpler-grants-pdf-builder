import csv
import json
from datetime import datetime

from django.db.models import Q
from django.http import HttpResponse
from django.utils.timezone import make_aware
from easyaudit.models import CRUDEvent
from nofos.models import Nofo, Subsection


def export_nofo_report(start_date, end_date, user):
    """
    Handles exporting all NOFOs the logged-in user has edited.
    """

    events_filters = {
        "event_type": 2,  # UPDATE events
        "content_type__model__in": ["nofo", "subsection"],
        "user": user,
    }

    # Convert dates to timezone-aware datetimes (set to start/end of the day)
    if start_date:
        start_date = make_aware(datetime.combine(start_date, datetime.min.time()))
        events_filters["datetime__gte"] = start_date

    if end_date:
        end_date = make_aware(datetime.combine(end_date, datetime.max.time()))
        events_filters["datetime__lte"] = end_date

    # Query CRUDEvent for NOFO edits within date range
    events = CRUDEvent.objects.filter(**events_filters).values(
        "object_id", "datetime", "content_type__model", "changed_fields"
    )

    # Organize events into a dict mapping NOFO IDs to edit counts
    nofo_edit_counts = {}

    for event in events:
        object_id = event["object_id"]
        model = event["content_type__model"]

        # Determine NOFO ID
        if model == "nofo":
            nofo_id = object_id

        elif model == "subsection":
            nofo_id = (
                Subsection.objects.filter(id=object_id)
                .values_list("section__nofo_id", flat=True)
                .first()
            )
            if not nofo_id:
                continue  # Skip if we can't resolve NOFO ID

        # Skip events where the only change was "updated" timestamp
        try:
            changed_fields = json.loads(event["changed_fields"])
            if (
                changed_fields
                and "updated" in changed_fields
                and len(changed_fields) == 1
            ):
                continue
        except json.JSONDecodeError:
            continue  # Skip events with invalid JSON

        # Count edits for each NOFO
        nofo_id = int(nofo_id)
        nofo_edit_counts[nofo_id] = nofo_edit_counts.get(nofo_id, 0) + 1

    # Fetch NOFO details for the edited NOFOs
    nofos = (
        Nofo.objects.filter(id__in=nofo_edit_counts.keys())
        .filter(Q(archived__isnull=True))
        .values("id", "number", "title", "status")
    )

    rows = [
        [
            "NOFO ID",
            "NOFO Number",
            "NOFO Title",
            "Nofo Status",
            "User Email",
            "Edits",
        ]
    ]

    for nofo in nofos:
        rows.append(
            [
                nofo["id"],
                nofo["number"],
                nofo["title"],
                nofo["status"],
                user.email,
                nofo_edit_counts[nofo["id"]],
            ]
        )

    return rows
