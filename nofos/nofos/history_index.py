"""Index audit ownership once, rather than searching document snapshots on reads.

The frozen migration seeds the same scalar projection maintained by live
signals. ``backfill_history_index`` fills missing rows after bulk audit inserts;
history requests never scan or repair the global audit log. Original records
are normally read-only, but saving an existing event also refreshes its index.
"""

import json
from collections import OrderedDict
from uuid import UUID

from django.apps import apps as live_apps
from django.db import OperationalError, ProgrammingError, connections, transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from easyaudit.models import CRUDEvent

ROOTS = {
    ("nofos", "nofo"),
    ("composer", "contentguide"),
    ("composer", "contentguideinstance"),
}
SECTIONS = {("nofos", "section"), ("composer", "contentguidesection")}
SUBSECTIONS = {("nofos", "subsection"), ("composer", "contentguidesubsection")}
EXCLUDED_FIELDS = {
    "updated",
    "status",
    "hidden",
    "optional",
    "conditional_questions",
    "filename",
}


def event_is_visible(event):
    if event.event_type != CRUDEvent.UPDATE:
        return True
    if not event.changed_fields or event.changed_fields == "null":
        return False
    try:
        changed = json.loads(event.changed_fields)
    except (TypeError, ValueError):
        changed = {}
    keys = set(changed) if isinstance(changed, dict) else set()
    return not (keys and keys.issubset(EXCLUDED_FIELDS))


def _uuid(value):
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _fields(event):
    try:
        data = json.loads(event.object_json_repr)
        fields = data[0]["fields"]
        return fields if isinstance(fields, dict) else {}
    except (ValueError, TypeError, KeyError, IndexError):
        return {}


class HistoryIndexer:
    def __init__(self, apps=live_apps, using="default"):
        self.apps = apps
        self.using = using
        self.mapping = apps.get_model("nofos", "AuditObjectDocument").objects.using(
            using
        )
        self.events = apps.get_model("nofos", "DocumentAuditEvent").objects.using(using)
        self.cache = OrderedDict()
        self.types = {
            (ct.app_label, ct.model): ct.pk
            for ct in apps.get_model("contenttypes", "ContentType")
            .objects.using(using)
            .filter(app_label__in=["nofos", "composer"])
        }

    def remember(self, content_type_id, object_id, root):
        object_id = _uuid(object_id)
        if object_id and root:
            key = (content_type_id, object_id)
            if self.lookup(content_type_id, object_id) != root:
                self.mapping.update_or_create(
                    content_type_id=content_type_id,
                    object_id=object_id,
                    defaults={
                        "document_content_type_id": root[0],
                        "document_id": root[1],
                    },
                )
            self.cache[key] = root
            self.cache.move_to_end(key)
            if len(self.cache) > 4096:
                self.cache.popitem(last=False)
        return root

    def lookup(self, content_type_id, object_id):
        object_id = _uuid(object_id)
        if not object_id:
            return None
        key = (content_type_id, object_id)
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        root = (
            self.mapping.filter(content_type_id=content_type_id, object_id=object_id)
            .values_list("document_content_type_id", "document_id")
            .first()
        )
        return root

    def root_for(self, content_type, object_id, fields):
        key = (content_type.app_label, content_type.model)
        object_id = _uuid(object_id)
        if key in ROOTS:
            return (content_type.pk, object_id) if object_id else None
        if key in SECTIONS:
            parent_fields = (
                [("nofo", ("nofos", "nofo"))]
                if key[0] == "nofos"
                else [
                    ("content_guide", ("composer", "contentguide")),
                    ("content_guide_instance", ("composer", "contentguideinstance")),
                ]
            )
            for name, parent_key in parent_fields:
                parent_id = _uuid(fields.get(name))
                parent_type = self.types.get(parent_key)
                if parent_id and parent_type:
                    return (parent_type, parent_id)
        if key in SUBSECTIONS:
            section_type = self.types.get(
                (key[0], "section" if key[0] == "nofos" else "contentguidesection")
            )
            root = self.lookup(section_type, fields.get("section"))
            if root:
                return root
        # Snapshots may be missing in custom events. A durable mapping outlives
        # the object; live models are a final fallback, not a history read path.
        root = self.lookup(content_type.pk, object_id)
        if root:
            return root
        if object_id and key in SECTIONS | SUBSECTIONS:
            model = self.apps.get_model(*key)
            instance = model.objects.using(self.using).filter(pk=object_id).first()
            if instance:
                return self.root_for_instance(instance)
        return None

    def root_for_instance(self, instance):
        key = (instance._meta.app_label, instance._meta.model_name)
        if key in ROOTS:
            return (self.types[key], instance.pk)
        if key in SECTIONS:
            parent_fields = (
                [("nofo_id", ("nofos", "nofo"))]
                if key[0] == "nofos"
                else [
                    ("content_guide_id", ("composer", "contentguide")),
                    ("content_guide_instance_id", ("composer", "contentguideinstance")),
                ]
            )
            for name, parent_key in parent_fields:
                parent_id = getattr(instance, name, None)
                if parent_id:
                    return (self.types[parent_key], parent_id)
            return None
        if key in SUBSECTIONS:
            section = instance.section
            root = self.root_for_instance(section)
            return self.remember(
                self.types[(section._meta.app_label, section._meta.model_name)],
                section.pk,
                root,
            )
        return None

    def index(self, event, pending=None):
        key = (event.content_type.app_label, event.content_type.model)
        if key not in ROOTS | SECTIONS | SUBSECTIONS:
            return False
        root = self.root_for(event.content_type, event.object_id, _fields(event))
        if not root:
            return False
        self.remember(event.content_type_id, event.object_id, root)
        values = {
            "document_content_type_id": root[0],
            "document_id": root[1],
            "datetime": event.datetime,
            "visible": event_is_visible(event),
        }
        if pending is None:
            self.events.update_or_create(event_id=event.pk, defaults=values)
        else:
            pending.append(self.events.model(event_id=event.pk, **values))
        return True


def backfill_history_index(apps=live_apps, using="default", chunk_size=100):
    """Idempotent, bounded-memory backfill, with section ownership resolved first."""
    indexer = HistoryIndexer(apps, using)
    Event = apps.get_model("easyaudit", "CRUDEvent")
    events = Event.objects.using(using).select_related("content_type").order_by("pk")
    # A surviving section can resolve an old deleted child even when its own
    # audit snapshots are absent (for example after a bulk historical import).
    for key in SECTIONS:
        if key not in indexer.types:
            continue
        for section in (
            apps.get_model(*key).objects.using(using).iterator(chunk_size=chunk_size)
        ):
            indexer.remember(
                indexer.types[key], section.pk, indexer.root_for_instance(section)
            )
    section_types = [indexer.types[key] for key in SECTIONS if key in indexer.types]
    # Recover deleted section ownership from its own historical snapshots before
    # processing subsection events, including events with no surviving section.
    for event in events.filter(content_type_id__in=section_types).iterator(
        chunk_size=chunk_size
    ):
        root = indexer.root_for(event.content_type, event.object_id, _fields(event))
        indexer.remember(event.content_type_id, event.object_id, root)
    relevant_types = [
        indexer.types[key]
        for key in ROOTS | SECTIONS | SUBSECTIONS
        if key in indexer.types
    ]
    indexed = unresolved = 0
    pending = []
    for event in events.filter(content_type_id__in=relevant_types).iterator(
        chunk_size=chunk_size
    ):
        if indexer.index(event, pending):
            indexed += 1
        else:
            unresolved += 1
        if len(pending) >= chunk_size:
            indexer.events.bulk_create(
                pending, ignore_conflicts=True, batch_size=chunk_size
            )
            pending.clear()
    if pending:
        indexer.events.bulk_create(
            pending, ignore_conflicts=True, batch_size=chunk_size
        )
    return {"indexed": indexed, "unresolved": unresolved}


def _maintain_projection(using, callback):
    """Keep old-schema migrations from breaking the original audit write.

    Historical model migrations can cause easy-audit to save a *live*
    CRUDEvent before our projection tables exist. Isolate the projection in a
    savepoint, and suppress only when schema inspection confirms that state.
    Real errors with an installed schema must still propagate.
    """
    try:
        with transaction.atomic(using=using):
            return callback()
    except (OperationalError, ProgrammingError):
        tables = set(connections[using].introspection.table_names())
        required = {
            live_apps.get_model("nofos", name)._meta.db_table
            for name in ("AuditObjectDocument", "DocumentAuditEvent")
        }
        if required.issubset(tables):
            raise
        return None


@receiver(post_save, sender=CRUDEvent)
def index_audit_event(sender, instance, created, raw, using, **kwargs):
    if not raw:
        _maintain_projection(using, lambda: HistoryIndexer(using=using).index(instance))


@receiver(pre_delete)
def remember_deleted_object(sender, instance, using, **kwargs):
    if sender._meta.apps is not live_apps:
        return
    key = (sender._meta.app_label, sender._meta.model_name)
    if key in ROOTS | SECTIONS | SUBSECTIONS:

        def remember():
            indexer = HistoryIndexer(using=using)
            indexer.remember(
                indexer.types[key], instance.pk, indexer.root_for_instance(instance)
            )

        _maintain_projection(using, remember)
