from datetime import date

from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, Section, Subsection
from nofos.nofo import END_NOTES_PLACEHOLDER_BODY


class NofoAddEndNotesSectionViewTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="test@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client = Client()
        self.client.login(email="test@example.com", password="testpass123")

        self.nofo = Nofo.objects.create(
            title="Test NOFO",
            short_name="test-nofo",
            number="NOFO-ACF-001",
            opdiv="ACF",
            group="bloom",
            status="draft",
        )

        self.section = Section.objects.create(
            nofo=self.nofo,
            name="Section 1",
            order=1,
        )

        self.url = reverse("nofos:section_add_end_notes", kwargs={"pk": self.nofo.id})

    def test_get_request_renders_template_with_prepopulated_body(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "nofos/section_add_end_notes.html")
        self.assertEqual(
            response.context["form"].initial.get("body"), END_NOTES_PLACEHOLDER_BODY
        )

    def test_post_creates_endnotes_section_and_subsection(self):
        response = self.client.post(
            self.url, {"body": "<ol><li>My endnote</li></ol>"}, follow=True
        )
        self.assertEqual(response.status_code, 200)

        section = self.nofo.sections.get(name="Endnotes")
        self.assertEqual(section.html_id, "endnotes")
        self.assertFalse(section.has_section_page)
        self.assertEqual(section.order, 2)  # after the one existing section

        subsections = section.subsections.all()
        self.assertEqual(subsections.count(), 1)
        self.assertEqual(subsections[0].name, "")
        self.assertEqual(subsections[0].tag, "")
        self.assertEqual(subsections[0].body, "<ol><li>My endnote</li></ol>")
        self.assertEqual(subsections[0].order, 1)

        messages = [msg.message for msg in get_messages(response.wsgi_request)]
        self.assertTrue(any("Added new section" in m for m in messages))

    def test_post_with_no_body_uses_placeholder_content(self):
        # The form field is not required, but the page always ships with the
        # placeholder prefilled - simulate a real submit of that value.
        self.client.post(self.url, {"body": END_NOTES_PLACEHOLDER_BODY}, follow=True)

        section = self.nofo.sections.get(name="Endnotes")
        self.assertEqual(section.subsections.first().body, END_NOTES_PLACEHOLDER_BODY)

    def test_post_inserts_endnotes_directly_above_existing_modifications_section(self):
        modifications_section = Section.objects.create(
            nofo=self.nofo, name="Modifications", html_id="modifications", order=2
        )

        self.client.post(self.url, {"body": "content"}, follow=True)

        section = self.nofo.sections.get(name="Endnotes")
        modifications_section.refresh_from_db()

        self.assertEqual(section.order, 2)
        self.assertEqual(modifications_section.order, 3)
        self.assertLess(section.order, modifications_section.order)

    def test_post_shifts_sections_after_nonfinal_modifications_without_collision(self):
        modifications_section = Section.objects.create(
            nofo=self.nofo, name="Modifications", html_id="modifications", order=2
        )
        appendix_section = Section.objects.create(
            nofo=self.nofo, name="Appendix", html_id="appendix", order=3
        )

        response = self.client.post(self.url, {"body": "content"})

        self.assertEqual(response.status_code, 302)
        endnotes_section = self.nofo.sections.get(html_id="endnotes")
        modifications_section.refresh_from_db()
        appendix_section.refresh_from_db()
        self.assertEqual(endnotes_section.order, 2)
        self.assertEqual(modifications_section.order, 3)
        self.assertEqual(appendix_section.order, 4)

    def test_get_redirects_when_endnotes_section_already_exists(self):
        Section.objects.create(
            nofo=self.nofo, name="Endnotes", html_id="endnotes", order=2
        )

        response = self.client.get(self.url, follow=True)
        self.assertRedirects(
            response, reverse("nofos:nofo_edit", kwargs={"pk": self.nofo.id})
        )

        messages = [msg.message for msg in get_messages(response.wsgi_request)]
        self.assertTrue(any("already has an Endnotes section" in m for m in messages))

    def test_post_does_not_duplicate_endnotes_section(self):
        Section.objects.create(
            nofo=self.nofo, name="Endnotes", html_id="endnotes", order=2
        )

        self.client.post(self.url, {"body": "content"}, follow=True)

        self.assertEqual(self.nofo.sections.filter(name="Endnotes").count(), 1)
        self.assertEqual(Subsection.objects.filter(section__nofo=self.nofo).count(), 0)

    def test_post_does_not_duplicate_endnotes_html_id_under_another_name(self):
        Section.objects.create(
            nofo=self.nofo,
            name="References",
            html_id="endnotes",
            order=2,
        )

        response = self.client.post(self.url, {"body": "content"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.nofo.sections.filter(html_id="endnotes").count(), 1)
        self.assertEqual(Subsection.objects.filter(section__nofo=self.nofo).count(), 0)

    def test_prevents_add_on_published_nofo(self):
        self.nofo.status = "published"
        self.nofo.save()

        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.post(self.url, {"body": "content"})

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Endnotes can’t be added to published NOFOs.", status_code=400
        )
        self.assertFalse(self.nofo.sections.filter(name="Endnotes").exists())

    def test_prevents_add_on_published_nofo_with_modifications(self):
        self.nofo.status = "published"
        self.nofo.modifications = date(2026, 8, 28)
        self.nofo.save()

        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.post(self.url, {"body": "content"})

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Endnotes can’t be added to published NOFOs.", status_code=400
        )
        self.assertFalse(self.nofo.sections.filter(html_id="endnotes").exists())

    def test_prevents_add_on_archived_nofo(self):
        from django.utils import timezone

        self.nofo.archived = timezone.now().date()
        self.nofo.save()

        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.post(self.url, {"body": "content"})

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Endnotes can’t be added to archived NOFOs.", status_code=400
        )
        self.assertFalse(self.nofo.sections.filter(name="Endnotes").exists())

    def test_checks_group_access_before_revealing_existing_endnotes(self):
        self.nofo.group = "acf"
        self.nofo.save()
        Section.objects.create(
            nofo=self.nofo,
            name="Endnotes",
            html_id="endnotes",
            order=2,
        )
        other_user = BloomUser.objects.create_user(
            email="other@example.com",
            password="testpass123",
            force_password_reset=False,
            group="hrsa",
        )
        self.client.force_login(other_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)
