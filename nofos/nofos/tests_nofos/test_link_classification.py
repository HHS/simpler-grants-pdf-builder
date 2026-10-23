"""
End-to-end coverage for how link destinations outside a NOFO are classified.

Google Docs URLs and the destination-less "about:blank" placeholder used to be
reported as broken *internal* links, which was misleading (neither is an anchor
into the NOFO) and, for Google Docs, a duplicate of the external-link report.
See GitHub issue #908.
"""

from unittest.mock import patch

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

        missing_panel = soup.find(id="tabpanel-5")
        self.assertEqual(
            [row.a.get_text() for row in missing_panel.find_all("li")],
            ["empty link", "a blank one", "an href-less one"],
        )

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
        The inline highlight remains alongside the missing-destination panel.
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

    def save_body(self, subsection, body):
        url = reverse(
            "nofos:subsection_edit",
            args=[self.nofo.pk, self.section.pk, subsection.pk],
        )
        form = self.client.get(url).context["form"]
        response = self.client.post(
            url,
            {
                "name": subsection.name,
                "tag": subsection.tag,
                "html_class": subsection.html_class,
                "body": body,
                "edit_version": form["edit_version"].value(),
            },
            follow=True,
        )
        self.assertRedirects(response, self.edit_url + "#" + subsection.html_id)
        subsection.refresh_from_db()
        self.assertEqual(subsection.body, body)
        return response

    def missing_rows(self, response):
        soup = BeautifulSoup(response.content, "html.parser")
        panel = soup.find(id="tabpanel-5")
        self.assertIsNotNone(panel)
        return panel.find_all("li")

    @patch("nofos.nofo.requests.get")
    def test_empty_destination_stays_actionable_after_edit_save(self, request):
        subsection = self.section.subsections.get()
        subsection.body = "[See eligibility](#nonexistent-heading)"
        subsection.save()
        before = self.client.get(self.edit_url)
        self.assertEqual(len(before.context["broken_links"]), 1)

        response = self.save_body(subsection, "[See eligibility]()")
        self.assertEqual(response.context["broken_links"], [])
        rows = self.missing_rows(response)
        self.assertEqual(len(rows), 1)
        self.assertIn("See eligibility", rows[0].get_text())
        self.assertIn("Test Section, Links", rows[0].get_text())
        self.assertEqual(rows[0].a["href"], "#links")
        self.assertContains(response, "Check missing link destinations (1)")
        self.assertContains(response, "Link with no destination")
        request.assert_not_called()

        response = self.save_body(subsection, "[See eligibility](#links)")
        self.assertEqual(response.context["missing_destination_links"], [])
        self.assertNotContains(response, 'id="tab-5"')

    def test_multiple_instances_clear_individually_after_saving(self):
        subsection = self.section.subsections.get()
        response = self.save_body(
            subsection,
            "[First]() [Second]() [Third](#missing)",
        )
        self.assertEqual(len(self.missing_rows(response)), 2)
        self.assertEqual(len(response.context["broken_links"]), 1)

        response = self.save_body(subsection, "[First](#links) [Second]() Third")
        self.assertEqual(response.context["broken_links"], [])
        rows = self.missing_rows(response)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].a.get_text(), "Second")

        response = self.save_body(subsection, "[First](#links) Second Third")
        self.assertEqual(response.context["missing_destination_links"], [])
        self.assertNotContains(response, 'id="tab-5"')

    def test_missing_destination_warning_always_has_a_rendered_location_target(self):
        subsection = self.section.subsections.get()
        for name, html_id in (
            ("Links", "links"),
            ("Basic information", "suppressed-basic-information"),
            ("", ""),
        ):
            with self.subTest(name=name, html_id=html_id):
                subsection.name = name
                subsection.html_id = html_id
                subsection.body = "[Find this missing destination]()"
                subsection.save()
                response = self.client.get(self.edit_url)
                soup = BeautifulSoup(response.content, "html.parser")
                link = soup.select_one("#tabpanel-5 li a")
                expected = html_id if name == "Links" else self.section.html_id
                self.assertEqual(link["href"], "#" + expected)
                self.assertIsNotNone(soup.find(id=expected))
                self.assertEqual(link.get_text(), "Find this missing destination")

    @patch("nofos.nofo.requests.get")
    def test_missing_destination_alone_keeps_warning_summary_in_review(self, request):
        # External-link checking is hidden in this status. Complete metadata
        # and valid heading levels leave missing destinations as the sole warning.
        self.nofo.status = "review"
        self.nofo.author = "Test author"
        self.nofo.subject = "Test subject"
        self.nofo.keywords = "test"
        self.nofo.save()
        subsection = self.section.subsections.get()
        response = self.save_body(
            subsection,
            '[Only missing]() <a id="bookmark">Bookmark target</a>',
        )
        self.assertFalse(response.context["has_external_links"])
        self.assertFalse(response.context["has_broken_links"])
        self.assertFalse(response.context["has_heading_errors"])
        self.assertFalse(response.context["has_unconverted_footnotes"])
        self.assertFalse(response.context["has_missing_metadata"])
        self.assertTrue(response.context["has_warnings"])
        self.assertEqual(len(self.missing_rows(response)), 1)
        self.assertContains(response, "Before publishing, address the following:")
        request.assert_not_called()
