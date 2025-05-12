import json
from collections import OrderedDict

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


def get_audit_events_for_nofo(nofo, reverse=True):
    """
    Return all audit events related to the given NOFO: the NOFO object,
    its sections, and its subsections.
    """

    def _filter_updated_events(events):
        """Remove events where only the 'updated' field changed."""
        filtered_events = []
        for event in events:
            if event.event_type != CRUDEvent.UPDATE:
                filtered_events.append(event)
                continue
            try:
                changed = json.loads(event.changed_fields or "{}")
                if not (
                    changed.keys() == {"updated"} or list(changed.keys()) == ["updated"]
                ):
                    filtered_events.append(event)
            except Exception:
                filtered_events.append(event)
        return filtered_events

    # Get audit events for the NOFO
    nofo_events = CRUDEvent.objects.filter(
        object_id=nofo.id, content_type__model="nofo"
    )
    nofo_events = _filter_updated_events(nofo_events)

    # Get audit events for Sections
    section_ids = list(nofo.sections.values_list("id", flat=True))
    section_events = CRUDEvent.objects.filter(
        object_id__in=[str(sid) for sid in section_ids],
        content_type__model="section",
    )

    # Get audit events for Subsections
    subsection_ids = list(
        Subsection.objects.filter(section__nofo=nofo).values_list("id", flat=True)
    )
    subsection_events = CRUDEvent.objects.filter(
        object_id__in=[str(sid) for sid in subsection_ids],
        content_type__model="subsection",
    )

    return sorted(
        list(nofo_events) + list(section_events) + list(subsection_events),
        key=lambda e: e.datetime,
        reverse=reverse,
    )
