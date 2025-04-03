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
