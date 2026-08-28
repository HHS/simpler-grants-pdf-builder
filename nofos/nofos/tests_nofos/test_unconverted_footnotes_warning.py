from bs4 import BeautifulSoup
from django.test import Client, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, Section, Subsection


class NofoUnconvertedFootnotesWarningTests(TestCase):
    def setUp(self):
        user = BloomUser.objects.create_user(
            email="unconverted-footnotes@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client = Client()
        self.client.force_login(user)
        self.nofo = Nofo.objects.create(
            title="Unconverted footnotes warning test",
            short_name="unconverted-footnotes-warning",
            number="TEST-840",
            opdiv="TEST",
            group="bloom",
            status="draft",
        )
        footnotes_section = Section.objects.create(
            nofo=self.nofo,
            name="Footnotes",
            html_id="footnotes",
            order=1,
        )
        Subsection.objects.create(
            section=footnotes_section,
            name="",
            tag="",
            body="[1] First manually typed note.\n\n[2] Second manually typed note.",
            order=1,
        )
        self.edit_url = reverse("nofos:nofo_edit", kwargs={"pk": self.nofo.id})

    def test_section_level_warning_links_to_section_once_and_includes_required_copy(
        self,
    ):
        response = self.client.get(self.edit_url)
        soup = BeautifulSoup(response.content, "html.parser")

        self.assertTrue(response.context["has_unconverted_footnotes"])
        self.assertEqual(len(response.context["unconverted_footnotes"]), 1)

        tab = soup.find(id="tab-4")
        panel = soup.find(id="tabpanel-4")
        self.assertIsNotNone(tab)
        self.assertEqual(
            tab.get("aria-label"), "Check possible unconverted footnotes (1)"
        )
        location_link = panel.select_one("ol li a")
        self.assertEqual(location_link.get("href"), "#footnotes")
        self.assertEqual(location_link.get_text(strip=True), "Footnotes")

        panel_text = panel.get_text(" ", strip=True)
        self.assertIn("There is 1 location to review", panel_text)
        self.assertIn("reference numbers are sequential with no repeats", panel_text)
        self.assertIn("each reference has a corresponding entry", panel_text)
