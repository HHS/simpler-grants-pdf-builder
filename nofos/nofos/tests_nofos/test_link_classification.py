"""
End-to-end coverage for how link destinations outside a NOFO are classified.

Google Docs URLs and the destination-less "about:blank" placeholder used to be
reported as broken *internal* links, which was misleading (neither is an anchor
into the NOFO) and, for Google Docs, a duplicate of the external-link report.
See GitHub issue #908.
"""

from bs4 import BeautifulSoup
from django.test import Client, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, Section, Subsection

GOOGLE_DOCS_URL = "https://docs.google.com/document/d/some-document"


class LinkClassificationViewTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="link-classification@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client = Client()
        self.client.force_login(self.user)

        self.nofo = Nofo.objects.create(
            title="Link classification test NOFO",
            short_name="link-classification-test",
            number="TEST-908",
            opdiv="TEST",
            group="bloom",
            status="draft",
        )
        self.section = Section.objects.create(
            nofo=self.nofo, name="Test Section", html_id="test-section", order=1
        )
        Subsection.objects.create(
            section=self.section,
            name="Links",
            tag="h3",
            order=1,
            html_id="links",
            body=(
                "A [Google Docs link]({}) and an [empty link](about:blank) "
                "and a [truly broken link](#h.gone)."
            ).format(GOOGLE_DOCS_URL),
        )

        self.edit_url = reverse("nofos:nofo_edit", kwargs={"pk": self.nofo.id})
        self.check_links_url = reverse(
            "nofos:nofo_check_links", kwargs={"pk": self.nofo.id}
        )

    def test_edit_page_broken_links_panel_excludes_google_docs_and_about_blank(self):
        response = self.client.get(self.edit_url)

        broken_hrefs = [link["link_href"] for link in response.context["broken_links"]]
        self.assertEqual(broken_hrefs, ["#h.gone"])

        soup = BeautifulSoup(response.content, "html.parser")
        panel = soup.find(id="tabpanel-1")
        self.assertIsNotNone(panel)
        panel_text = panel.get_text(" ", strip=True)
        self.assertIn("There is 1 broken link", panel_text)
        self.assertNotIn("Google Docs link", panel_text)
        self.assertNotIn("empty link", panel_text)

    def test_edit_page_counts_google_docs_and_about_blank_as_external(self):
        response = self.client.get(self.edit_url)

        external_urls = [link["url"] for link in response.context["external_links"]]
        self.assertEqual(sorted(external_urls), ["about:blank", GOOGLE_DOCS_URL])
        self.assertTrue(response.context["has_external_links"])

    def test_check_links_page_lists_google_docs_as_a_normal_external_link(self):
        response = self.client.get(self.check_links_url)

        google_docs_link = next(
            link for link in response.context["links"] if link["url"] == GOOGLE_DOCS_URL
        )
        self.assertEqual(google_docs_link["domain"], "docs.google.com")
        self.assertFalse(google_docs_link["invalid_destination"])
        self.assertContains(response, "docs.google.com")

    def test_check_links_page_flags_about_blank_as_having_no_destination(self):
        response = self.client.get(self.check_links_url)

        invalid_links = response.context["invalid_destination_links"]
        self.assertEqual([link["url"] for link in invalid_links], ["about:blank"])

        page_text = BeautifulSoup(response.content, "html.parser").get_text(
            " ", strip=True
        )
        self.assertIn("no destination", page_text)
        self.assertIn("Not checked", page_text)

    def test_check_links_page_has_no_invalid_banner_without_about_blank(self):
        Subsection.objects.filter(section=self.section).update(
            body="Just a [Google Docs link]({}).".format(GOOGLE_DOCS_URL)
        )

        response = self.client.get(self.check_links_url)

        self.assertEqual(response.context["invalid_destination_links"], [])
        page_text = BeautifulSoup(response.content, "html.parser").get_text(
            " ", strip=True
        )
        self.assertNotIn("no destination", page_text)
