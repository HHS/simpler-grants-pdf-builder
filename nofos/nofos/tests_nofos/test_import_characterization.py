"""Contracts for isolating import orchestration without changing its behavior.

Synthetic HTML represents input shapes, not compatibility with a vendor editor.
Expected failures below name tracked fidelity limitations, not supported policy.
"""

from contextlib import ExitStack
from unittest import expectedFailure
from unittest.mock import patch

from bs4 import BeautifulSoup
from compare.models import CompareDocument
from composer.models import ContentGuide
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from martor.templatetags.martortags import safe_markdown

from nofos.models import Nofo
from nofos.nofo import process_nofo_html, resolve_section_heading_level
from nofos.nofo_markdown import MISSING_ALT_TEXT_ATTR, md
from nofos.views import BaseNofoImportView


def html_upload(html, filename="synthetic.html"):
    return SimpleUploadedFile(filename, html.encode(), content_type="text/html")


def translate(html):
    soup = BeautifulSoup(html, "html.parser")
    level = resolve_section_heading_level(soup)
    soup, _ = process_nofo_html(soup, level)
    sections = BaseNofoImportView.get_sections_and_subsections_from_soup(soup, level)
    bodies = [
        "".join(str(tag) for tag in subsection["body"])
        for section in sections
        for subsection in section["subsections"]
    ]
    rendered = BeautifulSoup(
        safe_markdown("\n\n".join(md(body) for body in bodies)),
        "html.parser",
    )
    return soup, sections, rendered


class CapturingImportView(BaseNofoImportView):
    def handle_nofo_create(self, request, soup, sections, filename, **kwargs):
        self.result = (soup, sections, filename, kwargs["warning_count"])
        return HttpResponse("parsed")


@override_settings(DEBUG=False)
class ImportOrchestrationTests(SimpleTestCase):
    def request(self):
        return RequestFactory().post(
            "/", {"nofo-import": html_upload("<h1>Section</h1><p>Body</p>")}
        )

    def test_order_and_mutable_results_reach_consumer_unchanged(self):
        events = []
        soup = BeautifulSoup("<p>Metadata source</p>", "html.parser")
        sections = [{"name": "Section", "subsections": []}]
        instructions = [soup.p]
        view = CapturingImportView()

        def step(name, result):
            def record(*args, **kwargs):
                events.append(name)
                return result

            return record

        def instruction_hook(**kwargs):
            self.assertIs(kwargs["sections"], sections)
            self.assertIs(kwargs["instructions_tables"], instructions)
            events.append("instructions")

        transforms = {
            "parse_uploaded_file_as_html_string": ("convert", ("html", 2)),
            "replace_chars": ("characters", "html"),
            "replace_links": ("links", "html"),
            "BeautifulSoup": ("soup", soup),
            "decompose_before_you_begin_section": ("before_you_begin", None),
            "resolve_section_heading_level": ("heading_level", "h1"),
            "process_nofo_html": ("process", (soup, instructions)),
            "add_final_subsection_to_step_3": ("step_3", None),
            "add_line_breaks_to_key_dates_values": ("key_dates", None),
        }
        with ExitStack() as stack:
            for function, (name, result) in transforms.items():
                stack.enter_context(
                    patch("nofos.views." + function, side_effect=step(name, result))
                )
            stack.enter_context(
                patch.object(
                    view,
                    "get_sections_and_subsections_from_soup",
                    side_effect=step("sections", sections),
                )
            )
            stack.enter_context(
                patch.object(view, "add_instructions_to_subsections", instruction_hook)
            )
            self.assertEqual(view.post(self.request()).status_code, 200)
        self.assertEqual(
            events,
            [
                "convert",
                "characters",
                "links",
                "soup",
                "before_you_begin",
                "heading_level",
                "process",
                "sections",
                "instructions",
                "step_3",
                "key_dates",
            ],
        )
        self.assertIs(view.result[0], soup)
        self.assertIs(view.result[1], sections)
        self.assertEqual(view.result[2:], ("synthetic.html", 2))

    def test_instruction_hook_failure_is_owned_by_parse_handler(self):
        view = CapturingImportView()
        with (
            patch.object(
                view,
                "add_instructions_to_subsections",
                side_effect=RuntimeError("hook"),
            ),
            patch("nofos.views.log_exception") as log,
            patch(
                "nofos.views.render_import_server_error",
                return_value=HttpResponse(status=500),
            ),
        ):
            self.assertEqual(view.post(self.request()).status_code, 500)
        self.assertEqual(
            log.call_args.kwargs["context"],
            "BaseNofoImportView:Exception:IMPORT-UNEXPECTED",
        )

    def test_postprocessing_failures_remain_outside_parse_handler(self):
        for function in (
            "add_final_subsection_to_step_3",
            "add_line_breaks_to_key_dates_values",
        ):
            with (
                self.subTest(function=function),
                patch(
                    "nofos.views." + function, side_effect=RuntimeError("postprocess")
                ),
                patch("nofos.views.log_exception") as log,
            ):
                with self.assertRaisesRegex(RuntimeError, "postprocess"):
                    CapturingImportView().post(self.request())
                log.assert_not_called()

    def test_no_sections_keeps_validation_code(self):
        with self.assertRaises(ValidationError) as error:
            BaseNofoImportView.get_sections_and_subsections_from_soup(
                BeautifulSoup("<p>Body</p>", "html.parser"), "h2"
            )
        self.assertEqual(error.exception.code, "no_sections")

    def test_metadata_preamble_retained_outside_section_bodies(self):
        soup, sections, _ = translate(
            "<p>Opdiv: CDC</p><p>Metadata source</p><h1>Section</h1>"
            "<h2>Summary</h2><p>Body</p>"
        )
        self.assertIn("Metadata source", str(soup))
        self.assertNotIn("Metadata source", str(sections))
        self.assertIn("Body", str(sections))


@override_settings(DEBUG=False)
class ImportConsumerCharacterizationTests(TestCase):
    def test_synthetic_html_persists_through_all_three_consumers(self):
        user = get_user_model().objects.create_user(
            email="characterization@example.com",
            password="local-test",
            group="bloom",
            force_password_reset=False,
            is_composer_admin=True,
        )
        self.client.force_login(user)
        html = (
            "<p>Opdiv: CDC</p><p>Opportunity number: SYNTHETIC-001</p>"
            "<p>Opportunity title: Synthetic import</p>"
            "<h1>Step 1: Review the opportunity</h1><h2>Summary</h2><p>Test body.</p>"
        )
        for route, model in (
            ("nofos:nofo_import", Nofo),
            ("composer:composer_import", ContentGuide),
            ("compare:compare_import", CompareDocument),
        ):
            with self.subTest(route=route):
                response = self.client.post(
                    reverse(route), {"nofo-import": html_upload(html)}
                )
                self.assertEqual(response.status_code, 302)
                document = model.objects.get()
                self.assertEqual(document.filename, "synthetic.html")
                section = document.sections.get()
                self.assertEqual(section.name, "Step 1: Review the opportunity")
                subsection = section.subsections.get()
                self.assertEqual(subsection.name, "Summary")
                self.assertIn("Test body.", subsection.body)


@override_settings(DEBUG=False)
class ImportFidelityCharacterizationTests(SimpleTestCase):
    prefix = "<h2>Opportunity</h2><h3>Funding</h3>"

    # Shared with the expected failures so unrelated parser errors fail normally.
    fidelity_inputs = {
        "wrapped_main_heading": "<div><h2>Opportunity</h2><h3>Eligibility</h3><p>Public agencies.</p></div><h2>Apply</h2><p>Submit online.</p>",
        "wrapped_subheading": "<h2>Opportunity</h2><div><h3>Eligibility</h3><p>Public agencies.</p></div>",
        "captioned_table": prefix
        + "<table><caption>Awards</caption><tr><td>Program</td><td>Amount</td></tr><tr><td>Training</td><td>0</td></tr></table>",
        "bare_image": prefix + '<img src="logo.png" alt="Agency logo">',
        "list_item_anchor": prefix
        + '<p><a href="#note-1">Read note</a></p><ol><li id="note-1">Source</li></ol>',
    }

    def test_known_lossy_inputs_complete_translation(self):
        for shape, html in self.fidelity_inputs.items():
            with self.subTest(shape=shape):
                _, sections, rendered = translate(html)
                self.assertTrue(sections)
                self.assertIsInstance(rendered, BeautifulSoup)

    def test_direct_and_figure_tables_keep_values_with_different_header_policy(self):
        table = "<table><tr><td>Program</td><td>Amount</td></tr><tr><td>Training</td><td>0</td></tr></table>"
        for wrapped in (False, True):
            with self.subTest(wrapped=wrapped):
                source = "<figure>" + table + "</figure>" if wrapped else table
                soup, _, rendered = translate(self.prefix + source)
                self.assertEqual(len(soup.find_all("th")), 0 if wrapped else 2)
                self.assertIsNotNone(rendered.table)
                self.assertIn("Training", rendered.get_text())
                self.assertIn("0", rendered.get_text())

    def test_single_cell_table_is_intentionally_a_callout(self):
        _, sections, rendered = translate(
            self.prefix + "<table><tr><td>$100</td></tr></table>"
        )
        self.assertTrue(
            any(
                subsection["is_callout_box"]
                for subsection in sections[0]["subsections"]
            )
        )
        self.assertIn("$100", rendered.get_text())

    def test_merged_table_keeps_spans_and_values(self):
        _, _, rendered = translate(
            self.prefix
            + '<table><tr><th colspan="2">Awards</th></tr><tr><td rowspan="2">Training</td><td>0</td></tr><tr><td>100</td></tr></table>'
        )
        self.assertEqual(rendered.th["colspan"], "2")
        self.assertEqual(rendered.td["rowspan"], "2")
        self.assertIn("100", rendered.get_text())

    def test_paragraph_images_and_explicit_bookmark_survive(self):
        html = (
            self.prefix
            + '<p><img src="logo.png" alt="Agency logo"></p><p><img src="decoration.png" alt=""></p><p><img src="missing.png"></p><p><a href="#note-1">Read note</a></p><p><a id="note-1"></a>Source</p>'
        )
        soup = BeautifulSoup(html, "html.parser")
        soup, _ = process_nofo_html(soup, resolve_section_heading_level(soup))
        self.assertFalse(
            soup.find("img", src="decoration.png").has_attr(MISSING_ALT_TEXT_ATTR)
        )
        self.assertTrue(
            soup.find("img", src="missing.png").has_attr(MISSING_ALT_TEXT_ATTR)
        )
        _, _, rendered = translate(html)
        self.assertEqual(len(rendered.find_all("img")), 3)
        self.assertEqual(rendered.find("img", src="logo.png")["alt"], "Agency logo")
        self.assertEqual(rendered.find("img", src="decoration.png")["alt"], "")
        self.assertEqual(rendered.find("img", src="missing.png")["alt"], "")
        self.assertIsNotNone(rendered.find(id="note-1"))
        self.assertEqual(rendered.find("a", string="Read note")["href"], "#note-1")

    def test_explicit_form_projection_distinguishes_zero_false_and_missing(self):
        # Projection belongs to the caller, not to Builder or a vendor runtime.
        values = {"amount": 0, "match": False}
        html = (
            self.prefix
            + f'<p>Amount: ${values["amount"]}</p><p>Match required: {"Yes" if values["match"] else "No"}</p><p>Notes: Not supplied</p><table><tr><th>Activity</th><th>Amount</th></tr><tr data-source-key="r1"><td>Training</td><td>$0</td></tr></table>'
        )
        _, sections, rendered = translate(html)
        for text in (
            "Amount: $0",
            "Match required: No",
            "Notes: Not supplied",
            "Training",
        ):
            self.assertIn(text, rendered.get_text())
        self.assertIn("data-source-key", str(sections))
        self.assertNotIn("data-source-key", str(rendered))

    @expectedFailure
    def test_wrapped_main_heading_keeps_content_issue_1049(self):
        _, _, rendered = translate(self.fidelity_inputs["wrapped_main_heading"])
        self.assertIn("Public agencies.", rendered.get_text())

    @expectedFailure
    def test_wrapped_subheading_is_structured_issue_1049(self):
        _, sections, _ = translate(self.fidelity_inputs["wrapped_subheading"])
        self.assertIn("Eligibility", [s["name"] for s in sections[0]["subsections"]])

    def test_captioned_table_stays_tabular_issue_1050(self):
        _, _, rendered = translate(self.fidelity_inputs["captioned_table"])
        self.assertIsNotNone(rendered.table)

    @expectedFailure
    def test_bare_image_survives_issue_1051(self):
        _, _, rendered = translate(self.fidelity_inputs["bare_image"])
        self.assertIsNotNone(rendered.find("img", src="logo.png"))

    @expectedFailure
    def test_list_item_anchor_survives_issue_1052(self):
        _, _, rendered = translate(self.fidelity_inputs["list_item_anchor"])
        self.assertIsNotNone(rendered.find(id="note-1"))
