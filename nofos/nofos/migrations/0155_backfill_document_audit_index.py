"""Retired deployment-time backfill, retained for migration-history compatibility.

The frozen helper records the original algorithm but operations is intentionally
empty. Run the separate management command after rollout instead of scanning the
audit log during deployment. Original audit records are never modified.
"""

import json
from uuid import UUID

from django.db import migrations


def backfill(apps, schema_editor):
    alias = schema_editor.connection.alias
    Mapping = apps.get_model("nofos", "AuditObjectDocument").objects.using(alias)
    Index = apps.get_model("nofos", "DocumentAuditEvent").objects.using(alias)
    Event = apps.get_model("easyaudit", "CRUDEvent").objects.using(alias)
    types = {
        (ct.app_label, ct.model): ct.pk
        for ct in apps.get_model("contenttypes", "ContentType")
        .objects.using(alias)
        .all()
    }
    roots = {
        ("nofos", "nofo"),
        ("composer", "contentguide"),
        ("composer", "contentguideinstance"),
    }
    sections = {("nofos", "section"), ("composer", "contentguidesection")}
    subsections = {("nofos", "subsection"), ("composer", "contentguidesubsection")}
    excluded = {
        "updated",
        "status",
        "hidden",
        "optional",
        "conditional_questions",
        "filename",
    }

    ownership_cache = {}

    def uuid(value):
        try:
            return UUID(str(value))
        except (ValueError, TypeError, AttributeError):
            return None

    def fields(event):
        try:
            result = json.loads(event.object_json_repr)[0]["fields"]
            return result if isinstance(result, dict) else {}
        except (ValueError, TypeError, KeyError, IndexError):
            return {}

    def remember(ct, oid, root):
        if oid and root:
            if lookup(ct, oid) != root:
                Mapping.update_or_create(
                    content_type_id=ct,
                    object_id=oid,
                    defaults={
                        "document_content_type_id": root[0],
                        "document_id": root[1],
                    },
                )
            if len(ownership_cache) >= 4096:
                ownership_cache.clear()
            ownership_cache[(ct, oid)] = root

    def lookup(ct, oid):
        if not uuid(oid):
            return None
        if (ct, uuid(oid)) in ownership_cache:
            return ownership_cache[(ct, uuid(oid))]
        return (
            Mapping.filter(content_type_id=ct, object_id=uuid(oid))
            .values_list("document_content_type_id", "document_id")
            .first()
        )

    # Seed live section ownership, then recover sections removed by reimports
    # from their serialized audit snapshots. No subsection bodies are scanned in
    # this pass and all reads use a bounded database cursor.
    for key in sections:
        for section in (
            apps.get_model(*key).objects.using(alias).all().iterator(chunk_size=100)
        ):
            parent_fields = (
                [("nofo_id", ("nofos", "nofo"))]
                if key[0] == "nofos"
                else [
                    ("content_guide_id", ("composer", "contentguide")),
                    ("content_guide_instance_id", ("composer", "contentguideinstance")),
                ]
            )
            for name, root_key in parent_fields:
                parent_id = getattr(section, name)
                if parent_id and root_key in types:
                    remember(types[key], section.pk, (types[root_key], parent_id))
    section_types = [types[key] for key in sections if key in types]
    for event in (
        Event.filter(content_type_id__in=section_types)
        .select_related("content_type")
        .order_by("pk")
        .iterator(chunk_size=100)
    ):
        data = fields(event)
        parents = (
            [("nofo", ("nofos", "nofo"))]
            if event.content_type.app_label == "nofos"
            else [
                ("content_guide", ("composer", "contentguide")),
                ("content_guide_instance", ("composer", "contentguideinstance")),
            ]
        )
        for name, root_key in parents:
            parent_id = uuid(data.get(name))
            if parent_id and root_key in types:
                remember(
                    event.content_type_id,
                    uuid(event.object_id),
                    (types[root_key], parent_id),
                )

    pending = []
    unresolved = indexed = 0
    relevant_types = [
        types[key] for key in roots | sections | subsections if key in types
    ]
    for event in (
        Event.filter(content_type_id__in=relevant_types)
        .select_related("content_type")
        .order_by("pk")
        .iterator(chunk_size=100)
    ):
        key = (event.content_type.app_label, event.content_type.model)
        oid = uuid(event.object_id)
        root = None
        if oid and key in roots:
            root = (event.content_type_id, oid)
        elif key in sections:
            root = lookup(event.content_type_id, oid)
        elif key in subsections:
            section_type = types.get(
                (key[0], "section" if key[0] == "nofos" else "contentguidesection")
            )
            root = lookup(section_type, fields(event).get("section"))
            if not root:
                root = lookup(event.content_type_id, oid)
            if not root and oid:
                instance = (
                    apps.get_model(*key)
                    .objects.using(alias)
                    .filter(pk=oid)
                    .values_list("section_id", flat=True)
                    .first()
                )
                root = lookup(section_type, instance)
        if not root:
            unresolved += 1
            continue
        remember(event.content_type_id, oid, root)
        visible = event.event_type != 2
        if (
            event.event_type == 2
            and event.changed_fields
            and event.changed_fields != "null"
        ):
            try:
                changed = json.loads(event.changed_fields)
            except (ValueError, TypeError):
                changed = {}
            keys = set(changed) if isinstance(changed, dict) else set()
            visible = not (keys and keys.issubset(excluded))
        pending.append(
            Index.model(
                event_id=event.pk,
                document_content_type_id=root[0],
                document_id=root[1],
                datetime=event.datetime,
                visible=visible,
            )
        )
        indexed += 1
        if len(pending) >= 100:
            Index.bulk_create(pending, ignore_conflicts=True, batch_size=100)
            pending.clear()
    if pending:
        Index.bulk_create(pending, ignore_conflicts=True, batch_size=100)
    print(
        f"Document audit index: {indexed} indexed, {unresolved} unresolved ownership."
    )


class Migration(migrations.Migration):
    atomic = False
    dependencies = [
        ("nofos", "0154_document_audit_index"),
        ("composer", "0013_alter_contentguide_group_and_more"),
    ]
    # Retired during restoration after #1166: never scan historical events as
    # part of deployment. Keep this migration identity/dependencies so databases
    # that applied 0154 or both original migrations retain a compatible graph.
    # The frozen helper above is historical reference, not a migration operation.
    # Use backfill_document_audit_index after all old workers have stopped.
    operations = []
