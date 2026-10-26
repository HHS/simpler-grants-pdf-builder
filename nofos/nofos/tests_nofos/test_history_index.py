import importlib
import json
from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from composer.models import (
    ContentGuide,
    ContentGuideInstance,
    ContentGuideSection,
    ContentGuideSubsection,
)
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import OperationalError, ProgrammingError, connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from easyaudit.models import CRUDEvent

from nofos.history_index import backfill_history_index
from nofos.models import (
    AuditObjectDocument,
    DocumentAuditEvent,
    Nofo,
    Section,
    Subsection,
)


class DocumentAuditIndexTests(TestCase):
    def setUp(self):
        self.nofo = Nofo.objects.create(
            title="History", number="TEST", group="bloom", opdiv="test-opdiv"
        )
        self.section = Section.objects.create(nofo=self.nofo, name="Section", order=1)
        self.subsection = Subsection.objects.create(
            section=self.section, name="Body", body="Text", order=1, tag="h2"
        )
        CRUDEvent.objects.all().delete()

    def event(self, model, oid, fields=None, changed=None, event_type=CRUDEvent.UPDATE):
        return CRUDEvent.objects.create(
            content_type=ContentType.objects.get_for_model(model),
            object_id=str(oid),
            object_repr="Synthetic",
            object_json_repr=json.dumps([{"fields": fields or {}}]),
            changed_fields=json.dumps(changed),
            event_type=event_type,
            datetime=timezone.now(),
        )

    def test_live_projection_has_scalar_ownership_and_visibility(self):
        event = self.event(
            Subsection,
            self.subsection.pk,
            {"section": str(self.section.pk)},
            {"body": ["old", "new"]},
        )
        index = DocumentAuditEvent.objects.get(event=event)
        self.assertEqual(index.document_id, self.nofo.pk)
        self.assertEqual(
            index.document_content_type, ContentType.objects.get_for_model(Nofo)
        )
        self.assertTrue(index.visible)
        hidden = self.event(
            Nofo,
            self.nofo.pk,
            changed={"status": ["draft", "active"], "updated": ["a", "b"]},
        )
        self.assertFalse(DocumentAuditEvent.objects.get(event=hidden).visible)
        self.assertEqual(CRUDEvent.objects.count(), 2)

    def test_null_updates_hidden_and_creates_deletes_visible(self):
        for kind, expected in [
            (CRUDEvent.UPDATE, False),
            (CRUDEvent.CREATE, True),
            (CRUDEvent.DELETE, True),
        ]:
            event = self.event(Nofo, self.nofo.pk, event_type=kind)
            self.assertEqual(
                DocumentAuditEvent.objects.get(event=event).visible, expected
            )

    def test_saving_existing_event_refreshes_index_without_duplicate(self):
        event = self.event(Nofo, self.nofo.pk, changed={"status": ["draft", "active"]})
        event.changed_fields = json.dumps({"title": ["old", "new"]})
        event.datetime += timedelta(days=1)
        event.save(update_fields=["datetime", "changed_fields"])
        index = DocumentAuditEvent.objects.get(event=event)
        self.assertTrue(index.visible)
        self.assertEqual(index.datetime, event.datetime)
        self.assertEqual(DocumentAuditEvent.objects.filter(event=event).count(), 1)

    def test_installed_schema_does_not_hide_database_errors(self):
        for error_type in (OperationalError, ProgrammingError):
            with self.subTest(error_type=error_type):
                with patch(
                    "nofos.history_index.HistoryIndexer.index",
                    side_effect=error_type("synthetic failure"),
                ):
                    with self.assertRaisesMessage(error_type, "synthetic failure"):
                        self.event(
                            Nofo, self.nofo.pk, changed={"title": ["old", "new"]}
                        )

    def test_installed_schema_does_not_hide_delete_database_errors(self):
        with patch(
            "nofos.history_index.HistoryIndexer.remember",
            side_effect=OperationalError("synthetic delete failure"),
        ):
            with self.assertRaisesMessage(OperationalError, "synthetic delete failure"):
                self.section.delete()

    def test_delete_keeps_parent_association_without_live_section(self):
        section_id, subsection_id = self.section.pk, self.subsection.pk
        self.section.delete()
        self.assertTrue(
            AuditObjectDocument.objects.filter(
                object_id=section_id, document_id=self.nofo.pk
            ).exists()
        )
        event = self.event(
            Subsection,
            subsection_id,
            {"section": str(section_id)},
            event_type=CRUDEvent.DELETE,
        )
        self.assertEqual(
            DocumentAuditEvent.objects.get(event=event).document_id, self.nofo.pk
        )

    def test_composer_and_writer_share_children_but_not_root(self):
        guide = ContentGuide.objects.create(
            title="Guide", group="bloom", opdiv="test-opdiv"
        )
        draft = ContentGuideInstance.objects.create(
            title="Draft", group="bloom", parent=guide, opdiv="test-opdiv"
        )
        for document, field in [
            (guide, "content_guide"),
            (draft, "content_guide_instance"),
        ]:
            section = ContentGuideSection.objects.create(
                **{field: document}, name="Section", order=1
            )
            subsection = ContentGuideSubsection.objects.create(
                section=section, name="Body", body="Text", order=1, tag="h2"
            )
            event = self.event(
                ContentGuideSubsection,
                subsection.pk,
                {"section": str(section.pk)},
                {"body": ["old", "new"]},
            )
            index = DocumentAuditEvent.objects.get(event=event)
            self.assertEqual(index.document_id, document.pk)
            self.assertEqual(
                index.document_content_type,
                ContentType.objects.get_for_model(type(document)),
            )

    def test_backfill_recovers_deleted_section_from_snapshot(self):
        section_id, subsection_id = self.section.pk, self.subsection.pk
        section_event = self.event(
            Section,
            section_id,
            {"nofo": str(self.nofo.pk)},
            event_type=CRUDEvent.CREATE,
        )
        child_event = self.event(
            Subsection,
            subsection_id,
            {"section": str(section_id)},
            {"name": ["old", "new"]},
        )
        self.section.delete()
        DocumentAuditEvent.objects.all().delete()
        AuditObjectDocument.objects.all().delete()
        result = backfill_history_index(chunk_size=1)
        self.assertEqual(result, {"indexed": 2, "unresolved": 0})
        self.assertEqual(
            set(DocumentAuditEvent.objects.values_list("event_id", flat=True)),
            {section_event.pk, child_event.pk},
        )
        self.assertEqual(backfill_history_index(chunk_size=1), result)
        self.assertEqual(DocumentAuditEvent.objects.count(), 2)

    def test_frozen_migration_recovers_deleted_children_and_keeps_raw_events(self):
        section_id, subsection_id = self.section.pk, self.subsection.pk
        self.event(
            Section,
            section_id,
            {"nofo": str(self.nofo.pk)},
            event_type=CRUDEvent.CREATE,
        )
        self.event(
            Subsection,
            subsection_id,
            {"section": str(section_id)},
            {"body": ["old", "new"]},
        )
        self.section.delete()
        DocumentAuditEvent.objects.all().delete()
        AuditObjectDocument.objects.all().delete()
        before = list(CRUDEvent.objects.values())
        migration = importlib.import_module(
            "nofos.migrations.0155_backfill_document_audit_index"
        )
        migration.backfill(apps, SimpleNamespace(connection=connection))
        self.assertEqual(DocumentAuditEvent.objects.count(), 2)
        self.assertEqual(before, list(CRUDEvent.objects.values()))

    def test_unresolved_or_unrelated_events_never_get_guessed_root(self):
        missing = self.event(
            Subsection, uuid4(), {"section": str(uuid4())}, {"name": ["a", "b"]}
        )
        self.assertFalse(DocumentAuditEvent.objects.filter(event=missing).exists())
        result = backfill_history_index(chunk_size=1)
        self.assertEqual(result["unresolved"], 1)

    def test_runtime_backfill_uses_live_section_when_deleted_child_has_no_mapping(self):
        child_id = self.subsection.pk
        self.subsection.delete()
        AuditObjectDocument.objects.all().delete()
        CRUDEvent.objects.bulk_create(
            [
                CRUDEvent(
                    content_type=ContentType.objects.get_for_model(Subsection),
                    object_id=str(child_id),
                    object_json_repr=json.dumps(
                        [{"fields": {"section": str(self.section.pk)}}]
                    ),
                    changed_fields='{"body": ["before", "after"]}',
                    event_type=CRUDEvent.UPDATE,
                )
            ]
        )
        self.assertEqual(backfill_history_index(), {"indexed": 1, "unresolved": 0})
        self.assertEqual(DocumentAuditEvent.objects.get().document_id, self.nofo.pk)

    def test_event_deletion_removes_projection_not_object_association(self):
        event = self.event(
            Subsection,
            self.subsection.pk,
            {"section": str(self.section.pk)},
            {"body": ["a", "b"]},
        )
        event.delete()
        self.assertFalse(DocumentAuditEvent.objects.exists())
        self.assertTrue(
            AuditObjectDocument.objects.filter(object_id=self.subsection.pk).exists()
        )

    def test_post_rollout_command_catches_events_written_without_new_hooks(self):
        # Simulate an old worker inserting after the migration's read snapshot.
        event = CRUDEvent(
            content_type=ContentType.objects.get_for_model(Subsection),
            object_id=str(self.subsection.pk),
            object_json_repr=json.dumps(
                [{"fields": {"section": str(self.section.pk)}}]
            ),
            changed_fields='{"body": ["old", "new"]}',
            event_type=CRUDEvent.UPDATE,
        )
        CRUDEvent.objects.bulk_create([event])
        self.assertFalse(DocumentAuditEvent.objects.filter(event=event).exists())
        output = StringIO()
        call_command("backfill_document_audit_index", stdout=output)
        self.assertEqual(
            DocumentAuditEvent.objects.get(event=event).document_id, self.nofo.pk
        )
        call_command("backfill_document_audit_index", stdout=output)
        self.assertEqual(DocumentAuditEvent.objects.filter(event=event).count(), 1)
        self.assertIn("0 unresolved ownership", output.getvalue())

    def test_deployment_migration_does_not_run_the_historical_backfill(self):
        migration = importlib.import_module(
            "nofos.migrations.0155_backfill_document_audit_index"
        )
        self.assertEqual(migration.Migration.operations, [])

    def test_completeness_check_is_read_only_and_fails_for_unindexed_events(self):
        event = self.event(Nofo, self.nofo.pk, changed={"title": ["old", "new"]})
        DocumentAuditEvent.objects.all().delete()
        before = list(CRUDEvent.objects.values())
        with self.assertRaisesMessage(CommandError, "1 events missing"):
            call_command("backfill_document_audit_index", check=True)
        self.assertFalse(DocumentAuditEvent.objects.exists())
        self.assertEqual(before, list(CRUDEvent.objects.values()))
        call_command("backfill_document_audit_index", stdout=StringIO())
        output = StringIO()
        call_command("backfill_document_audit_index", check=True, stdout=output)
        self.assertIn("0 events missing", output.getvalue())
        self.assertTrue(DocumentAuditEvent.objects.filter(event=event).exists())

    def test_real_audit_callbacks_after_cascade_keep_deleted_child_history(self):
        child_id = self.subsection.pk
        with self.captureOnCommitCallbacks(execute=True):
            self.section.delete()
        deleted_events = CRUDEvent.objects.filter(
            content_type=ContentType.objects.get_for_model(Subsection),
            object_id=str(child_id),
            event_type=CRUDEvent.DELETE,
        )
        self.assertTrue(deleted_events.exists())
        self.assertEqual(
            DocumentAuditEvent.objects.filter(
                event__in=deleted_events, document_id=self.nofo.pk
            ).count(),
            deleted_events.count(),
        )


class DocumentAuditMissingSchemaTests(TransactionTestCase):
    def test_partial_prior_rollout_finishes_without_backfilling_or_changing_events(
        self,
    ):
        content_type = ContentType.objects.get_for_model(Nofo)
        event = CRUDEvent.objects.create(
            content_type=content_type,
            object_id=str(uuid4()),
            object_repr="Synthetic pre-rollout event",
            object_json_repr="[]",
            changed_fields='{"title": ["before", "after"]}',
            event_type=CRUDEvent.UPDATE,
        )
        DocumentAuditEvent.objects.all().delete()
        original = list(CRUDEvent.objects.values())
        recorder = MigrationRecorder(connection)
        loader = MigrationLoader(connection)
        # Simulate a partial rollout without leaving applied descendants whose
        # dependency has been removed from migration history (including merges).
        applied = [
            node
            for node in loader.graph.backwards_plan(
                ("nofos", "0155_backfill_document_audit_index")
            )
            if node in loader.applied_migrations
        ]
        for node in applied:
            recorder.record_unapplied(*node)
        try:
            call_command(
                "migrate", "nofos", "0155_backfill_document_audit_index", verbosity=0
            )
            self.assertFalse(DocumentAuditEvent.objects.filter(event=event).exists())
            self.assertEqual(original, list(CRUDEvent.objects.values()))
            call_command("backfill_document_audit_index", stdout=StringIO())
            self.assertTrue(DocumentAuditEvent.objects.filter(event=event).exists())
            call_command("backfill_document_audit_index", check=True, stdout=StringIO())
        finally:
            for node in reversed(applied):
                recorder.record_applied(*node)

    def test_real_missing_projection_table_preserves_original_audit_insert(self):
        content_type = ContentType.objects.get_for_model(Nofo)
        # Exercise actual missing-table SQL, as old-schema migrations can save
        # live audit events before either projection table has been created.
        for model in (DocumentAuditEvent, AuditObjectDocument):
            with self.subTest(model=model.__name__):
                with connection.schema_editor() as editor:
                    editor.delete_model(model)
                try:
                    event = CRUDEvent.objects.create(
                        content_type=content_type,
                        object_id=str(uuid4()),
                        object_repr="Synthetic migration audit",
                        object_json_repr="[]",
                        changed_fields="null",
                        event_type=CRUDEvent.CREATE,
                        datetime=timezone.now(),
                    )
                    self.assertTrue(CRUDEvent.objects.filter(pk=event.pk).exists())
                    self.assertGreaterEqual(CRUDEvent.objects.count(), 1)
                finally:
                    with connection.schema_editor() as editor:
                        editor.create_model(model)
