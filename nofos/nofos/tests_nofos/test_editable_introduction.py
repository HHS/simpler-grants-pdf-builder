"""Ownership, source structure, rendering and editor contracts for IMPORT-065."""

from io import BytesIO
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.content_processing import ContentProcessingError, process_document_content
from nofos.forms import SubsectionEditForm
from nofos.introductory_page import INTRO_ANCHOR, imported_introduction
from nofos.models import Nofo, Section
from nofos.nofo import (
    add_headings_to_document,
    create_nofo,
    find_broken_links,
    suggest_all_nofo_fields,
)
from nofos.nofo_document_context import get_nofo_document_context
from nofos.subsection_conflicts import version_token
from nofos.tests_nofos.test_introductory_page import introductory_docx
from nofos.views import duplicate_nofo


def source_html(name="Before You Get Started", level=1, guidance=False):
    return f"""<h{level} id="original-intro">{name}</h{level}>
<p>Authored introductory opening. <a href="https://sam.gov">Registration</a>.</p>
<h{level + 1} id="authored-child">Get registered</h{level + 1}>
<p>Keep this authored deadline: October 30.</p><ul><li>Register now.</li><li>Check your account.</li></ul>
<table><tr><td>Agency</td><td>Instructions</td></tr><tr><td>HHS</td><td>Keep this table.</td></tr></table>
{'<p>In Adobe Reader, press Alt + Left Arrow on your keyboard.</p>' if guidance else ''}
<h{level}>Step 1: Review the Opportunity</h{level}><h{level + 1}>Basic information</h{level + 1}>
<p>Program description.</p><table><tr><td><h{level + 2}>Application due date</h{level + 2}><p>October 30, 2027</p></td></tr></table>
<h{level}>Step 2: Get Ready to Apply</h{level}><h{level + 1}>Registration</h{level + 1}>
<p>See <a href="#original-intro">the introduction</a> and <a href="#authored-child">registration</a>.</p>
<h{level}>Appendix A</h{level}><p>Retain appendix.</p>
<h{level + 2}>Metadata</h{level + 2}><p>OpDiv: HRSA</p><p>Opportunity name: Synthetic editable introduction</p><p>Opportunity number: HRSA-27-001</p><p>Metadata author: HHS</p>
"""


def fy27_docx(name="Before You Get Started"):
    """Small Word fixture using the cleared master's three independent signals."""
    old = ZipFile(BytesIO(introductory_docx(name=name)))
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for item in old.infolist():
            value = old.read(item.filename)
            if item.filename == "word/document.xml":
                value = value.replace(
                    b"Distinctive source text MUST NOT publish.",
                    b"Distinctive source text is editable after import.",
                )
                for text in (
                    "Opportunity Number: HRSA-27-001",
                    "Opdiv: HRSA",
                    "Opportunity Name: Synthetic introductory page review",
                    "Application Deadline: October 30, 2027",
                ):
                    value = value.replace(
                        f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>".encode(), b""
                    )
                value = value.replace(
                    b"</w:body>",
                    b'<w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr><w:r><w:t>Metadata</w:t></w:r></w:p><w:p><w:r><w:t>OpDiv: HRSA</w:t></w:r></w:p><w:p><w:r><w:t>Opportunity number: HRSA-27-001</w:t></w:r></w:p><w:p><w:r><w:t>Opportunity name: Synthetic editable introduction</w:t></w:r></w:p><w:p><w:r><w:t>Application deadline: October 30, 2027</w:t></w:r></w:p><w:p><w:r><w:t>Metadata author: HHS</w:t></w:r></w:p></w:body>',
                )
            archive.writestr(item, value)
    return output.getvalue()


class EditableIntroductionProcessingTests(SimpleTestCase):
    def process(self, html=None, policy="detect"):
        return process_document_content(
            html or source_html(),
            builder_import=True,
            editable_intro=policy,
            extract_scoped_tagline=True,
        )

    def test_compound_structure_preserves_source_and_orders_without_shifting_steps(
        self,
    ):
        for level in (1, 2):
            with self.subTest(level=level):
                result = self.process(source_html(level=level))
                self.assertTrue(imported_introduction(result.soup))
                self.assertEqual(
                    [(s["order"], s.get("role", "")) for s in result.sections],
                    [(0, "introduction"), (1, ""), (2, ""), (3, "")],
                )
                self.assertEqual(result.sections[0]["name"], "Before you get started")
                self.assertFalse(result.sections[0]["has_section_page"])
                self.assertEqual(result.sections[0]["subsections"][0]["tag"], "")
                self.assertEqual(
                    result.sections[0]["subsections"][1]["name"], "Get registered"
                )
                self.assertIn("Keep this table.", str(result.sections[0]))
                self.assertIn("OpDiv: HRSA", str(result.soup))
                self.assertNotIn("Metadata author", str(result.sections))
                self.assertIn("Retain appendix", str(result.sections[-1]))

    def test_heading_or_hierarchy_alone_never_selects_editable_mode(self):
        cases = [
            source_html().replace("<h3>Metadata</h3>", "<p>Metadata</p>"),
            source_html(name="Before You Begin"),
            source_html().replace("Basic information", "Unrecognized heading"),
            source_html().replace("Before You Get Started", "Different introduction"),
            source_html().replace(
                '<h1 id="original-intro">Before You Get Started</h1>',
                "<h1>Before You Get Started</h1><h1>Before You Get Started</h1>",
            ),
        ]
        for html in cases:
            with self.subTest(html=html[:90]):
                self.assertFalse(imported_introduction(self.process(html).soup))

    def test_default_consumers_and_generated_policy_keep_existing_removal(self):
        for builder in (True, False):
            result = process_document_content(
                source_html(name="Before You Begin"), builder_import=builder
            )
            self.assertFalse(imported_introduction(result.soup))
            self.assertNotIn("Authored introductory opening", str(result.sections))

    def test_uploaded_private_mode_attribute_cannot_override_workflow_policy(self):
        forged = (
            '<body data-nofo-introductory-content-mode="imported">'
            + source_html(name="Before You Begin")
            + "</body>"
        )
        for builder in (False, True):
            result = process_document_content(forged, builder_import=builder)
            self.assertFalse(imported_introduction(result.soup))
            self.assertNotIn("Authored introductory opening", str(result.sections))

    def test_required_reimport_accepts_legacy_name_but_rejects_missing_repeated_empty(
        self,
    ):
        self.assertTrue(
            imported_introduction(
                self.process(
                    source_html(name="Before You Begin"), policy="required"
                ).soup
            )
        )
        for html in (
            "<h1>Step 1: Review</h1><p>Only body</p>",
            "<h1>Before You Begin</h1><h1>Step 1: Review</h1>",
            source_html().replace("<h1>Step 1", "<h1>Before You Begin</h1><h1>Step 1"),
        ):
            with self.subTest(html=html[:70]), self.assertRaises(
                ContentProcessingError
            ) as caught:
                self.process(html, policy="required")
            self.assertEqual(caught.exception.code, "introductory_content_unsafe")

    def test_positive_structure_with_unmapped_prefix_rejects_instead_of_discarding(
        self,
    ):
        for prefix in (
            "<p>Important authored preface.</p>",
            "<h1>Preface</h1><p>Keep this.</p>",
        ):
            for policy in ("detect", "required"):
                with self.subTest(prefix=prefix, policy=policy), self.assertRaises(
                    ContentProcessingError
                ):
                    self.process(prefix + source_html(), policy=policy)

    def test_leading_recognized_metadata_is_extracted_not_introductory_body(self):
        result = self.process(
            "<h1>Metadata</h1><p>OpDiv: HRSA</p><p>Metadata author: HHS</p>"
            + source_html()
        )
        self.assertTrue(imported_introduction(result.soup))
        self.assertEqual(result.sections[0]["role"], "introduction")
        self.assertNotIn("Metadata author", str(result.sections))


class EditableIntroductionWorkflowTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="editable-intro@example.com",
            password=None,
            group="bloom",
            force_password_reset=False,
            is_superuser=True,
        )
        self.client.force_login(self.user)

    def create_document(self, guidance=False):
        result = process_document_content(
            source_html(guidance=guidance), builder_import=True, editable_intro="detect"
        )
        nofo = create_nofo("Synthetic editable introduction", result.sections, "HRSA")
        add_headings_to_document(nofo)
        suggest_all_nofo_fields(nofo, result.soup, first_time_import=True)
        nofo.save()
        return nofo

    def upload(self, url, data=None, filename="synthetic-fy27.docx"):
        return self.client.post(
            url,
            {
                "nofo-import": SimpleUploadedFile(
                    filename,
                    data or fy27_docx(),
                    content_type=(
                        "text/html"
                        if filename.endswith(".html")
                        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    ),
                )
            },
        )

    def test_real_docx_new_import_selects_mode_and_retains_authored_body(self):
        response = self.upload(reverse("nofos:nofo_import"))
        self.assertEqual(response.status_code, 302)
        nofo = Nofo.objects.latest("created")
        self.assertTrue(nofo.has_imported_introduction)
        self.assertEqual(nofo.sections.first().role, "introduction")
        self.assertIn(
            "Distinctive source", nofo.sections.first().subsections.first().body
        )

    def test_html_upload_retains_generated_workflow(self):
        self.client.post(
            reverse("nofos:nofo_import"),
            {
                "nofo-import": SimpleUploadedFile(
                    "test.html", source_html().encode(), content_type="text/html"
                )
            },
        )
        self.assertFalse(Nofo.objects.latest("created").has_imported_introduction)

    def test_forged_html_attribute_cannot_change_new_or_existing_record_mode(self):
        forged = (
            '<body data-nofo-introductory-content-mode="imported">'
            + source_html()
            + "</body>"
        ).encode()
        response = self.upload(
            reverse("nofos:nofo_import"), forged, filename="forged.html"
        )
        self.assertEqual(response.status_code, 302)
        nofo = Nofo.objects.latest("created")
        self.assertFalse(nofo.has_imported_introduction)
        response = self.upload(
            reverse("nofos:nofo_import_overwrite", args=[nofo.pk]),
            forged,
            filename="forged.html",
        )
        self.assertEqual(response.status_code, 302)
        nofo.refresh_from_db()
        self.assertFalse(nofo.has_imported_introduction)
        self.assertFalse(nofo.sections.filter(role="introduction").exists())

    def test_legacy_noncontiguous_orders_keep_loop_numbering_and_export_metadata(self):
        nofo = Nofo.objects.create(
            title="Legacy gaps", opdiv="HRSA", before_you_begin="none", group="bloom"
        )
        for order in (3, 9):
            Section.objects.create(
                nofo=nofo,
                name=f"Step {order}: Existing",
                order=order,
                html_id=f"old-{order}",
                has_section_page=False,
            )
        html = self.client.get(
            reverse("nofos:nofo_view", args=[nofo.pk])
        ).content.decode()
        soup = BeautifulSoup(html, "html.parser")
        self.assertIn("section--1", soup.find(id="section--old-3")["class"])
        self.assertIn("section--2", soup.find(id="section--old-9")["class"])
        self.assertNotIn("section--appendix", soup.find(id="section--old-9")["class"])
        exported = render_to_string(
            "nofos/includes/nofo_export_document.html", {"nofo": nofo}
        )
        self.assertEqual(exported.count("Opdiv: HRSA"), 1)

    def test_existing_families_variants_blank_numbers_reimport_stay_generated(self):
        for family in ("", "legacy", "get_started"):
            for variant in ("none", "full", "era", "hrsa", "sole_source"):
                with self.subTest(family=family, variant=variant):
                    nofo = Nofo.objects.create(
                        title="Existing",
                        opdiv="HRSA",
                        group="bloom",
                        number="HRSA-27-001",
                        introductory_page_family=family,
                        before_you_begin=variant,
                    )
                    response = self.upload(
                        reverse("nofos:nofo_import_overwrite", args=[nofo.pk])
                    )
                    self.assertEqual(response.status_code, 302)
                    nofo.refresh_from_db()
                    self.assertFalse(nofo.has_imported_introduction)
                    self.assertEqual(
                        (nofo.introductory_page_family, nofo.before_you_begin),
                        (family, variant),
                    )
                    self.assertEqual(
                        self.client.get(
                            reverse("nofos:nofo_edit_byb", args=[nofo.pk])
                        ).status_code,
                        200,
                    )
                    copied = duplicate_nofo(nofo)
                    self.assertEqual(
                        (
                            copied.introductory_content_mode,
                            copied.introductory_page_family,
                            copied.before_you_begin,
                        ),
                        ("generated", family, variant),
                    )

    def test_imported_reimport_rejects_missing_intro_without_archive_or_mutation(self):
        nofo = self.create_document()
        before = list(nofo.sections.values_list("id", "name"))
        response = self.upload(
            reverse("nofos:nofo_import_overwrite", args=[nofo.pk]),
            b"<h1>Step 1: Review</h1><p>body</p>",
            filename="replacement.html",
        )
        self.assertEqual(response.status_code, 422)
        self.assertContains(response, "IMPORT-INTRODUCTION-STRUCTURE", status_code=422)
        self.assertEqual(list(nofo.sections.values_list("id", "name")), before)
        self.assertEqual(Nofo.objects.filter(successor=nofo).count(), 0)

    def test_reimport_duplicate_and_archive_preserve_mode_and_role(self):
        nofo = self.create_document()
        response = self.upload(
            reverse("nofos:nofo_import_overwrite", args=[nofo.pk]),
            fy27_docx(name="Before You Begin"),
        )
        self.assertEqual(response.status_code, 302)
        if "confirm" in response.url:
            response = self.client.post(response.url)
            self.assertEqual(response.status_code, 302)
        nofo.refresh_from_db()
        self.assertTrue(nofo.has_imported_introduction)
        self.assertEqual(nofo.introductory_page_family, "get_started")
        for copied in (duplicate_nofo(nofo), Nofo.objects.get(successor=nofo)):
            self.assertTrue(copied.has_imported_introduction)
            self.assertTrue(copied.sections.first().is_introduction)

    def test_settings_hidden_and_direct_get_post_rejected(self):
        nofo = self.create_document()
        page = self.client.get(reverse("nofos:nofo_edit", args=[nofo.pk]))
        self.assertNotContains(page, reverse("nofos:nofo_edit_byb", args=[nofo.pk]))
        for method in (self.client.get, self.client.post):
            self.assertEqual(
                method(
                    reverse("nofos:nofo_edit_byb", args=[nofo.pk]),
                    {"before_you_begin": "none"},
                ).status_code,
                403,
            )
        nofo.refresh_from_db()
        self.assertNotEqual(nofo.before_you_begin, "none")

    def test_parent_role_and_position_are_fixed_and_unique(self):
        nofo = self.create_document()
        intro = nofo.sections.first()
        intro.name = "Rename attempt"
        with self.assertRaises(ValidationError):
            intro.save()
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Section.objects.create(
                nofo=nofo,
                name="Another",
                order=99,
                role="introduction",
                html_id="other",
            )

    def test_add_endnotes_preserves_intro_order_and_first_step(self):
        nofo = self.create_document()
        nofo.sections.filter(name="Appendix A").update(
            name="Appendix", html_id="appendix"
        )
        response = self.client.post(
            reverse("nofos:section_add_end_notes", args=[nofo.pk]),
            {"body": "Synthetic citation."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(nofo.sections.get(role="introduction").order, 0)
        self.assertEqual(nofo.sections.get(name__startswith="Step 1").order, 1)
        self.assertEqual(
            list(nofo.sections.values_list("name", flat=True))[-2:],
            ["Endnotes", "Appendix"],
        )

    def test_body_editor_is_headingless_and_guards_direct_heading_manipulation(self):
        nofo = self.create_document()
        body = nofo.sections.first().subsections.first()
        url = reverse("nofos:subsection_edit", args=[nofo.pk, body.section_id, body.pk])
        response = self.client.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        self.assertTrue(soup.find("input", id="name").has_attr("disabled"))
        self.assertTrue(soup.find("input", id="callout_box").has_attr("disabled"))
        self.assertIsNone(soup.find("select", attrs={"name": "tag"}))
        values = {
            "name": "",
            "tag": "",
            "body": "Updated authored opening.",
            "callout_box": False,
            "html_class": "",
            "edit_version": version_token(body),
        }
        self.assertEqual(self.client.post(url, values).status_code, 302)
        body.refresh_from_db()
        self.assertEqual(body.body, "Updated authored opening.")
        for changes in (
            {"name": "Duplicate parent", "tag": "h2"},
            {"callout_box": True},
        ):
            body.refresh_from_db()
            form = SubsectionEditForm(data={**values, **changes}, instance=body)
            self.assertFalse(form.is_valid())
        child = body.section.subsections.exclude(tag="").first()
        form = SubsectionEditForm(
            data={**values, "name": "Edited child", "tag": child.tag}, instance=child
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_rendering_single_body_toc_icon_step_integrity_and_links(self):
        nofo = self.create_document()
        nofo.before_you_begin = "none"
        nofo.save()
        page = self.client.get(reverse("nofos:nofo_view", args=[nofo.pk]))
        self.assertEqual(page.status_code, 200)
        soup = BeautifulSoup(page.content, "html.parser")
        intro = soup.find(id=INTRO_ANCHOR)
        self.assertEqual(len(soup.find_all(id=INTRO_ANCHOR)), 1)
        self.assertEqual(intro.h2.text, "Before you get started")
        self.assertIn("Authored introductory opening", intro.text)
        self.assertNotIn("If you believe you are a good candidate", intro.text)
        self.assertIsNone(intro.find(class_="section--title-page"))
        toc = soup.find(class_="toc--imported-introduction")
        self.assertIsNotNone(toc.find("svg"))
        self.assertIsNone(toc.find("ol"))
        step1 = soup.find(class_="section--1")
        self.assertIn("Basic information", step1.text)
        self.assertIn("Application due date", step1.text)
        self.assertNotIn("Program description", intro.text)
        ids = [tag["id"] for tag in soup.find_all(id=True)]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(find_broken_links(nofo), [])

    def test_guidance_suppression_preserves_authored_text_and_export_policy(self):
        for guidance in (False, True):
            nofo = self.create_document(guidance=guidance)
            intro = nofo.sections.first()
            self.assertEqual(intro.needs_navigation_help, not guidance)
            page = self.client.get(
                reverse("nofos:nofo_view", args=[nofo.pk])
            ).content.decode()
            self.assertEqual(page.count("callout-box--keyboard"), 0 if guidance else 1)
            for readability in (False, True):
                html = render_to_string(
                    "nofos/includes/nofo_export_document.html",
                    {
                        "nofo": nofo,
                        "for_readability_metrics": readability,
                        **get_nofo_document_context(nofo),
                    },
                )
                self.assertEqual(html.count("Authored introductory opening"), 1)
                self.assertNotIn("callout-box--keyboard", html)
                self.assertNotIn("If you believe you are a good candidate", html)
                self.assertEqual(html.count("Opdiv: HRSA"), 1)

    def test_metadata_edits_do_not_rewrite_source_body(self):
        nofo = self.create_document()
        before = list(nofo.sections.first().subsections.values_list("body", flat=True))
        nofo.application_deadline = "December 31, 2028"
        nofo.save()
        self.assertEqual(
            list(nofo.sections.first().subsections.values_list("body", flat=True)),
            before,
        )

    def test_native_note_reference_inside_intro_and_return_target_survive_once(self):
        html = (
            source_html()
            .replace(
                "Authored introductory opening.",
                'Authored introductory opening.<sup><a id="footnote-ref-1" href="#footnote-1">1</a></sup>',
            )
            .replace(
                "<h3>Metadata</h3>",
                '<h1>Endnotes</h1><ol><li id="footnote-1"><p>Synthetic citation. <a href="#footnote-ref-1">↑</a></p></li></ol><h3>Metadata</h3>',
            )
        )
        result = process_document_content(
            html, builder_import=True, editable_intro="detect"
        )
        nofo = create_nofo("Synthetic notes", result.sections, "HRSA")
        add_headings_to_document(nofo)
        suggest_all_nofo_fields(nofo, result.soup, first_time_import=True)
        nofo.save()
        self.assertEqual(find_broken_links(nofo), [])
        soup = BeautifulSoup(
            self.client.get(reverse("nofos:nofo_view", args=[nofo.pk])).content,
            "html.parser",
        )
        for target in ("footnote-1", "footnote-ref-1"):
            self.assertEqual(len(soup.find_all(id=target)), 1)
        self.assertIsNotNone(soup.find(id=INTRO_ANCHOR).find("a", href="#footnote-1"))

    def test_blank_and_default_existing_numbers_never_select_imported_ownership(self):
        for number in ("", "NOFO #999", "XXX-XX-XXX"):
            nofo = Nofo.objects.create(
                title="Historical",
                group="bloom",
                opdiv="HRSA",
                number=number,
                before_you_begin="none",
                introductory_page_family="legacy",
            )
            response = self.upload(
                reverse("nofos:nofo_import_overwrite", args=[nofo.pk])
            )
            self.assertEqual(response.status_code, 302)
            if "confirm" in response.url:
                self.assertEqual(self.client.post(response.url).status_code, 302)
            nofo.refresh_from_db()
            self.assertFalse(nofo.has_imported_introduction)
            self.assertEqual(nofo.before_you_begin, "none")
            self.assertEqual(nofo.introductory_page_family, "legacy")
