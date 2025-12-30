import json
import re
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


def remove_model_from_description(description, model_name):
    return re.sub(
        r"\(" + re.escape(model_name) + r"\)", "", description, flags=re.IGNORECASE
    )


def format_audit_event(event, formatting_options=None):
    """
    Takes a CRUDEvent and returns a formatted dictionary for display in the UI.
    Includes enhanced labels and object details.
    """
    BASE_DOCUMENT_TYPES = ["nofo", "contentguide", "contentguideinstance"]

    def format_name(field_name):
        return " ".join(word.title() for word in field_name.split("_"))

    formatting_options = formatting_options or {}
    SubsectionModel = formatting_options.get("SubsectionModel", Subsection)
    document_display_prefix = formatting_options.get("document_display_prefix", "NOFO")

    event_details = {
        "event_id": event.id,
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
    if event.content_type.model.endswith("subsection"):
        try:
            subsection = SubsectionModel.objects.get(id=event.object_id)
            name = subsection.name or "#{}".format(subsection.order)
            event_details["object_description"] = f"{subsection.section.name} - {name}"
        except SubsectionModel.DoesNotExist:
            pass

    # Handle custom audit events
    if event.changed_fields:
        try:
            changed_fields = json.loads(event.changed_fields)
            if isinstance(changed_fields, dict):
                # Handle custom actions
                if "action" in changed_fields:
                    event_details["object_description"] = remove_model_from_description(
                        event_details["object_description"],
                        event.content_type.model,
                    )
                    action = changed_fields["action"]
                    if action == "nofo_import":
                        event_details["event_type"] = (
                            f"{document_display_prefix} imported"
                        )
                    elif action == "nofo_print":
                        event_details["event_type"] = (
                            f"{document_display_prefix} printed"
                        )
                        if "print_mode" in changed_fields:
                            event_details[
                                "event_type"
                            ] += f" ({changed_fields['print_mode'][0]} mode)"
                    elif action == "nofo_reimport":
                        event_details["event_type"] = (
                            f"{document_display_prefix} re-imported"
                        )

                # Improve object description for Nofo field changes
                elif event.content_type.model in BASE_DOCUMENT_TYPES:
                    field_name = next(iter(changed_fields.keys()))
                    event_details["object_description"] = format_name(field_name)
        except Exception:
            pass

    # Still do event object formatting for "created" (event_type == 1) events
    elif event.event_type == 1:
        if event.content_type.model in BASE_DOCUMENT_TYPES:
            # Remove '([model])' in object repr string, to ensure consistency with display name
            event_details["object_description"] = remove_model_from_description(
                event_details["object_description"],
                event.content_type.model,
            )
    return event_details


def get_audit_events_for_nofo(nofo, reverse=True):
    return get_audit_events_for_document(
        nofo,
        document_model="nofo",
        section_model="section",
        subsection_model="subsection",
        reverse=reverse,
    )


def get_audit_events_for_document(
    document, document_model, section_model, subsection_model, reverse=True
):
    """
    Return all audit events related to the given NOFO: the NOFO object,
    its sections, and its subsections.
    """

    def _filter_events(events):
        """
        Remove events that should not be displayed to the user:
            - where 'changed_fields' is null
            - where only excluded fields were changed. These are excluded because they are
                either not relevant to the user (e.g. updated, status) or can never be
                changed after initial update (e.g. filename, conditional_questions).
        """
        EXCLUDED_FIELDS = set(
            [
                "updated",
                "status",
                "hidden",
                "optional",
                "conditional_questions",
                "filename",
            ]
        )
        filtered_events = []
        for event in events:
            # Include all CREATED/DELETE events
            if event.event_type != CRUDEvent.UPDATE:
                filtered_events.append(event)
                continue

            # Exclude UPDATE events with changed fields == 'null'
            if event.changed_fields == "null" or not event.changed_fields:
                continue
            try:
                changed = json.loads(event.changed_fields or "{}")
                # Exclude UPDATE events that only changed excluded fields
                changed_keys = set(changed.keys())
                if changed_keys and changed_keys.issubset(EXCLUDED_FIELDS):
                    continue
                # Otherwise, include
                filtered_events.append(event)
            except Exception:
                # Include events we can't parse -- unexpected edge case
                filtered_events.append(event)

        return filtered_events

    # Get audit events for the NOFO
    document_events = CRUDEvent.objects.filter(
        object_id=document.id, content_type__model=document_model
    )
    document_events = _filter_events(document_events)

    # Get audit events for Sections
    section_ids = list(document.sections.values_list("id", flat=True))
    section_events = CRUDEvent.objects.filter(
        object_id__in=[str(sid) for sid in section_ids],
        content_type__model=section_model,
    )
    section_events = _filter_events(section_events)

    # Get audit events for Subsections (even if they have been deleted)
    subsection_filter = Q()
    for section_id in section_ids:
        subsection_filter |= Q(object_json_repr__contains=str(section_id))

    subsection_events = CRUDEvent.objects.filter(
        content_type__model=subsection_model
    ).filter(subsection_filter)

    subsection_events = _filter_events(subsection_events)

    # Sort and combine all events. If key datetime is the same, order by event type
    def sort_key(event):
        """
        Sort by datetime first (excluding seconds/ms), then prioritize nofo_import events.
        When datetime is equal (same minute), nofo_import actions should come first.
        """
        # Truncate datetime to minute level (exclude microseconds)
        dt_truncated = event.datetime.replace(second=0, microsecond=0)

        # For events in the same minute, sort based on custom event priority:
        # 1. nofo_import events (priority 0)
        # 2. create events
        # 3. update events
        # 4. delete events
        if event.event_type == CRUDEvent.DELETE:
            event_priority = 3
        elif event.event_type == CRUDEvent.UPDATE:
            event_priority = 2
        elif event.event_type == CRUDEvent.CREATE:
            event_priority = 1

        if event.changed_fields:
            try:
                changed_fields = json.loads(event.changed_fields)
                if (
                    isinstance(changed_fields, dict)
                    and changed_fields.get("action") == "nofo_import"
                ):
                    event_priority = 0
            except Exception:
                pass

        # Return tuple: (datetime_truncated, priority_flag)
        # Lower priority_flag means higher priority, so comes first in sorting
        return (dt_truncated, event_priority)

    combined_events = (
        list(document_events) + list(section_events) + list(subsection_events)
    )
    return sorted(combined_events, key=sort_key, reverse=reverse)


def get_audit_event_by_id(event_id):
    """
    Retrieve a CRUDEvent by its ID.
    """
    try:
        event = CRUDEvent.objects.get(id=event_id)
        return event
    except CRUDEvent.DoesNotExist:
        return None
