"""Regression coverage for supported div-wrapped document headings (#1049)."""

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from martor.templatetags.martortags import safe_markdown

from nofos.models import Nofo
from nofos.nofo import unwrap_heading_containers
from nofos.tests_nofos.test_import_characterization import html_upload, translate


@override_settings(DEBUG=False)
class WrappedHeadingTests(SimpleTestCase):
    def test_nested_wrappers_keep_sections_and_subsections_in_order(self):
        for section_tag, subsection_tag in (("h1", "h2"), ("h2", "h3")):
            with self.subTest(section_tag=section_tag):
                _, sections, rendered = translate(
                    f'<div><div><{section_tag} id="opportunity">Opportunity</{section_tag}>'
                    f'<div><{subsection_tag} id="eligibility">Eligibility</{subsection_tag}>'
                    f"<p>Public agencies.</p></div></div><{section_tag}>Apply</{section_tag}>"
                    "<p>Submit online.</p></div>"
                )
                self.assertEqual(
                    [s["name"] for s in sections], ["Opportunity", "Apply"]
                )
                eligibility = sections[0]["subsections"][0]
                self.assertEqual(eligibility["name"], "Eligibility")
                self.assertEqual(eligibility["html_id"], "eligibility")
                self.assertEqual(eligibility["tag"], "h3")
                self.assertIn("Public agencies.", rendered.get_text())
                self.assertIn("Submit online.", rendered.get_text())

    def test_wrapper_targets_alias_heading_without_overwriting_existing_id(self):
        soup, sections, rendered = translate(
            '<div id="outer"><h1 id="section">Opportunity</h1>'
            '<div id="inner"><h2 id="eligibility">Eligibility</h2>'
            '<p><a href="#outer">Section</a> <a href="#inner">Eligibility</a></p>'
            "</div></div>"
        )
        self.assertEqual(soup.h1["id"], "section")
        self.assertEqual(sections[0]["subsections"][0]["html_id"], "eligibility")
        self.assertEqual(
            [a["href"] for a in rendered.find_all("a")], ["#section", "#eligibility"]
        )

    def test_wrapper_id_becomes_heading_target_when_heading_has_none(self):
        _, sections, rendered = translate(
            '<h1>Opportunity</h1><div id="eligibility"><h2>Eligibility</h2>'
            '<p><a href="#eligibility">See eligibility</a></p></div>'
        )
        self.assertEqual(sections[0]["subsections"][0]["html_id"], "eligibility")
        self.assertEqual(rendered.a["href"], "#eligibility")

    def test_synthetic_h7_heading_is_not_unwrapped(self):
        _, sections, rendered = translate(
            '<h2>Opportunity</h2><div><div role="heading" aria-level="7" id="detail">'
            "Detail</div><p>Detail body.</p></div>"
        )
        subsection = sections[0]["subsections"][0]
        self.assertEqual(
            (subsection["name"], subsection["tag"], subsection["html_id"]),
            ("Detail", "h7", "detail"),
        )
        self.assertIn("Detail body.", rendered.get_text())

    def test_semantic_containers_and_unrelated_wrappers_are_unchanged(self):
        for html in (
            "<div><p>Ordinary body.</p></div>",
            "<table><tr><td><div><h3>Callout</h3><p>Body</p></div></td></tr></table>",
            "<ul><li><div><h3>List heading</h3></div></li></ul>",
            "<figure><div><h3>Figure heading</h3></div></figure>",
            '<div role="region"><div><h3>Region heading</h3></div></div>',
        ):
            with self.subTest(html=html):
                soup = BeautifulSoup("<body>" + html + "</body>", "html.parser")
                before = str(soup)
                unwrap_heading_containers(soup)
                self.assertEqual(str(soup), before)

    def test_wrapped_sections_retain_word_callout_interpretation(self):
        _, sections, rendered = translate(
            "<div><h1>Opportunity</h1><h2>Summary</h2><p>Intro.</p>"
            "<table><tr><td><h3>Key facts</h3><p>Important fact.</p></td></tr></table>"
            "<h2>Apply</h2><p>Submit online.</p></div>"
        )
        callouts = [s for s in sections[0]["subsections"] if s["is_callout_box"]]
        self.assertEqual(len(callouts), 1)
        self.assertEqual((callouts[0]["name"], callouts[0]["tag"]), ("Key facts", "h4"))
        self.assertIn("Important fact.", rendered.get_text())


@override_settings(DEBUG=False)
class WrappedHeadingPersistenceTests(TestCase):
    def test_import_preserves_structure_content_and_resolved_heading_links(self):
        user = get_user_model().objects.create_user(
            email="wrapped-heading@example.com",
            password="local-test",
            group="bloom",
            force_password_reset=False,
        )
        self.client.force_login(user)
        html = (
            "<p>Opdiv: CDC</p><p>Opportunity number: SYNTHETIC-1049</p>"
            "<p>Opportunity title: Wrapped heading validation</p>"
            '<div id="wrapper"><h1 id="opportunity">Opportunity</h1>'
            '<div><h2 id="eligibility">Eligibility</h2><p>Public agencies.</p>'
            '<p><a href="#eligibility">Eligibility requirements</a> '
            '<a href="#wrapper">Opportunity section</a></p></div></div>'
            "<h1>Apply</h1><p>Submit online.</p>"
        )
        response = self.client.post(
            reverse("nofos:nofo_import"), {"nofo-import": html_upload(html)}
        )
        self.assertEqual(response.status_code, 302)
        nofo = Nofo.objects.get()
        self.assertEqual(
            list(nofo.sections.order_by("order").values_list("name", flat=True)),
            ["Opportunity", "Apply"],
        )
        opportunity = nofo.sections.get(name="Opportunity")
        subsection = opportunity.subsections.get(name="Eligibility")
        rendered = BeautifulSoup(safe_markdown(subsection.body), "html.parser")
        self.assertIn("Public agencies.", rendered.get_text())
        self.assertEqual(
            [a["href"] for a in rendered.find_all("a")],
            [f"#{subsection.html_id}", f"#{opportunity.html_id}"],
        )
        edit = self.client.get(reverse("nofos:nofo_edit", args=[nofo.id]))
        self.assertEqual(edit.status_code, 200)
        self.assertContains(edit, "Public agencies.")
