from bs4 import BeautifulSoup
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.content_processing import (
    get_sections_and_subsections_from_soup,
    remove_step_1_tagline_subsections,
)
from nofos.models import Nofo, Section, Subsection


def _subsection(name, order, body_html, tag="h3"):
    soup = BeautifulSoup(body_html, "html.parser")
    return {
        "name": name,
        "order": order,
        "tag": tag if name else "",
        "html_id": "",
        "is_callout_box": False,
        "body": [tag for tag in soup.contents if getattr(tag, "name", None)],
    }


class RemoveTaglineSubsectionsFromStep1Tests(TestCase):
    def _sections(
        self, step_1_subsections, section_name="Step 1: Review the Opportunity"
    ):
        return [
            {"name": section_name, "order": 1, "subsections": step_1_subsections},
            {
                "name": "Step 2: Get Ready to Apply",
                "order": 2,
                "subsections": [
                    _subsection("", 1, "<p>Tagline: Not in Step 1, keep me.</p>")
                ],
            },
        ]

    def test_removes_untitled_subsection_starting_with_tagline(self):
        sections = self._sections(
            [
                _subsection("", 1, "<p>Tagline: Helping families thrive.</p>"),
                _subsection("Basic information", 2, "<p>Basic info body.</p>"),
                _subsection("Eligibility", 3, "<p>Eligibility body.</p>"),
            ]
        )

        removed = remove_step_1_tagline_subsections(sections)

        self.assertEqual(len(removed), 1)
        step_1 = sections[0]["subsections"]
        self.assertEqual(
            [(s["name"], s["order"]) for s in step_1],
            [("Basic information", 1), ("Eligibility", 2)],
        )

    def test_removes_whole_subsection_even_with_content_after_tagline(self):
        sections = self._sections(
            [
                _subsection(
                    "",
                    1,
                    "<p>Tagline: Helping families thrive.</p><p>More text.</p>",
                ),
            ]
        )

        remove_step_1_tagline_subsections(sections)

        self.assertEqual(sections[0]["subsections"], [])

    def test_match_is_case_and_whitespace_insensitive_and_skips_empty_paragraphs(
        self,
    ):
        sections = self._sections(
            [
                _subsection(
                    "",
                    1,
                    "<p> </p><p>​</p><p><strong>TAGLINE :</strong> Thrive.</p>",
                ),
            ]
        )

        remove_step_1_tagline_subsections(sections)

        self.assertEqual(sections[0]["subsections"], [])

    def test_keeps_titled_subsection_starting_with_tagline(self):
        sections = self._sections(
            [_subsection("Summary", 1, "<p>Tagline: Helping families thrive.</p>")]
        )

        removed = remove_step_1_tagline_subsections(sections)

        self.assertEqual(removed, [])
        self.assertEqual(len(sections[0]["subsections"]), 1)

    def test_keeps_untitled_subsection_when_tagline_is_not_first(self):
        sections = self._sections(
            [
                _subsection(
                    "",
                    1,
                    "<p>Opening paragraph.</p><p>Tagline: Helping families thrive.</p>",
                )
            ]
        )

        removed = remove_step_1_tagline_subsections(sections)

        self.assertEqual(removed, [])
        self.assertEqual(len(sections[0]["subsections"]), 1)

    def test_keeps_text_that_mentions_tagline_without_label(self):
        sections = self._sections(
            [_subsection("", 1, "<p>Taglines are short summaries.</p>")]
        )

        remove_step_1_tagline_subsections(sections)

        self.assertEqual(len(sections[0]["subsections"]), 1)

    def test_ignores_sections_other_than_step_1(self):
        sections = self._sections(
            [_subsection("", 1, "<p>Tagline: Helping families thrive.</p>")],
            section_name="Step 3: Prepare Your Application",
        )

        removed = remove_step_1_tagline_subsections(sections)

        self.assertEqual(removed, [])
        self.assertEqual(len(sections[0]["subsections"]), 1)
        self.assertEqual(len(sections[1]["subsections"]), 1)

    def test_handles_string_and_callout_box_bodies(self):
        callout_cell = BeautifulSoup(
            "<div><p>Tagline: In a callout.</p></div>", "html.parser"
        ).div
        sections = self._sections(
            [
                {
                    "name": "",
                    "order": 1,
                    "tag": "",
                    "html_id": "",
                    "is_callout_box": True,
                    "body": callout_cell,
                },
                {
                    "name": "",
                    "order": 2,
                    "tag": "",
                    "html_id": "",
                    "body": ["<p>Tagline: As a string.</p>"],
                },
            ]
        )

        remove_step_1_tagline_subsections(sections)

        self.assertEqual(sections[0]["subsections"], [])


class SectionParserOptInTests(TestCase):
    HTML = (
        "<h1>Step 1: Review the Opportunity</h1>"
        "<p>Tagline: Helping families thrive.</p>"
        "<h2>Basic information</h2><p>Body.</p>"
    )

    def _step_1_names(self, **kwargs):
        soup = BeautifulSoup(self.HTML, "html.parser")
        sections = get_sections_and_subsections_from_soup(soup, "h1", **kwargs)
        return [s["name"] for s in sections[0]["subsections"]]

    def test_builder_opt_in_removes_tagline_subsection(self):
        self.assertEqual(
            self._step_1_names(consume_scoped_tagline=True), ["Basic information"]
        )

    def test_without_opt_in_composer_and_compare_keep_it(self):
        self.assertEqual(self._step_1_names(), ["", "Basic information"])


TAGLINE_HTML = """
<html><body>
<p>Opportunity name: Tagline fixture</p>
<p>OpDiv: Administration for Children and Families</p>
<p>Opportunity number: {number}</p>
<p>Tagline: Helping families thrive.</p>
<h1>Step 1: Review the Opportunity</h1>
<p>Tagline: Helping families thrive.</p>
<h2>Basic information</h2>
<p>Basic information body.</p>
<h1>Step 2: Get Ready to Apply</h1>
<p>Tagline: Not in Step 1, keep me.</p>
</body></html>
"""


def _upload(number):
    return SimpleUploadedFile(
        "tagline.html",
        TAGLINE_HTML.format(number=number).encode("utf-8"),
        content_type="text/html",
    )


class TaglineSubsectionImportTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="tagline-test@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client = Client()
        self.client.login(email="tagline-test@example.com", password="testpass123")

    def _assert_tagline_removed_from_step_1(self, nofo):
        self.assertEqual(nofo.tagline, "Helping families thrive.")

        step_1 = nofo.sections.get(order=1)
        step_1_subsections = list(step_1.subsections.order_by("order"))
        self.assertEqual(
            [(s.name, s.order) for s in step_1_subsections],
            [("Basic information", 1)],
        )
        self.assertFalse(any("Tagline" in (s.body or "") for s in step_1_subsections))

        # Only Step 1 is affected
        step_2 = nofo.sections.get(order=2)
        self.assertIn("Tagline: Not in Step 1", step_2.subsections.first().body)

    def test_new_import_omits_tagline_subsection_in_step_1(self):
        response = self.client.post(
            reverse("nofos:nofo_import"), {"nofo-import": _upload("ACF-TAG-001")}
        )

        self.assertEqual(response.status_code, 302)
        self._assert_tagline_removed_from_step_1(Nofo.objects.get())

    def test_reimport_omits_tagline_subsection_in_step_1(self):
        nofo = Nofo.objects.create(
            title="Tagline fixture",
            number="ACF-TAG-001",
            opdiv="ACF",
            group="bloom",
        )
        section = Section.objects.create(nofo=nofo, name="Old section", order=1)
        Subsection.objects.create(
            section=section, name="Old subsection", order=1, tag="h3", body="Old"
        )

        response = self.client.post(
            reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.id}),
            {"nofo-import": _upload("ACF-TAG-001")},
        )

        self.assertEqual(response.status_code, 302)
        nofo.refresh_from_db()
        self._assert_tagline_removed_from_step_1(nofo)

    def test_confirmed_reimport_with_new_number_omits_tagline_subsection(self):
        nofo = Nofo.objects.create(
            title="Tagline fixture",
            number="ACF-TAG-001",
            opdiv="ACF",
            group="bloom",
        )

        response = self.client.post(
            reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.id}),
            {"nofo-import": _upload("ACF-TAG-002")},
        )
        self.assertRedirects(
            response,
            reverse("nofos:nofo_import_confirm_overwrite", kwargs={"pk": nofo.id}),
            fetch_redirect_response=False,
        )

        response = self.client.post(
            reverse("nofos:nofo_import_confirm_overwrite", kwargs={"pk": nofo.id})
        )

        self.assertEqual(response.status_code, 302)
        nofo.refresh_from_db()
        self._assert_tagline_removed_from_step_1(nofo)
