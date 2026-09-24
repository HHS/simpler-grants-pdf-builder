import io
import json

from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone
from easyaudit.models import CRUDEvent
from freezegun import freeze_time
from users.models import BloomUser

from nofos.models import ImportAttempt, Nofo, Section, Subsection


class ImportDriftMetricsCommandTests(TestCase):
    @freeze_time("2026-09-15 12:00:00")
    def setUp(self):
        self.external_user = BloomUser.objects.create_user(
            email="external@example.com", password=None, group="cdc"
        )
        self.internal_user = BloomUser.objects.create_user(
            email="internal@example.com", password=None, group="bloom"
        )
        self.nofo = Nofo.objects.create(
            title="Drift test", number="CDC-001", opdiv="CDC", group="cdc"
        )
        self.section = Section.objects.create(
            nofo=self.nofo, name="Section", html_id="section", order=1
        )
        self.subsection = Subsection.objects.create(
            section=self.section,
            name="Subsection",
            html_id="subsection",
            order=1,
            tag="h3",
        )

        # Ignore automatic setup events; the command tests use explicit fixtures.
        CRUDEvent.objects.all().delete()

        ImportAttempt.objects.create(
            user=self.external_user,
            nofo=self.nofo,
            filename="source.docx",
            is_reimport=True,
            warning_count=2,
        )
        ImportAttempt.objects.create(
            user=self.external_user,
            filename="broken.docx",
            error_code="IMPORT-AMBIGUOUS-HEADINGS",
        )
        ImportAttempt.objects.create(
            user=self.internal_user,
            filename="internal.docx",
            warning_count=99,
        )

        subsection_type = ContentType.objects.get_for_model(Subsection)
        nofo_type = ContentType.objects.get_for_model(Nofo)
        now = timezone.now()
        CRUDEvent.objects.create(
            event_type=CRUDEvent.UPDATE,
            object_id=str(self.subsection.pk),
            content_type=subsection_type,
            user=self.external_user,
            datetime=now,
            changed_fields=json.dumps(
                {
                    "name": ["sensitive old heading", "sensitive new heading"],
                    "tag": ["h3", "h4"],
                    "body": ["sensitive old body", "sensitive new body"],
                }
            ),
        )
        CRUDEvent.objects.create(
            event_type=CRUDEvent.UPDATE,
            object_id=str(self.nofo.pk),
            content_type=nofo_type,
            user=self.external_user,
            datetime=now,
            changed_fields=json.dumps({"action": "nofo_reimport"}),
        )
        CRUDEvent.objects.create(
            event_type=CRUDEvent.UPDATE,
            object_id=str(self.nofo.pk),
            content_type=nofo_type,
            user=self.external_user,
            datetime=now,
            changed_fields="not-json",
        )
        CRUDEvent.objects.create(
            event_type=CRUDEvent.UPDATE,
            object_id=str(self.nofo.pk),
            content_type=nofo_type,
            user=self.external_user,
            datetime=now,
            changed_fields=json.dumps({"action": "sensitive user supplied action"}),
        )
        CRUDEvent.objects.create(
            event_type=CRUDEvent.UPDATE,
            object_id=str(self.subsection.pk),
            content_type=subsection_type,
            user=self.internal_user,
            datetime=now,
            changed_fields=json.dumps({"body": ["old", "new"]}),
        )
        CRUDEvent.objects.create(
            event_type=CRUDEvent.UPDATE,
            object_id=str(self.subsection.pk),
            content_type=subsection_type,
            user=None,
            datetime=now,
            changed_fields=json.dumps({"body": ["old", "new"]}),
        )

    def run_command(self, *extra_args):
        output = io.StringIO()
        call_command(
            "import_drift_metrics",
            "--since",
            "2026-09-01",
            "--until",
            "2026-10-01",
            *extra_args,
            stdout=output,
        )
        return output.getvalue()

    def test_reports_aggregate_external_signals_without_payload_values(self):
        output = self.run_command()

        expected_rows = {
            "imports.attempts\t2\tN/A",
            "imports.reimport_attempts\t1\tN/A",
            "imports.failed_attempts\t1\tN/A",
            "imports.attempts_with_warnings\t1\tN/A",
            "imports.warning_count\t2\tN/A",
            "imports.error.import-ambiguous-headings\t1\tN/A",
            "audit.eligible_events\t4\tN/A",
            "audit.unknown_user_events\t1\tN/A",
            "audit.internal_events_excluded\t1\tN/A",
            "action.nofo_reimport\t1\t1",
            "action.other\t1\t1",
            "audit.unreadable_changed_fields\t1\t1",
            "edit.heading_text\t1\t1",
            "edit.heading_level\t1\t1",
            "edit.subsection_body\t1\t1",
        }
        self.assertTrue(expected_rows.issubset(set(output.splitlines())))
        self.assertNotIn("sensitive", output)
        self.assertNotIn("external@example.com", output)
        self.assertNotIn("source.docx", output)

    def test_group_filter_uses_import_time_group_and_current_audit_user_group(self):
        output = self.run_command("--group", "cdc")

        self.assertIn("imports.attempts\t2\tN/A", output)
        self.assertIn("audit.eligible_events\t4\tN/A", output)

    def test_rejects_invalid_date_window(self):
        with self.assertRaisesMessage(CommandError, "--until must be later"):
            self.run_command("--since", "2026-10-01")

    def test_rejects_unknown_group(self):
        with self.assertRaisesMessage(CommandError, "Unknown OpDiv group"):
            self.run_command("--group", "not-a-group")
