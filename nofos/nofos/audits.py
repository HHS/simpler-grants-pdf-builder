import json
import re
import uuid
from collections import OrderedDict

from django.contrib.contenttypes.models import ContentType
from easyaudit.models import CRUDEvent

from .models import DocumentAuditEvent, Subsection


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
        event_details["object_exists"] = False
        try:
            if "subsections" in formatting_options:
                subsection = formatting_options["subsections"].get(event.object_id)
                if subsection is None:
                    raise SubsectionModel.DoesNotExist
            else:
                subsection = SubsectionModel.objects.select_related("section").get(
                    id=event.object_id
                )
            name = subsection.name or "#{}".format(subsection.order)
            event_details["object_description"] = f"{subsection.section.name} - {name}"
            event_details["object_exists"] = True
        except SubsectionModel.DoesNotExist:
            pass

    # Handle custom audit events
    changed_fields = safe_get_changed_fields(event)
    if changed_fields:
        event_details["changed_fields"] = changed_fields
        if isinstance(changed_fields, dict):
            # Handle custom actions
            if "action" in changed_fields:
                event_details["object_description"] = remove_model_from_description(
                    event_details["object_description"],
                    event.content_type.model,
                )
                action = changed_fields["action"]
                if action == "nofo_import":
                    event_details["event_type"] = f"{document_display_prefix} imported"
                elif action == "nofo_print":
                    event_details["event_type"] = f"{document_display_prefix} printed"
                    if "print_mode" in changed_fields:
                        event_details[
                            "event_type"
                        ] += f" ({changed_fields['print_mode'][0]} mode)"
                elif action == "nofo_reimport":
                    event_details["event_type"] = (
                        f"{document_display_prefix} re-imported"
                    )

            # Improve object description for Nofo field changes if changed_fields is not empty
            elif event.content_type.model in BASE_DOCUMENT_TYPES:
                field_name = next(iter(changed_fields.keys()))
                event_details["object_description"] = format_name(field_name)

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


def document_audit_entries(document, reverse=True):
    """Indexed, payload-free scope shared by paginated and full-history consumers."""
    content_type = ContentType.objects.get_for_model(document)
    ordering = ("-datetime", "-event_id") if reverse else ("datetime", "event_id")
    return DocumentAuditEvent.objects.filter(
        document_content_type=content_type, document_id=document.pk, visible=True
    ).order_by(*ordering)


def _load_audit_events(event_ids):
    events = CRUDEvent.objects.select_related("content_type", "user").in_bulk(event_ids)
    return [events[event_id] for event_id in event_ids if event_id in events]


def get_audit_events_page(document, offset=0, limit=25):
    """Load only one page plus a lookahead, never the document's complete payloads."""
    ids = list(
        document_audit_entries(document).values_list("event_id", flat=True)[
            offset : offset + limit + 1
        ]
    )
    return _load_audit_events(ids)


def get_audit_events_for_document(
    document, document_model, section_model, subsection_model, reverse=True
):
    """Full history for explicit full-history consumers, without global JSON searches.

    Model-name arguments remain for compatibility. The actual document content type
    scopes ownership, including the separate Composer and Writer document families.
    Interactive history pages must use get_audit_events_page instead.
    """
    return _load_audit_events(
        list(
            document_audit_entries(document, reverse=reverse).values_list(
                "event_id", flat=True
            )
        )
    )


def audit_event_formatting_options(events, options=None):
    """Batch live subsection labels; deleted objects retain their audit description."""
    options = dict(options or {})
    subsection_model = options.get("SubsectionModel", Subsection)
    ids = [
        event.object_id
        for event in events
        if event.content_type.model == subsection_model._meta.model_name
    ]
    # Audit object IDs are strings. Invalid historical IDs must not break the page.
    valid_ids = []
    for object_id in ids:
        try:
            valid_ids.append(uuid.UUID(object_id))
        except (ValueError, TypeError, AttributeError):
            continue
    options["subsections"] = {
        str(subsection.pk): subsection
        for subsection in subsection_model.objects.select_related("section").filter(
            pk__in=valid_ids
        )
    }
    return options


def get_audit_event_by_id(event_id):
    """
    Retrieve a CRUDEvent by its ID.
    """
    try:
        event = CRUDEvent.objects.get(id=event_id)
        return event
    except CRUDEvent.DoesNotExist:
        return None


def safe_get_changed_fields(event):
    """
    Safely parse the changed_fields of a CRUDEvent.
    Returns an empty dict if parsing fails.
    """
    try:
        changed = json.loads(event.changed_fields) if event.changed_fields else {}
        return changed if isinstance(changed, dict) else {}
    except Exception:
        return {}
