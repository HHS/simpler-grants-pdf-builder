import json
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone
from easyaudit.models import CRUDEvent

from nofos.models import Nofo, Section, Subsection

from ..audits import (
    deduplicate_audit_events_by_day_and_object,
    format_audit_event,
    get_audit_events_for_nofo,
)


class DeduplicateAuditEventsTests(TestCase):
    def setUp(self):
        base_time = datetime(2025, 4, 1, 12, 0, 0)

        self.events = [
            {
                "object_type": "Subsection",
                "object_description": "Step 1 - Key facts",
                "timestamp": base_time,
            },
            {
                "object_type": "Subsection",
                "object_description": "Step 1 - Key facts",
                "timestamp": base_time + timedelta(hours=1),  # same day, should replace
            },
            {
                "object_type": "Subsection",
                "object_description": "Step 1 - Key facts",
                "timestamp": base_time + timedelta(days=1),  # next day, keep
            },
            {
                "object_type": "Nofo",
                "object_description": "Application Deadline",
                "timestamp": base_time,
            },
            {
                "object_type": "Nofo",
                "object_description": "Application Deadline",
                "timestamp": base_time
                + timedelta(minutes=30),  # same day, should replace
            },
        ]

    def test_deduplicates_by_object_and_date(self):
        deduped = deduplicate_audit_events_by_day_and_object(self.events)

        # Expect only 3 results:
        # - One for "Step 1 - Key facts" on April 1 (latest one)
        # - One for "Step 1 - Key facts" on April 2
        # - One for "Application Deadline" on April 1 (latest one)
        self.assertEqual(len(deduped), 3)

        key_facts_april1 = next(
            e
            for e in deduped
            if e["object_description"] == "Step 1 - Key facts"
            and e["timestamp"].date() == datetime(2025, 4, 1).date()
        )
        self.assertEqual(key_facts_april1["timestamp"].hour, 13)

        app_deadline = next(
            e for e in deduped if e["object_description"] == "Application Deadline"
        )
        self.assertEqual(app_deadline["timestamp"].minute, 30)

    def test_empty_event_list(self):
        deduped = deduplicate_audit_events_by_day_and_object([])
        self.assertEqual(deduped, [])

    def test_single_event(self):
        single = self.events[:1]
        deduped = deduplicate_audit_events_by_day_and_object(single)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0], single[0])


class FormatAuditEventTests(TestCase):
    def setUp(self):
        self.nofo = Nofo.objects.create(
            title="Test NOFO", group="bloom", opdiv="Test OpDiv"
        )
        self.section = Section.objects.create(
            nofo=self.nofo, name="Section 1", html_id="sec-1", order=1
        )
        self.subsection = Subsection.objects.create(
            section=self.section, name="Subsection 1", order=1, tag="h3"
        )

        self.nofo_ct = ContentType.objects.get_for_model(Nofo)
        self.section_ct = ContentType.objects.get_for_model(Section)
        self.subsection_ct = ContentType.objects.get_for_model(Subsection)

    def create_event(
        self, obj, content_type, changed_fields=None, event_type=CRUDEvent.UPDATE
    ):
        return CRUDEvent.objects.create(
            object_id=str(obj.id),
            content_type=content_type,
            event_type=event_type,
            changed_fields=json.dumps(changed_fields or {}),
            object_repr=str(obj),
            object_json_repr=json.dumps(
                [{"fields": {"html_id": getattr(obj, "html_id", "")}}]
            ),
            user=None,
            datetime=timezone.now(),
        )

    def test_format_subsection_event(self):
        event = self.create_event(
            self.subsection, self.subsection_ct, {"body": ["Old", "New"]}
        )
        formatted = format_audit_event(event)

        self.assertEqual(formatted["object_type"], "Subsection")
        self.assertEqual(formatted["object_description"], "Section 1 - Subsection 1")
        self.assertEqual(formatted["event_type"], "Update")
        self.assertEqual(formatted["object_html_id"], "1--section-1--subsection-1")

    def test_format_nofo_field_update(self):
        event = self.create_event(self.nofo, self.nofo_ct, {"title": ["Old", "New"]})
        formatted = format_audit_event(event)

        self.assertEqual(formatted["object_type"], "Nofo")
        self.assertEqual(formatted["object_description"], "Title")

    def test_format_custom_action_event(self):
        event = self.create_event(
            self.nofo,
            self.nofo_ct,
            {"action": "nofo_print", "print_mode": ["full", "full"]},
        )
        formatted = format_audit_event(event)

        self.assertEqual(formatted["event_type"], "NOFO printed (full mode)")

    def test_handles_missing_html_id_gracefully(self):
        # nofo object does not have an HTML ID
        event = self.create_event(
            self.nofo, self.nofo_ct, {"status": ["draft", "published"]}
        )
        event.save()

        formatted = format_audit_event(event)
        self.assertEqual(formatted["object_html_id"], "")

    def test_non_json_changed_fields_does_not_crash(self):
        event = self.create_event(self.nofo, self.nofo_ct)
        event.changed_fields = "not-json"
        event.save()

        formatted = format_audit_event(event)
        self.assertEqual(formatted["event_type"], "Update")


class GetAuditEventsForNofoTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.nofo = Nofo.objects.create(
            title="Test NOFO", group="bloom", opdiv="Test OpDiv"
        )
        self.section = Section.objects.create(
            nofo=self.nofo, name="Section 1", html_id="sec-1", order=1
        )
        self.subsection = Subsection.objects.create(
            section=self.section, name="Subsection 1", order=1, tag="h3"
        )

        self.nofo_ct = ContentType.objects.get_for_model(Nofo)
        self.section_ct = ContentType.objects.get_for_model(Section)
        self.subsection_ct = ContentType.objects.get_for_model(Subsection)

    def create_event(
        self,
        obj,
        content_type,
        event_type=CRUDEvent.UPDATE,
        changed_fields=None,
        dt_offset=0,
        object_json_repr=None,
    ):
        return CRUDEvent.objects.create(
            content_type=content_type,
            object_id=str(obj.id),
            object_repr=str(obj),
            object_json_repr=json.dumps(object_json_repr or str(obj)),
            event_type=event_type,
            user=self.user,
            datetime=timezone.now() + timedelta(minutes=dt_offset),
            changed_fields=json.dumps(changed_fields or {"title": ["old", "new"]}),
        )

    def test_includes_all_event_types_except_updated_only(self):
        # Should be included
        self.create_event(
            self.nofo, self.nofo_ct, changed_fields={"title": ["Old", "New"]}
        )
        self.create_event(self.section, self.section_ct)
        self.create_event(
            self.subsection,
            self.subsection_ct,
            object_json_repr=[
                {
                    "model": "nofos.subsection",
                    "pk": str(self.subsection.id),
                    "fields": {
                        "name": self.subsection.name,
                        "section": str(self.section.id),
                    },
                }
            ],
        )

        # Should be excluded (NOFO event with only 'updated')
        self.create_event(
            self.nofo, self.nofo_ct, changed_fields={"updated": ["2023", "2024"]}
        )

        results = get_audit_events_for_nofo(self.nofo)

        # Should only return 3 events
        self.assertEqual(len(results), 3)
        self.assertTrue(all(isinstance(event, CRUDEvent) for event in results))
        self.assertNotIn(
            {"updated": ["2023", "2024"]},
            [json.loads(e.changed_fields or "{}") for e in results],
        )

    def test_returns_events_in_reverse_chronological_order_by_default(self):
        self.create_event(self.nofo, self.nofo_ct, dt_offset=2)
        self.create_event(self.section, self.section_ct, dt_offset=1)
        self.create_event(self.subsection, self.subsection_ct, dt_offset=0)

        events = get_audit_events_for_nofo(self.nofo)

        events_group_by_minute = [
            e.datetime.replace(second=0, microsecond=0) for e in events
        ]
        self.assertEqual(
            events_group_by_minute, sorted(events_group_by_minute, reverse=True)
        )

    def test_returns_events_in_chronological_order_if_requested(self):
        self.create_event(self.nofo, self.nofo_ct, dt_offset=2)
        self.create_event(self.section, self.section_ct, dt_offset=1)
        self.create_event(self.subsection, self.subsection_ct, dt_offset=0)

        events = get_audit_events_for_nofo(self.nofo, reverse=False)
        timestamps = [event.datetime for event in events]

        self.assertEqual(timestamps, sorted(timestamps))

    def test_includes_deleted_subsection_event(self):
        # Delete the subsection (this removes it from the database)
        self.subsection.delete()

        # Create a DELETE event for the subsection
        # event.object_json_repr still contains subsection info despite it not being in the DB
        delete_event = self.create_event(
            self.subsection,
            self.subsection_ct,
            CRUDEvent.DELETE,
            object_json_repr=[
                {
                    "model": "nofos.subsection",
                    "pk": str(self.subsection.id),
                    "fields": {
                        "name": self.subsection.name,
                        "section": str(self.section.id),
                    },
                }
            ],
        )

        # Fetch audit events for the NOFO
        results = get_audit_events_for_nofo(self.nofo)

        # Should include only the delete event, not the active subsection
        self.assertEqual(len(results), 1)
        self.assertIn(delete_event, results)
        self.assertEqual(results[0].event_type, CRUDEvent.DELETE)

    def test_includes_create_subsection_events(self):
        # Create an initial CREATE event for the subsection
        create_event = self.create_event(
            self.subsection,
            self.subsection_ct,
            CRUDEvent.CREATE,
            object_json_repr=[
                {
                    "model": "nofos.subsection",
                    "pk": str(self.subsection.id),
                    "fields": {
                        "name": self.subsection.name,
                        "section": str(self.section.id),
                    },
                }
            ],
            dt_offset=-2,  # 2 minutes ago
        )

        # Fetch audit events for the NOFO
        results = get_audit_events_for_nofo(self.nofo)

        # Ensure CREATE event is included
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], create_event)

    def test_includes_deleted_subsection_event(self):
        # Delete the subsection (this removes it from the database)
        self.subsection.delete()

        # Create a DELETE event for the subsection
        # event.object_json_repr still contains subsection info despite it not being in the DB
        delete_event = self.create_event(
            self.subsection,
            self.subsection_ct,
            CRUDEvent.DELETE,
            object_json_repr=[
                {
                    "model": "nofos.subsection",
                    "pk": str(self.subsection.id),
                    "fields": {
                        "name": self.subsection.name,
                        "section": str(self.section.id),
                    },
                }
            ],
        )

        # Fetch audit events for the NOFO
        results = get_audit_events_for_nofo(self.nofo)

        # Should include only the delete event, not the active subsection
        self.assertEqual(len(results), 1)
        self.assertIn(delete_event, results)
        self.assertEqual(results[0].event_type, CRUDEvent.DELETE)

    def test_includes_create_update_delete_subsection_events(self):
        # Create an initial CREATE event for the subsection
        create_event = self.create_event(
            self.subsection,
            self.subsection_ct,
            CRUDEvent.CREATE,
            object_json_repr=[
                {
                    "model": "nofos.subsection",
                    "pk": str(self.subsection.id),
                    "fields": {
                        "name": self.subsection.name,
                        "section": str(self.section.id),
                    },
                }
            ],
            dt_offset=-2,  # 2 minutes ago
        )

        # Simulate an UPDATE event for the subsection
        update_event = self.create_event(
            self.subsection,
            self.subsection_ct,
            CRUDEvent.UPDATE,
            object_json_repr=[
                {
                    "model": "nofos.subsection",
                    "pk": str(self.subsection.id),
                    "fields": {
                        "name": self.subsection.name,
                        "section": str(self.section.id),
                    },
                }
            ],
            changed_fields={"name": ["Subsection 1", "Updated Subsection"]},
            dt_offset=-1,  # 1 minute ago
        )

        # Delete the subsection (this removes it from the database)
        self.subsection.delete()

        delete_event = self.create_event(
            self.subsection,
            self.subsection_ct,
            CRUDEvent.DELETE,
            object_json_repr=[
                {
                    "model": "nofos.subsection",
                    "pk": str(self.subsection.id),
                    "fields": {
                        "name": self.subsection.name,
                        "section": str(self.section.id),
                    },
                }
            ],
        )

        # Fetch audit events for the NOFO
        results = get_audit_events_for_nofo(self.nofo)
        # Ensure all three events (CREATE, UPDATE, DELETE) are included
        self.assertEqual(len(results), 3)
        self.assertIn(create_event, results)
        self.assertIn(update_event, results)
        self.assertIn(delete_event, results)

        # Ensure reverse chronological order is correct (delete -> update -> create)
        self.assertEqual(results[2], create_event)
        self.assertEqual(results[1], update_event)
        self.assertEqual(results[0], delete_event)
