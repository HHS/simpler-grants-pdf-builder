"""Bounded work and document isolation for the shared history page."""

import json
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from easyaudit.models import CRUDEvent

from nofos.audits import document_audit_entries, get_audit_events_page
from nofos.models import Nofo, Section, Subsection
from nofos.tests_nofos import test_history


class HistoryPaginationTests(TestCase):
    setUp = test_history.NofoHistoryViewTests.setUp

    def event(self, subsection=None, **kwargs):
        subsection = subsection or self.subsection
        return CRUDEvent.objects.create(
            content_type=self.subsection_content_type,
            object_id=str(subsection.pk),
            object_repr="Synthetic subsection edit",
            object_json_repr=json.dumps(
                [{"fields": {"section": str(subsection.section_id)}}]
            ),
            event_type=CRUDEvent.UPDATE,
            user=self.user,
            changed_fields=json.dumps({"body": ["Old content", "New content"]}),
            **kwargs,
        )

    def url(self, offset=None):
        url = reverse("nofos:nofo_history", args=[self.nofo.pk])
        return url if offset is None else f"{url}?offset={offset}"

    def test_pages_have_no_duplicates_and_only_load_page_plus_lookahead(self):
        events = [self.event() for _ in range(60)]
        expected = [e.pk for e in reversed(events)]
        for offset in (0, 25, 50):
            with CaptureQueriesContext(connection) as queries:
                page = get_audit_events_page(self.nofo, offset=offset)
            self.assertEqual([e.pk for e in page], expected[offset : offset + 26])
            index_query = next(
                q["sql"] for q in queries if "nofos_documentauditevent" in q["sql"]
            )
            self.assertIn("LIMIT 26", index_query)
            self.assertNotIn("object_json_repr", index_query)
            self.assertLessEqual(len(queries), 3)
        responses = [self.client.get(self.url(offset)) for offset in (0, 25, 50)]
        shown = []
        for response in responses:
            self.assertEqual(response.status_code, 200)
            shown.extend(e["event_id"] for e in response.context["audit_events"])
        self.assertEqual(shown, expected)
        self.assertTrue(responses[0].context["has_more"])
        self.assertFalse(responses[-1].context["has_more"])

    def test_query_count_does_not_grow_per_visible_row_and_no_diff_runs(self):
        self.event()
        # Warm content-type and URL caches before comparing request query counts.
        self.client.get(self.url())
        with CaptureQueriesContext(connection) as one:
            self.client.get(self.url())
        for _ in range(30):
            self.event()
        with (
            patch("nofos.views.html_diff") as diff,
            patch("nofos.views.markdownify") as render,
            CaptureQueriesContext(connection) as many,
        ):
            response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["audit_events"]), 25)
        self.assertEqual(len(one), len(many))
        diff.assert_not_called()
        render.assert_not_called()

    def test_empty_document_never_includes_another_documents_subsections(self):
        self.event()
        empty = Nofo.objects.create(
            title="Empty synthetic NOFO", group="bloom", opdiv="test"
        )
        self.assertEqual(get_audit_events_page(empty), [])

    def test_deleted_subsection_and_section_events_remain_visible(self):
        event = self.event()
        self.section.delete()
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        row = next(
            e for e in response.context["audit_events"] if e["event_id"] == event.pk
        )
        self.assertEqual(row["object_description"], "Synthetic subsection edit")
        self.assertFalse(row["should_link_to_diff"])

    def test_unrelated_history_does_not_change_query_shape_or_results(self):
        own = self.event()
        other = Nofo.objects.create(
            title="Other synthetic NOFO", group="hrsa", opdiv="test"
        )
        section = Section.objects.create(nofo=other, name="Other section", order=1)
        subsection = Subsection.objects.create(
            section=section, name="Other text", order=1, tag="h2"
        )
        with CaptureQueriesContext(connection) as before:
            initial = get_audit_events_page(self.nofo)
        for _ in range(100):
            self.event(subsection)
        with CaptureQueriesContext(connection) as after:
            result = get_audit_events_page(self.nofo)
        self.assertEqual([e.pk for e in initial], [own.pk])
        self.assertEqual([e.pk for e in result], [own.pk])
        self.assertEqual(len(before), len(after))
        self.assertFalse(any(" LIKE " in q["sql"] for q in after))

    def test_excluded_updates_do_not_create_gaps_in_pagination(self):
        for _ in range(30):
            self.event()
            CRUDEvent.objects.create(
                content_type=self.nofo_content_type,
                object_id=str(self.nofo.pk),
                event_type=CRUDEvent.UPDATE,
                changed_fields='{"updated": ["before", "after"]}',
            )
        response = self.client.get(self.url())
        self.assertEqual(len(response.context["audit_events"]), 25)
        self.assertTrue(response.context["has_more"])

    def test_invalid_and_negative_offsets_use_first_page(self):
        event = self.event()
        for offset in ("bad", "-20", "9" * 100, "9" * 5000):
            with self.subTest(offset=offset):
                response = self.client.get(self.url(offset))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.context["audit_events"][0]["event_id"], event.pk
                )

    def test_other_group_cannot_read_document_history(self):
        self.nofo.group = "hrsa"
        self.nofo.save()
        self.user.group = "cdc"
        self.user.save()
        self.assertEqual(self.client.get(self.url()).status_code, 403)

    def test_sqlite_page_plan_uses_ordered_visible_index_without_temp_sort(self):
        if connection.vendor != "sqlite":
            self.skipTest(
                "SQLite-specific plan check; inspect PostgreSQL on deployment"
            )
        self.event()
        plan = (
            document_audit_entries(self.nofo)
            .values_list("event_id", flat=True)[:26]
            .explain()
        )
        self.assertIn("document_audit_page_idx", plan)
        self.assertNotIn("TEMP B-TREE", plan)

    def test_malformed_changed_fields_do_not_break_history(self):
        event = self.event()
        for changed in ('"body"', '["body"]', '{"body": "invalid pair"}', "not-json"):
            with self.subTest(changed=changed):
                event.changed_fields = changed
                event.save()
                response = self.client.get(self.url())
                self.assertEqual(response.status_code, 200)
                self.assertFalse(
                    response.context["audit_events"][0]["should_link_to_diff"]
                )
