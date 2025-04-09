import json
from datetime import datetime

from django.db.models import Q
from django.utils.timezone import make_aware
from easyaudit.models import CRUDEvent
from nofos.models import Nofo, Subsection

from .models import BloomUser


def get_filename(base_filename, group, start_date, end_date):
    # Determine the file name based on provided dates.
    filename = "{}_{}".format(base_filename, group if group else "user")
    if start_date and end_date:
        # Both dates provided: use both.
        return "{}_{}_{}.csv".format(
            filename, start_date.isoformat(), end_date.isoformat()
        )
    elif start_date or end_date:
        # Only one date provided: use whichever is not None.
        provided_date = start_date if start_date else end_date
        return "{}_{}.csv".format(filename, provided_date.isoformat())

    return "{}.csv".format(filename)


def export_nofo_report(start_date, end_date, user, group=None):
    """
    Handles exporting all NOFOs for the logged-in user or everyone in their group.
    Now aggregates the number of edits per user and per NOFO.
    """

    # Start with audit events that have been recorded.
    events_filters = {
        "event_type": 2,  # UPDATE events
        "content_type__model__in": ["nofo", "subsection"],
    }

    if group:
        # For a group export, get events for all users in the given group.
        events_filters["user__in"] = BloomUser.objects.filter(group=group)
    else:
        # For an individual export, just get events for the current user.
        events_filters["user"] = user

    # Convert dates to timezone-aware datetimes (set to start or end of the day)
    if start_date:
        start_date = make_aware(datetime.combine(start_date, datetime.min.time()))
        events_filters["datetime__gte"] = start_date

    if end_date:
        end_date = make_aware(datetime.combine(end_date, datetime.max.time()))
        events_filters["datetime__lte"] = end_date

    # Include the "user" field in our values so we know who did the edit.
    events = CRUDEvent.objects.filter(**events_filters).values(
        "user", "object_id", "datetime", "content_type__model", "changed_fields"
    )

    # Group edits by (user, NOFO id).
    per_edit_counts = {}
    for event in events:
        current_user_id = event["user"]

        # Determine the actual NOFO ID for the event.
        model = event["content_type__model"]
        if model == "nofo":
            nofo_id = event["object_id"]
        elif model == "subsection":
            nofo_id = (
                Subsection.objects.filter(id=event["object_id"])
                .values_list("section__nofo_id", flat=True)
                .first()
            )
            if not nofo_id:
                continue  # Skip if unable to resolve the NOFO ID.
        else:
            continue

        # Skip events where the only change was the "updated" timestamp.
        try:
            changed_fields = json.loads(event["changed_fields"])
            if (
                changed_fields
                and "updated" in changed_fields
                and len(changed_fields) == 1
            ):
                continue
        except json.JSONDecodeError:
            continue  # Skip events with invalid JSON.

        # Increment the count for this (user, NOFO) pair.
        key = (current_user_id, int(nofo_id))
        per_edit_counts[key] = per_edit_counts.get(key, 0) + 1

    # Get a distinct list of NOFO IDs involved.
    nofo_ids = {key[1] for key in per_edit_counts.keys()}

    # Fetch NOFO details.
    nofos = (
        Nofo.objects.filter(id__in=nofo_ids)
        .filter(Q(archived__isnull=True))
        .values("id", "number", "title", "status")
    )
    nofos_by_id = {n["id"]: n for n in nofos}

    # Fetch the users involved (only needed if exporting for a group).
    user_ids = {key[0] for key in per_edit_counts.keys()}
    users_by_id = {}
    if group:
        users = BloomUser.objects.filter(id__in=user_ids).values("id", "email")
        users_by_id = {u["id"]: u["email"] for u in users}
    else:
        # If not a group export, use the current user's email.
        users_by_id[user.id] = user.email

    # Prepare the CSV rows.
    # CSV Header: you can adjust the order as needed.
    rows = [
        [
            "User Email",
            "NOFO ID",
            "NOFO Number",
            "NOFO Title",
            "NOFO Status",
            "Edits",
        ]
    ]

    for (user_id, nofo_id), edit_count in per_edit_counts.items():
        # If the NOFO is archived, it won't be in nofos_by_id, so skip it.
        if nofo_id not in nofos_by_id:
            continue

        # Get the email, NOFO details, etc.
        email = users_by_id.get(user_id, "")
        nofo_details = nofos_by_id.get(nofo_id, {})
        row = [
            email,
            nofo_id,
            nofo_details.get("number", ""),
            nofo_details.get("title", ""),
            nofo_details.get("status", ""),
            edit_count,
        ]
        rows.append(row)

    return rows
