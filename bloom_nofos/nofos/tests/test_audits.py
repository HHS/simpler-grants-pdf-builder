import json
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from easyaudit.models import CRUDEvent
from nofos.models import Nofo, Section, Subsection
from ..audits import get_audit_events_for_nofo
from django.contrib.auth import get_user_model


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
    ):
        return CRUDEvent.objects.create(
            content_type=content_type,
            object_id=str(obj.id),
            object_repr=str(obj),
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
        self.create_event(self.subsection, self.subsection_ct)

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
        timestamps = [event.datetime for event in events]

        self.assertEqual(timestamps, sorted(timestamps, reverse=True))

    def test_returns_events_in_chronological_order_if_requested(self):
        self.create_event(self.nofo, self.nofo_ct, dt_offset=2)
        self.create_event(self.section, self.section_ct, dt_offset=1)
        self.create_event(self.subsection, self.subsection_ct, dt_offset=0)

        events = get_audit_events_for_nofo(self.nofo, reverse=False)
        timestamps = [event.datetime for event in events]

        self.assertEqual(timestamps, sorted(timestamps))
