from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from easyaudit.models import CRUDEvent

from nofos.audits import remove_model_from_description

from ..models import Nofo, Section, Subsection

User = get_user_model()


class NofoHistoryViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="test@example.com", password="testpass123")

        self.nofo = Nofo.objects.create(
            title="Test NOFO",
            number="TEST-2024-01",
            group="bloom",
            opdiv="test-opdiv",
        )

        self.section = Section.objects.create(
            nofo=self.nofo,
            name="Test Section",
            order=1,
        )

        self.subsection = Subsection.objects.create(
            section=self.section,
            name="Test Subsection",
            order=2,
            body="Test content",
            tag="h2",
            html_id="test-subsection-2",
        )

        # Get content types for our models
        self.nofo_content_type = ContentType.objects.get_for_model(Nofo)
        self.section_content_type = ContentType.objects.get_for_model(Section)
        self.subsection_content_type = ContentType.objects.get_for_model(Subsection)

    def test_history_view_shows_regular_crud_events(self):
        """Test that history view shows regular CRUD events"""
        # Create a test CRUD event
        event = CRUDEvent.objects.create(
            event_type=CRUDEvent.CREATE,
            object_id=self.nofo.id,
            content_type=self.nofo_content_type,
            object_repr=str(self.nofo),
            user=self.user,
            datetime=timezone.now(),
        )

        url = reverse("nofos:nofo_history", args=[self.nofo.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, event.get_event_type_display())
        self.assertContains(
            response, remove_model_from_description(str(self.nofo), "nofo")
        )

    def test_history_view_shows_custom_audit_events(self):
        """Test that history view shows custom audit events (import, print, reimport)"""
        # Create a NOFO import event
        import_event = CRUDEvent.objects.create(
            event_type=CRUDEvent.UPDATE,
            object_id=self.nofo.id,
            content_type=self.nofo_content_type,
            object_repr=str(self.nofo),
            user=self.user,
            datetime=timezone.now(),
            changed_fields='{"action": "nofo_import", "updated": ["2024-01-01 12:00:00.000000"]}',
        )

        # Create a NOFO print event with test mode
        print_event = CRUDEvent.objects.create(
            event_type=CRUDEvent.UPDATE,
            object_id=self.nofo.id,
            content_type=self.nofo_content_type,
            object_repr=str(self.nofo),
            user=self.user,
            datetime=timezone.now(),
            changed_fields='{"action": "nofo_print", "updated": ["2024-01-01 12:00:00.000000"], "print_mode": ["test"]}',
        )

        url = reverse("nofos:nofo_history", args=[self.nofo.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NOFO imported")
        self.assertContains(response, "NOFO printed (test mode)")

    def test_history_view_shows_section_and_subsection_events(self):
        """Test that history view shows events from sections and subsections"""
        # Create a section update event
        section_event = CRUDEvent.objects.create(
            event_type=CRUDEvent.UPDATE,
            object_id=self.section.id,
            content_type=self.section_content_type,
            object_repr=str(self.section),
            user=self.user,
            datetime=timezone.now(),
        )

        # Create a subsection update event
        subsection_event = CRUDEvent.objects.create(
            event_type=CRUDEvent.UPDATE,
            object_id=self.subsection.id,
            content_type=self.subsection_content_type,
            object_repr=str(self.subsection),
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
            changed_fields='{"body": ["Old content", "Test content"]}',
            user=self.user,
            datetime=timezone.now(),
        )

        url = reverse("nofos:nofo_history", args=[self.nofo.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, section_event.get_event_type_display())
        self.assertContains(response, subsection_event.get_event_type_display())
        self.assertContains(response, "Section")
        self.assertContains(response, "Subsection")

    def test_history_view_does_not_show_change_events_without_changed_fields(self):
        """Test that history view does not show change events without changed_fields"""
        # Create a subsection update event without changed_fields
        subsection_event = CRUDEvent.objects.create(
            event_type=CRUDEvent.UPDATE,
            object_id=self.subsection.id,
            content_type=self.subsection_content_type,
            object_repr=str(self.subsection),
            user=self.user,
            datetime=timezone.now(),
        )

        url = reverse("nofos:nofo_history", args=[self.nofo.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, subsection_event.get_event_type_display())
