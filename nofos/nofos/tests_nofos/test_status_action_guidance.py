from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from nofos.models import STATUS_CHOICES, Nofo, Section, Subsection


class StatusActionGuidanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            email="status@example.com",
            password=None,
            group="bloom",
            force_password_reset=False,
        )
        cls.nofo = Nofo.objects.create(title="Status test", group="bloom", opdiv="HRSA")
        cls.section = Section.objects.create(
            nofo=cls.nofo, name="Test section", order=1
        )
        cls.subsection = Subsection.objects.create(
            section=cls.section, name="Summary", tag="h3", body="Test content", order=1
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.edit_url = reverse("nofos:nofo_edit", args=[self.nofo.id])
        self.section_url = reverse(
            "nofos:section_detail", args=[self.nofo.id, self.section.id]
        )
        self.subsection_url = reverse(
            "nofos:subsection_edit",
            args=[self.nofo.id, self.section.id, self.subsection.id],
        )
        self.delete_url = reverse(
            "nofos:subsection_delete",
            args=[self.nofo.id, self.section.id, self.subsection.id],
        )
        self.create_url = reverse(
            "nofos:subsection_create", args=[self.nofo.id, self.section.id]
        )

    def set_status(self, status, *, modified=False, archived=False):
        self.nofo.status = status
        self.nofo.modifications = timezone.now() if modified else None
        self.nofo.archived = timezone.now().date() if archived else None
        self.nofo.save()

    def links_to(self, response, url):
        soup = BeautifulSoup(response.content, "html.parser")
        return [
            a for a in soup.find_all("a", href=True) if a["href"].split("?")[0] == url
        ]

    def test_section_controls_match_existing_status_rules(self):
        cases = [(status, False, False) for status, _ in STATUS_CHOICES]
        cases += [
            ("published", True, False),
            ("draft", False, True),
            ("published", True, True),
        ]
        for status, modified, archived in cases:
            with self.subTest(status=status, modified=modified, archived=archived):
                self.set_status(status, modified=modified, archived=archived)
                response = self.client.get(self.section_url)
                self.assertEqual(response.status_code, 200)
                can_edit = (
                    not archived
                    and status != "cancelled"
                    and (status != "published" or modified)
                )
                can_delete = not archived and status == "draft"
                self.assertEqual(
                    bool(self.links_to(response, self.delete_url)), can_delete
                )
                self.assertEqual(
                    bool(self.links_to(response, self.create_url)), can_edit
                )
                self.assertEqual(
                    b'id="toggle-tables-checkbox"' in response.content, can_edit
                )
                if not can_delete:
                    self.assertContains(response, "Delete unavailable")
                    self.assertContains(response, 'id="subsection-action-guidance"')

    def test_subsection_editor_hides_delete_but_keeps_add_for_editable_non_drafts(self):
        for status in [
            "active",
            "ready-for-qa",
            "review",
            "doge",
            "paused",
            "published",
        ]:
            with self.subTest(status=status):
                self.set_status(status, modified=status == "published")
                response = self.client.get(self.subsection_url)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(self.links_to(response, self.delete_url))
                self.assertTrue(self.links_to(response, self.create_url))
                self.assertContains(response, "Delete subsection unavailable")
                self.assertContains(response, f'href="{self.edit_url}#nofo-status"')

    def test_draft_keeps_existing_delete_links_and_return_destinations(self):
        for url, return_to in [
            (self.section_url, "section_detail"),
            (self.subsection_url, "subsection_edit"),
        ]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(
                    response, f"{self.delete_url}?return_to={return_to}"
                )
                self.assertNotContains(response, 'id="subsection-action-guidance"')
        response = self.client.get(self.delete_url + "?return_to=section_detail")
        self.assertContains(response, "Yes, delete it")
        self.assertEqual(response.context["cancel_url"], self.section_url)

    def test_main_page_explains_draft_requirement_and_has_status_anchor(self):
        self.set_status("active")
        response = self.client.get(self.edit_url)
        self.assertContains(response, 'id="nofo-status"')
        self.assertContains(response, "Deleting a NOFO or its subsections requires")
        self.assertNotContains(response, "Re-importing requires")

    def test_restricted_reimport_states_have_accurate_guidance(self):
        for status in ["review", "doge", "paused", "published"]:
            with self.subTest(status=status):
                self.set_status(status, modified=status == "published")
                response = self.client.get(self.edit_url)
                self.assertContains(response, "Re-importing requires")
                self.assertNotContains(response, "It can be edited or re-imported")

    def test_archived_guidance_does_not_offer_a_status_control_that_is_unavailable(
        self,
    ):
        self.set_status("draft", archived=True)
        response = self.client.get(self.section_url)
        self.assertContains(response, "Archived NOFOs cannot be changed")
        self.assertNotContains(response, "Review NOFO status")

    def test_subsection_delete_get_and_post_still_reject_non_drafts(self):
        for status, _ in STATUS_CHOICES:
            if status == "draft":
                continue
            self.set_status(status, modified=status == "published")
            for method in [self.client.get, self.client.post]:
                with self.subTest(status=status, method=method.__name__):
                    response = method(self.delete_url)
                    self.assertEqual(response.status_code, 400)
                    self.assertTrue(
                        Subsection.objects.filter(pk=self.subsection.pk).exists()
                    )

    def test_draft_post_still_deletes_with_existing_redirect(self):
        response = self.client.post(self.delete_url, {"return_to": "section_detail"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Subsection.objects.filter(pk=self.subsection.pk).exists())
        self.assertEqual(response.url, self.section_url)

    def test_section_view_still_denies_other_groups(self):
        other = get_user_model().objects.create_user(
            email="other-status@example.com",
            password=None,
            group="acf",
            force_password_reset=False,
        )
        self.client.force_login(other)
        self.assertEqual(self.client.get(self.section_url).status_code, 403)
