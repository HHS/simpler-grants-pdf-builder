from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from nofos.models import Nofo, Section, Subsection

User = get_user_model()


class SubsectionEditTemplateTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="test@example.com", password="testpass123")

        self.nofo = Nofo.objects.create(
            title="Test NOFO", group="bloom", opdiv="HRSA", modifications=timezone.now()
        )
        self.modifications_section = Section.objects.create(
            nofo=self.nofo, name="Modifications", html_id="modifications", order=1
        )

    def test_modifications_block_renders_for_first_subsection(self):
        subsection = Subsection.objects.create(
            section=self.modifications_section,
            name="Test Subsection",
            order=1,
            tag="h3",
        )

        response = self.client.get(
            reverse(
                "nofos:subsection_edit",
                args=[self.nofo.id, self.modifications_section.id, subsection.id],
            )
        )
        self.assertContains(response, "Modifications date")
        self.assertContains(response, "Edit modifications table")

    def test_modifications_block_does_not_render_if_order_is_not_1(self):
        subsection = Subsection.objects.create(
            section=self.modifications_section,
            name="Another Subsection",
            order=2,
            tag="h3",
        )

        response = self.client.get(
            reverse(
                "nofos:subsection_edit",
                args=[self.nofo.id, self.modifications_section.id, subsection.id],
            )
        )
        self.assertNotContains(response, "Modifications date")

    def test_modifications_block_does_not_render_if_section_name_differs(self):
        other_section = Section.objects.create(
            nofo=self.nofo, name="Other Section", html_id="other", order=2
        )
        subsection = Subsection.objects.create(
            section=other_section, name="Test Subsection", order=1, tag="h3"
        )

        response = self.client.get(
            reverse(
                "nofos:subsection_edit",
                args=[self.nofo.id, other_section.id, subsection.id],
            )
        )
        self.assertNotContains(response, "Modifications date")

    def test_modifications_block_does_not_render_if_no_modification_date(self):
        self.nofo.modifications = None
        self.nofo.save()

        subsection = Subsection.objects.create(
            section=self.modifications_section,
            name="Test Subsection",
            order=1,
            tag="h3",
        )

        response = self.client.get(
            reverse(
                "nofos:subsection_edit",
                args=[self.nofo.id, self.modifications_section.id, subsection.id],
            )
        )

        self.assertNotContains(response, "Modifications date")
