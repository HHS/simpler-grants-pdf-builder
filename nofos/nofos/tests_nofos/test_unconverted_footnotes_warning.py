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

    def test_warning_links_to_affected_content_and_includes_current_copy(
        self,
    ):
        response = self.client.get(self.edit_url)
        soup = BeautifulSoup(response.content, "html.parser")

        self.assertTrue(response.context["has_unconverted_footnotes"])
        issues = response.context["unconverted_footnotes"]
        self.assertGreaterEqual(len(issues), 2)

        tab = soup.find(id="tab-4")
        panel = soup.find(id="tabpanel-4")
        self.assertIsNotNone(tab)
        self.assertEqual(tab.get("aria-label"), f"Review endnotes ({len(issues)})")
        location_link = panel.select_one("ol li a")
        self.assertTrue(location_link.get("href").startswith("#"))
        self.assertIn("[1]", panel.get_text())
        self.assertIn("[2]", panel.get_text())

        panel_text = panel.get_text(" ", strip=True)
        self.assertIn("Warning: review endnotes", panel_text)
        self.assertIn(
            "Reference numbers must be sequential and can't repeat", panel_text
        )
        self.assertIn(
            "Every reference number must have a corresponding endnote entry",
            panel_text,
        )
        self.assertIn("matching [1] references and citations", panel_text)
        self.assertIn("correct the affected content here", panel_text)
        self.assertNotIn("not typed manually", panel_text)
        self.assertNotIn("could not be linked automatically", panel_text)

    def test_renamed_endnotes_section_still_shows_warning(self):
        footnotes_section = self.nofo.sections.get(name="Footnotes")
        footnotes_section.name = "Endnotes"
        footnotes_section.html_id = "endnotes"
        footnotes_section.save(update_fields=["name", "html_id"])

        response = self.client.get(self.edit_url)
        soup = BeautifulSoup(response.content, "html.parser")

        self.assertTrue(response.context["has_unconverted_footnotes"])
        self.assertGreaterEqual(len(response.context["unconverted_footnotes"]), 2)
        location_link = soup.select_one("#tabpanel-4 ol li a")
        self.assertTrue(location_link.get("href").startswith("#"))

    def test_opening_legacy_record_never_mutates_content_or_ids(self):
        before = list(self.nofo.sections.values())
        before_bodies = list(
            Subsection.objects.filter(section__nofo=self.nofo).values()
        )
        self.client.get(self.edit_url)
        self.assertEqual(list(self.nofo.sections.values()), before)
        self.assertEqual(
            list(Subsection.objects.filter(section__nofo=self.nofo).values()),
            before_bodies,
        )

    def test_legacy_google_note_links_are_checked_as_rendered(self):
        section = self.nofo.sections.first()
        note = section.subsections.first()
        note.body = "[[1]](#ftnt_ref1) Source."
        note.save()
        program = Section.objects.create(nofo=self.nofo, name="Program", order=0)
        Subsection.objects.create(
            section=program, order=1, name="", tag="", body="Evidence [[1]](#ref1)."
        )
        response = self.client.get(self.edit_url)
        self.assertFalse(response.context["has_unconverted_footnotes"])

    def test_warning_updates_after_edit_and_preserves_valid_links(self):
        section = self.nofo.sections.first()
        note = section.subsections.first()
        note.body = '<ol><li id="endnote-8"><p>Source <a href="#endnote-ref-8">↑</a></p></li></ol>'
        note.save()
        program = Section.objects.create(nofo=self.nofo, name="Program", order=0)
        reference = Subsection.objects.create(
            section=program,
            order=1,
            name="",
            tag="",
            body='<p>Evidence <sup><a id="endnote-ref-8" href="#endnote-8">[1]</a></sup></p>',
        )
        response = self.client.get(self.edit_url)
        self.assertFalse(response.context["has_unconverted_footnotes"])
        note.body = "The citation was removed."
        note.save()
        response = self.client.get(self.edit_url)
        self.assertTrue(response.context["has_unconverted_footnotes"])
        reference.refresh_from_db()
        self.assertIn('href="#endnote-8"', reference.body)
