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
                'and <a href="">a blank one</a> and <a>an href-less one</a> '
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
        for absent in (
            "Google Docs link",
            "empty link",
            "a blank one",
            "an href-less one",
        ):
            self.assertNotIn(absent, panel_text)

    def test_edit_page_counts_every_offsite_destination_as_external(self):
        response = self.client.get(self.edit_url)

        external = response.context["external_links"]
        self.assertEqual(
            sorted(link["link_text"] for link in external),
            [
                "Google Docs link",
                "a blank one",
                "an href-less one",
                "empty link",
            ],
        )
        self.assertTrue(response.context["has_external_links"])

    def test_edit_page_highlights_no_destination_links_in_the_body(self):
        """
        These are not in the broken-links panel, so the inline highlight is
        the only thing that shows a designer where they are.
        """
        response = self.client.get(self.edit_url)
        soup = BeautifulSoup(response.content, "html.parser")

        flagged = {
            link.get_text(strip=True): link.get("title")
            for link in soup.select("a.nofo_edit--broken-link")
        }

        # All three no-destination shapes get the same highlight and message.
        # Note "empty link" is the about:blank one: martor's sanitizer strips
        # the "about:" scheme, so it reaches the template href-less, exactly
        # like the anchor that never had an href.
        self.assertEqual(flagged.get("empty link"), "Link with no destination")
        self.assertEqual(flagged.get("a blank one"), "Link with no destination")
        self.assertEqual(flagged.get("an href-less one"), "Link with no destination")
        self.assertNotIn("Google Docs link", flagged)

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
        self.assertEqual(
            sorted(link["link_text"] for link in invalid_links),
            ["a blank one", "an href-less one", "empty link"],
        )

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
