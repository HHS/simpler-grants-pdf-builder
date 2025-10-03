import json
from collections import OrderedDict

from django.db.models import Q
from easyaudit.models import CRUDEvent

from .models import Subsection


def deduplicate_audit_events_by_day_and_object(events):
    """
    Deduplicate audit events so that only the most recent event
    for a given object (type + description) on a given day is kept.

    Args:
        events (list of dict): A list of audit event dictionaries, each with
        'object_type', 'object_description', and 'timestamp' keys.

    Returns:
        list: Deduplicated list of events, keeping the latest per object per day.
    """
    deduplicated = OrderedDict()

    for event in events:
        key = (
            event["object_type"],
            event["object_description"],
            event["timestamp"].date(),  # Use only the date
        )
        deduplicated[key] = event  # Overwrites earlier events on same object + day

    return list(deduplicated.values())


def format_audit_event(event):
    """
    Takes a CRUDEvent and returns a formatted dictionary for display in the UI.
    Includes enhanced labels and object details.
    """
    event_details = {
        "id": event.id,
        "event_type": event.get_event_type_display(),
        "object_type": event.content_type.model.title(),
        "object_description": event.object_repr,
        "user": event.user,
        "timestamp": event.datetime,
        "raw_event": event,
    }

    # Get html_id if it's available (safe fallback)
    try:
        event_details["object_html_id"] = (
            json.loads(event.object_json_repr)[0].get("fields", {}).get("html_id", "")
        )
    except Exception:
        event_details["object_html_id"] = ""

    # Improve object description for subsection edits
    if event.content_type.model == "subsection":
        try:
            subsection = Subsection.objects.get(id=event.object_id)
            name = subsection.name or "#{}".format(subsection.order)
            event_details["object_description"] = f"{subsection.section.name} - {name}"
        except Subsection.DoesNotExist:
            pass

    # Handle custom audit events
    if event.changed_fields:
        try:
            changed_fields = json.loads(event.changed_fields)

            if isinstance(changed_fields, dict):
                # Handle custom actions
                if "action" in changed_fields:
                    action = changed_fields["action"]
                    if action == "nofo_import":
                        event_details["event_type"] = "NOFO Imported"
                    elif action == "nofo_print":
                        event_details["event_type"] = "NOFO Printed"
                        if "print_mode" in changed_fields:
                            event_details[
                                "event_type"
                            ] += f" ({changed_fields['print_mode'][0]} mode)"
                    elif action == "nofo_reimport":
                        event_details["event_type"] = "NOFO Re-imported"

                # Improve object description for Nofo field changes
                elif event.content_type.model == "nofo":
                    field_name = next(iter(changed_fields.keys()))
                    formatted_field = " ".join(
                        word.title() for word in field_name.split("_")
                    )
                    event_details["object_description"] = formatted_field
        except Exception:
            pass

    return event_details


def get_audit_events_for_nofo(nofo, reverse=True, limit_per_set=None):
    """
    Return audit events related to the given NOFO: the NOFO object,
    its sections, and its subsections.

    Args:
        reverse (bool): newest-first if True.
        limit_per_set (int|None): if set, cap each bucket (NOFO / Sections / Subsections)
                                  by datetime DESC before merging.
    """

    def _filter_updated_events(events):
        """Remove events where only 'updated' or only 'uuid' changed."""
        filtered_events = []
        for event in events:
            if event.event_type != CRUDEvent.UPDATE:
                filtered_events.append(event)
                continue
            if event.changed_fields == "null":
                continue
            try:
                changed = json.loads(event.changed_fields or "{}")

                # Normalize keys into a set
                keys = set(changed.keys()) if isinstance(changed, dict) else set()

                # Ignore if only 'updated' or only 'uuid'
                if keys in ({"updated"}, {"uuid"}):
                    continue

                filtered_events.append(event)
            except Exception:
                # On parse error, safest is to keep
                filtered_events.append(event)
        return filtered_events

    # Get audit events for the NOFO
    nofo_events_qs = CRUDEvent.objects.filter(
        object_id=nofo.id,
        content_type__model="nofo",
    ).order_by("-datetime")
    if limit_per_set:
        nofo_events_qs = nofo_events_qs[:limit_per_set]

    # Get audit events for Sections
    section_ids = list(nofo.sections.values_list("id", flat=True))
    section_ids_str = [str(sid) for sid in section_ids]
    section_events_qs = CRUDEvent.objects.filter(
        object_id__in=section_ids_str,
        content_type__model="section",
    ).order_by("-datetime")
    if limit_per_set:
        section_events_qs = section_events_qs[:limit_per_set]

    # Get audit events for Subsections (even if they have been deleted)
    subsection_filter = Q()
    for section_id in section_ids:
        subsection_filter |= Q(object_json_repr__contains=str(section_id))

    subsection_events_qs = (
        CRUDEvent.objects.filter(content_type__model="subsection")
        .filter(subsection_filter)
        .order_by("-datetime")
    )
    if limit_per_set:
        subsection_events_qs = subsection_events_qs[:limit_per_set]

    # Only NOFO events get _filter_updated_events
    events = list(nofo_events_qs) + list(section_events_qs) + list(subsection_events_qs)

    return sorted(
        _filter_updated_events(events),
        key=lambda e: e.datetime,
        reverse=reverse,
    )


def get_latest_audit_event_for_nofo(nofo):
    """
    Return the most recent audit event for this NOFO (including related Sections/Subsections),
    honoring the same filtering rules as `get_audit_events_for_nofo`.
    """
    events = get_audit_events_for_nofo(nofo, reverse=True)  # newest-first
    return events[0] if events else None
