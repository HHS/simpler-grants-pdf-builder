"""Structured trailing metadata, legacy fallback, and saved-record contracts."""

from io import BytesIO
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

from bs4 import BeautifulSoup
from compare.models import CompareDocument
from compare.views import CompareImportView
from composer.models import ContentGuide
from composer.views import ComposerImportView
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, Section, Subsection
from nofos.nofo import (
    add_headings_to_document,
    builder_import_content,
    create_nofo,
    metadata_block_fields,
    parse_uploaded_file_as_html_string,
    recognized_metadata_block,
    suggest_all_nofo_fields,
    suggest_nofo_agency,
    suggest_nofo_author,
    suggest_nofo_opdiv,
    suggest_nofo_opportunity_number,
    suggest_nofo_subagency,
    suggest_nofo_subagency2,
    suggest_nofo_title,
)
from nofos.tests_nofos.test_endnote_import import (
    DOCX_CONTENT_TYPE,
    assert_internal_endnote_links_are_reciprocal,
    native_notes_docx,
    process_html_to_sections,
    render_stored_document,
)


def metadata_docx(
    *,
    legacy=False,
    opdiv="HHS",
    legacy_intro=False,
    number="TEST-1096",
    author="Example Office",
):
    """Real Word headings, split inline runs, appendix and native notes."""
    fields = (
        f"<w:p><w:r><w:t>OpDiv: {opdiv}</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Agency: Synthetic Agency</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Sub Agency: Bureau</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Sub Agency 2: Office</w:t></w:r></w:p>"
        "<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Opportunity </w:t></w:r>"
        "<w:r><w:t>name: Synthetic: trailing metadata</w:t></w:r></w:p>"
        f"<w:p><w:r><w:t>Opportunity number: {number}</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Application deadline: October 31, 2026</w:t></w:r></w:p>"
        f"<w:p><w:r><w:t>Metadata author: {author}</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Metadata subject: Research: community health</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Metadata keywords: research, health</w:t></w:r></w:p>"
    ).encode()
    with ZipFile(BytesIO(native_notes_docx())) as source:
        files = {name: source.read(name) for name in source.namelist()}
    if legacy:
        # Legacy labels need not be run-split; keep their historical scanner.
        fields = fields.replace(
            b"<w:r><w:rPr><w:b/></w:rPr><w:t>Opportunity </w:t></w:r><w:r><w:t>name:",
            b"<w:r><w:t>Opportunity name:",
        )
        files["word/document.xml"] = files["word/document.xml"].replace(
            b"<w:body>", b"<w:body>" + fields
        )
    else:
        # Establish precedence against the front-page values the old scanner
        # would incorrectly select. They must not contaminate the final block.
        files["word/document.xml"] = files["word/document.xml"].replace(
            b"<w:body>",
            b"<w:body><w:p><w:r><w:t>OpDiv: NIH</w:t></w:r></w:p>"
            b"<w:p><w:r><w:t>Agency: Front-page example</w:t></w:r></w:p>"
            b"<w:p><w:r><w:t>Opportunity number: OLD-EXAMPLE</w:t></w:r></w:p>",
        )
        block = (
            b'<w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr>'
            b"<w:r><w:t>Metadata</w:t></w:r></w:p>"
            + fields
            + b'<w:p><w:pPr><w:pStyle w:val="Heading4"/></w:pPr>'
            b"<w:r><w:t>Appendix</w:t></w:r></w:p>"
            b"<w:p><w:r><w:t>Agency: Appendix example, not metadata</w:t></w:r></w:p>"
        )
        if legacy_intro:
            block = (
                b'<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr>'
                b"<w:r><w:t>Before You Begin</w:t></w:r></w:p>"
                b"<w:p><w:r><w:t>Source registration prose.</w:t></w:r></w:p>" + block
            )
        files["word/document.xml"] = files["word/document.xml"].replace(
            b"<w:sectPr/>", block + b"<w:sectPr/>"
        )
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()


def parse_fixture(*, legacy=False, opdiv="HHS"):
    upload = SimpleUploadedFile(
        "synthetic-metadata.docx",
        metadata_docx(legacy=legacy, opdiv=opdiv),
        content_type=DOCX_CONTENT_TYPE,
    )
    html, _ = parse_uploaded_file_as_html_string(upload)
    return process_html_to_sections(html)


class MetadataBlockTests(TestCase):
    def soup(self, text):
        return BeautifulSoup(text, "html.parser")

    def test_content_copy_consumes_all_recognized_blocks_without_losing_authority(self):
        source = self.soup(
            "<h2>Program</h2><p>Agency: Front</p><h3>Metadata</h3>"
            "<p>OpDiv: NIH</p><p>Agency: Earlier</p><p></p>"
            "<h3>Metadata</h3><p><strong>OpDiv:</strong> HHS</p>"
            "<p>Agency: </p><p>Agency: Later</p><p></p>"
            "<h3>Metadata</h3><p>Ordinary metadata discussion.</p>"
        )
        before = str(source)
        content = builder_import_content(source)
        self.assertEqual(str(source), before)
        self.assertEqual(suggest_nofo_agency(source), "")
        self.assertEqual(suggest_nofo_opdiv(source), "HHS")
        self.assertEqual(len(content.find_all("h3")), 1)
        self.assertIn("Ordinary metadata discussion.", str(content))
        self.assertNotIn("Earlier", str(content))
        self.assertNotIn("Later", str(content))

    def test_consumption_uses_every_supported_heading_and_exact_boundaries(self):
        for level in range(1, 8):
            heading = (
                f"<h{level}> mETADATA </h{level}>"
                if level < 7
                else '<div role="heading" aria-level="7">Metadata</div>'
            )
            for boundary in (
                "<h1>Appendix</h1>",
                "<h3>Appendix</h3>",
                "<h6>Appendix</h6>",
                "<p>Unrelated prose.</p>",
                "<ul><li>List content</li></ul>",
                "<table><tr><td>Table content</td></tr></table>",
                '<ol><li id="footnote-1">Native note</li></ol>',
                '<p><img alt="Program diagram" src="diagram.png"/></p>',
                "<p><svg><title>Program diagram</title></svg></p>",
            ):
                with self.subTest(level=level, boundary=boundary):
                    source = self.soup(
                        "<h2>Program</h2>"
                        + heading
                        + "<p></p><p>OpDiv: HHS</p><p>Agency: </p><p></p>"
                        + boundary
                        + "<p>Agency: Outside</p>"
                    )
                    content = builder_import_content(source)
                    self.assertIn(boundary, str(content))
                    self.assertIn("Agency: Outside", str(content))
                    self.assertIsNone(recognized_metadata_block(content))
                    self.assertEqual(suggest_nofo_agency(source), "")

    def test_consumed_anchor_links_keep_text_and_surviving_destinations(self):
        source = self.soup(
            '<h2>Program</h2><p><a href="#meta">Metadata link</a> '
            '<a href="#field">field link</a> <a href="#appendix">appendix link</a></p>'
            '<h3 id="meta">Metadata</h3><p id="field">OpDiv: HHS</p>'
            '<h4 id="appendix">Appendix</h4><p>Keep content.</p>'
        )
        content = builder_import_content(source)
        self.assertIn("Metadata link", content.get_text())
        self.assertIn("field link", content.get_text())
        self.assertIsNone(content.find("a", href="#meta"))
        self.assertIsNone(content.find("a", href="#field"))
        self.assertIsNotNone(content.find("a", href="#appendix"))

    def test_unrecognized_mentions_and_legacy_are_not_consumed(self):
        for text in (
            "<h3>Metadata</h3><p>Ordinary prose.</p>",
            "<p>Metadata</p><p>Agency: Legacy</p>",
            "<h3>Metadata details</h3><p>OpDiv: HHS</p>",
        ):
            source = self.soup(text)
            self.assertEqual(str(builder_import_content(source)), str(source))

    def test_heading_levels_and_normalized_inline_labels(self):
        for level in range(1, 8):
            heading = (
                f"<h{level}>  mEtAdAtA </h{level}>"
                if level < 7
                else ('<div role="heading" aria-level="7">Metadata</div>')
            )
            with self.subTest(level=level):
                soup = self.soup(
                    heading + "<p><strong>OPPORTUNITY</strong>\u00a0name : A: B</p>"
                    "<p>Sub   Agency 2: Office</p>"
                )
                self.assertEqual(suggest_nofo_title(soup), "A: B")
                self.assertEqual(suggest_nofo_subagency2(soup), "Office")

    def test_boundary_stops_at_every_heading_level_and_preserves_source(self):
        for end in (
            "<h2>Appendix</h2>",
            "<h3>Appendix</h3>",
            "<h4>Appendix</h4>",
            "<p>Unrelated prose.</p>",
            "<ol><li>Note</li></ol>",
            "<table><tr><td>Example</td></tr></table>",
        ):
            soup = self.soup(
                "<h3>Metadata</h3><p>OpDiv: HHS</p>" + end + "<p>Agency: Outside</p>"
            )
            before = str(soup)
            self.assertEqual(suggest_nofo_agency(soup), "")
            self.assertEqual(str(soup), before)

    def test_incidental_metadata_does_not_change_legacy_fallback(self):
        for mention in (
            "<p>Metadata</p>",
            "<h3>Metadata</h3><p>About this data.</p>",
            "<h3>Metadata details</h3>",
            "<h3>Metadata</h3><h4>Other</h4>",
        ):
            soup = self.soup("<p>Agency: Legacy</p>" + mention)
            self.assertIsNone(recognized_metadata_block(soup))
            self.assertEqual(suggest_nofo_agency(soup), "Legacy")

    def test_absent_and_blank_fields_never_borrow_legacy_values(self):
        soup = self.soup(
            "<p>OpDiv: NIH</p><p>Agency: Legacy</p>"
            "<p>Opportunity number: OLD-1</p><h3>Metadata</h3>"
            "<p>OpDiv:</p><p>Agency: </p>"
        )
        self.assertEqual(suggest_nofo_opdiv(soup), "")
        self.assertEqual(suggest_nofo_agency(soup), "")
        self.assertEqual(suggest_nofo_opportunity_number(soup), "NOFO #999")

    def test_last_block_first_label_policy_does_not_merge_blocks(self):
        soup = self.soup(
            "<h3>Metadata</h3><p>OpDiv: NIH</p><p>Agency: Old</p>"
            "<h3>Metadata</h3><p>Agency: </p><p></p><p>Agency: Later</p>"
        )
        self.assertEqual(recognized_metadata_block(soup), {"agency": ""})
        self.assertEqual(suggest_nofo_opdiv(soup), "")
        self.assertIsNotNone(metadata_block_fields(soup.find_all("h3")[1]))

    def test_sample_placeholders_are_normalized_only_for_pdf_fields(self):
        soup = self.soup(
            "<h3>Metadata</h3><p>OpDiv: {Insert name of awarding agency.}</p>"
            "<p>Agency: {Insert the level below awarding agency.}</p>"
            "<p>Opportunity name: {Insert opportunity name.}</p>"
            "<p>Opportunity number: {Insert opportunity number.}</p>"
            "<p>Application deadline: {Insert application deadline date.}</p>"
            "<p>Metadata author: {Same as OpDiv.}</p>"
            "<p>Metadata subject: {Prompt to enter or offer AI to help create it.}</p>"
            "<p>Metadata keywords: {Separate with commas.}</p>"
        )
        self.assertEqual(suggest_nofo_opdiv(soup), "{Insert name of awarding agency.}")
        self.assertEqual(
            suggest_nofo_agency(soup), "{Insert the level below awarding agency.}"
        )
        self.assertEqual(suggest_nofo_author(soup), "")
        nofo = Nofo(
            title="Existing", opdiv="HHS", number="OLD", theme="portrait-cdc-blue"
        )
        suggest_all_nofo_fields(nofo, soup, first_time_import=False)
        self.assertEqual((nofo.author, nofo.subject, nofo.keywords), ("", "", ""))
        self.assertEqual(nofo.number, "{Insert opportunity number.}")
        self.assertEqual(nofo.title, "{Insert opportunity name.}")
        self.assertEqual(
            nofo.application_deadline, "{Insert application deadline date.}"
        )
        self.assertEqual(nofo.theme, "portrait-cdc-blue")

    def test_legacy_opdiv_continuation_and_spaced_aliases(self):
        soup = self.soup(
            "<p>OpDiv:</p><p>HRSA</p><p>Agency: HHS</p>"
            "<p>Sub Agency: Bureau</p><p>Sub Agency 2: Office</p>"
        )
        self.assertEqual(suggest_nofo_opdiv(soup), "HRSA")
        self.assertEqual(suggest_nofo_subagency(soup), "Bureau")
        self.assertEqual(suggest_nofo_subagency2(soup), "Office")
        self.assertEqual(
            suggest_nofo_opdiv(self.soup("<p>OpDiv:</p><p>Agency: HHS</p>")), ""
        )

    def test_resolved_fields_drive_theme_and_unrelated_tagline_stays_legacy(self):
        soup = self.soup(
            "<p>OpDiv: NIH</p><p>Tagline: Keep legacy tagline</p>"
            "<h3>Metadata</h3><p>OpDiv: HRSA</p><p>Opportunity number: TEST-1096</p>"
        )
        nofo = Nofo(title="Existing", opdiv="HHS", group="bloom")
        suggest_all_nofo_fields(nofo, soup, first_time_import=True)
        self.assertEqual(nofo.theme, "portrait-hrsa-white")
        self.assertEqual(nofo.tagline, "Keep legacy tagline")


class MetadataWordImportTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="metadata-test@example.com",
            password="synthetic-test",
            group="bloom",
            force_password_reset=False,
        )
        self.client.force_login(self.user)

    def upload(self, *, legacy=False, opdiv="HHS", legacy_intro=False, **metadata):
        return SimpleUploadedFile(
            "synthetic-metadata.docx",
            metadata_docx(
                legacy=legacy, opdiv=opdiv, legacy_intro=legacy_intro, **metadata
            ),
            content_type=DOCX_CONTENT_TYPE,
        )

    def test_acl_word_import_selects_acl_theme_from_resolved_opdiv(self):
        opdiv = "Administration for Community Living (ACL)"
        for legacy in (False, True):
            for number in ("", "{Insert opportunity number.}", "HHS-2027-001"):
                with self.subTest(legacy=legacy, number=number):
                    response = self.client.post(
                        reverse("nofos:nofo_import"),
                        {
                            "nofo-import": self.upload(
                                legacy=legacy, opdiv=opdiv, number=number, author=opdiv
                            )
                        },
                    )
                    self.assertEqual(response.status_code, 302)
                    nofo = Nofo.objects.latest("created")
                    self.assertEqual((nofo.opdiv, nofo.author), (opdiv, opdiv))
                    self.assertEqual(nofo.theme, "portrait-acl-white")
                    self.assertEqual(nofo.cover, "nofo--cover-page--text")

    def test_acl_word_reimport_keeps_saved_design_even_with_default_number(self):
        opdiv = "Administration for Community Living (ACL)"
        for theme in ("portrait-nih-white", "portrait-cdc-blue"):
            with self.subTest(theme=theme):
                nofo = Nofo.objects.create(
                    title="Existing ACL opportunity",
                    number="NOFO #999",
                    opdiv=opdiv,
                    group="bloom",
                    theme=theme,
                    cover="nofo--cover-page--medium",
                    before_you_begin="era",
                )
                response = self.client.post(
                    reverse("nofos:nofo_import_overwrite", args=[nofo.pk]),
                    {"nofo-import": self.upload(opdiv=opdiv, number="", author=opdiv)},
                )
                self.assertEqual(response.status_code, 302)
                nofo.refresh_from_db()
                self.assertEqual((nofo.opdiv, nofo.author), (opdiv, opdiv))
                self.assertEqual(
                    (nofo.theme, nofo.cover, nofo.before_you_begin),
                    (theme, "nofo--cover-page--medium", "era"),
                )

    def test_new_and_legacy_real_word_uploads_fill_all_fields_and_keep_notes(self):
        for legacy in (False, True):
            with self.subTest(legacy=legacy):
                response = self.client.post(
                    reverse("nofos:nofo_import"),
                    {"nofo-import": self.upload(legacy=legacy)},
                )
                self.assertEqual(response.status_code, 302)
                nofo = Nofo.objects.get(
                    title="Synthetic: trailing metadata", successor__isnull=True
                )
                self.assertEqual(
                    (nofo.opdiv, nofo.agency, nofo.subagency, nofo.subagency2),
                    ("HHS", "Synthetic Agency", "Bureau", "Office"),
                )
                self.assertEqual(
                    (nofo.number, nofo.application_deadline),
                    ("TEST-1096", "October 31, 2026"),
                )
                self.assertEqual(
                    (nofo.author, nofo.subject, nofo.keywords),
                    (
                        "Example Office",
                        "Research: community health",
                        "research, health",
                    ),
                )
                bodies = " ".join(
                    Subsection.objects.filter(section__nofo=nofo).values_list(
                        "body", flat=True
                    )
                )
                self.assertIn("Footnote citation.", bodies)
                self.assertIn("Endnote citation.", bodies)
                self.assertIn("footnote", bodies)
                assert_internal_endnote_links_are_reciprocal(
                    self, render_stored_document(nofo)
                )
                if not legacy:
                    self.assertIn("Appendix example, not metadata", bodies)
                    self.assertFalse(
                        Subsection.objects.filter(
                            section__nofo=nofo, name="Metadata"
                        ).exists()
                    )
                    self.assertNotIn("Metadata author:", bodies)
                nofo.delete()

    def test_manual_endnotes_following_metadata_keep_their_links(self):
        soup, sections = process_html_to_sections(
            "<p>OpDiv: NIH</p><h2>Program</h2><p>Application claim [1].</p>"
            "<h3>Metadata</h3><p>OpDiv: HHS</p><p>Agency: Actual agency</p>"
            "<h2>Endnotes</h2><p>[1] Manual citation.</p>"
        )
        nofo = create_nofo("Manual notes", sections, suggest_nofo_opdiv(soup))
        add_headings_to_document(nofo)
        suggest_all_nofo_fields(nofo, soup, first_time_import=True)
        self.assertEqual(nofo.agency, "Actual agency")
        assert_internal_endnote_links_are_reciprocal(self, render_stored_document(nofo))

    def test_legacy_intro_cleanup_preserves_lower_metadata_heading_and_authority(self):
        response = self.client.post(
            reverse("nofos:nofo_import"),
            {"nofo-import": self.upload(legacy_intro=True)},
        )
        self.assertEqual(response.status_code, 302)
        nofo = Nofo.objects.get()
        self.assertEqual(
            (nofo.opdiv, nofo.agency, nofo.number),
            ("HHS", "Synthetic Agency", "TEST-1096"),
        )
        self.assertFalse(
            Subsection.objects.filter(section__nofo=nofo, name="Metadata").exists()
        )
        bodies = " ".join(
            Subsection.objects.filter(section__nofo=nofo).values_list("body", flat=True)
        )
        self.assertNotIn("Source registration prose.", bodies)
        self.assertIn("Appendix example, not metadata", bodies)

    def test_blank_structured_opdiv_blocks_import_instead_of_borrowing_front_page(self):
        response = self.client.post(
            reverse("nofos:nofo_import"), {"nofo-import": self.upload(opdiv="")}
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Nofo.objects.exists())

    def test_confirmation_keeps_extraction_source_but_consumes_stored_content(self):
        nofo = Nofo.objects.create(
            title="Saved",
            number="OLD-EXAMPLE",
            opdiv="HHS",
            group="bloom",
            status="draft",
            theme="portrait-cdc-blue",
            before_you_begin="sole_source",
        )
        section = Section.objects.create(nofo=nofo, name="Original", order=1)
        Subsection.objects.create(section=section, name="", body="Archive me", order=1)
        url = reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk})
        response = self.client.post(
            url, {"nofo-import": self.upload(legacy_intro=True)}
        )
        self.assertRedirects(
            response,
            reverse("nofos:nofo_import_confirm_overwrite", kwargs={"pk": nofo.pk}),
        )
        captured = self.client.session["reimport_data"]
        self.assertIn("Metadata", captured["soup"])
        self.assertEqual(captured["new_opportunity_number"], "TEST-1096")
        self.assertEqual(nofo.sections.get().subsections.get().body, "Archive me")
        response = self.client.post(
            reverse("nofos:nofo_import_confirm_overwrite", kwargs={"pk": nofo.pk})
        )
        self.assertEqual(response.status_code, 302)
        nofo.refresh_from_db()
        self.assertEqual(
            (nofo.number, nofo.agency, nofo.author),
            ("TEST-1096", "Synthetic Agency", "Example Office"),
        )
        self.assertEqual(
            (nofo.theme, nofo.before_you_begin, nofo.introductory_page_family),
            ("portrait-cdc-blue", "sole_source", ""),
        )
        self.assertFalse(
            Subsection.objects.filter(section__nofo=nofo, name="Metadata").exists()
        )
        archive = Nofo.objects.get(successor=nofo)
        self.assertEqual(archive.sections.get().subsections.get().body, "Archive me")

    def test_metadata_h1_does_not_change_program_heading_resolution(self):
        with patch(
            "nofos.views.parse_uploaded_file_as_html_string",
            return_value=(
                "<h2>Program</h2><h3>Summary</h3><p>Keep program content.</p>"
                "<h1>Metadata</h1><p>OpDiv: HHS</p><p>Agency: Captured agency</p>"
                "<h2>Appendix</h2><p>Keep appendix.</p>",
                0,
            ),
        ):
            response = self.client.post(
                reverse("nofos:nofo_import"), {"nofo-import": self.upload()}
            )
        self.assertEqual(response.status_code, 302)
        nofo = Nofo.objects.get()
        self.assertEqual(nofo.agency, "Captured agency")
        self.assertEqual(
            list(nofo.sections.values_list("name", flat=True)), ["Program", "Appendix"]
        )

    def test_source_absent_from_editor_public_and_word_export_html(self):
        from django.template.loader import render_to_string

        from nofos.nofo_document_context import get_nofo_document_context

        self.client.post(reverse("nofos:nofo_import"), {"nofo-import": self.upload()})
        nofo = Nofo.objects.get()
        for url_name in ("nofos:nofo_edit", "nofos:nofo_view", "nofos:nofo_export"):
            response = self.client.get(reverse(url_name, kwargs={"pk": nofo.pk}))
            self.assertEqual(response.status_code, 200)
            rendered = BeautifulSoup(response.content, "html.parser")
            self.assertFalse(
                any(
                    h.get_text(strip=True).casefold() == "metadata"
                    for h in rendered.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
                )
            )
        html = render_to_string(
            "nofos/includes/nofo_export_document.html",
            {"nofo": nofo, **get_nofo_document_context(nofo)},
        )
        # Word export intentionally adds existing metadata fields in its own
        # Basic information block. Only the duplicate imported source is gone.
        headings = BeautifulSoup(html, "html.parser").find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6"]
        )
        self.assertFalse(
            any(h.get_text(strip=True).casefold() == "metadata" for h in headings)
        )
        self.assertIn("Appendix example, not metadata", html)

    def test_word_bookmarks_into_consumed_heading_and_fields_become_plain_text(self):
        with patch(
            "nofos.views.parse_uploaded_file_as_html_string",
            return_value=(
                '<h2>Program</h2><p><a href="#metadata-bookmark">Metadata link</a> '
                '<a href="#field-bookmark">Field link</a></p>'
                '<p><a id="metadata-bookmark"></a></p><h3>Metadata</h3>'
                '<p><a id="field-bookmark"></a>OpDiv: HHS</p>'
                "<p>Agency: Captured</p><h4>Appendix</h4><p>Keep me.</p>",
                0,
            ),
        ):
            response = self.client.post(
                reverse("nofos:nofo_import"), {"nofo-import": self.upload()}
            )
        self.assertEqual(response.status_code, 302)
        nofo = Nofo.objects.get()
        rendered = render_stored_document(nofo)
        self.assertIn("Metadata link", rendered.get_text())
        self.assertIn("Field link", rendered.get_text())
        self.assertIsNone(rendered.find("a", string="Metadata link"))
        self.assertIsNone(rendered.find("a", string="Field link"))
        self.assertIn("Keep me.", rendered.get_text())

    def test_reimport_keeps_record_and_saved_design_then_rolls_back_failures(self):
        nofo = Nofo.objects.create(
            title="Saved title",
            number="TEST-1096",
            opdiv="HHS",
            group="bloom",
            status="draft",
            theme="portrait-cdc-blue",
            cover="nofo--cover-page--medium",
            before_you_begin="sole_source",
        )
        section = Section.objects.create(nofo=nofo, name="Old content", order=1)
        Subsection.objects.create(section=section, name="", body="Old body", order=1)
        url = reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk})
        for legacy in (True, False):
            response = self.client.post(
                url, {"nofo-import": self.upload(legacy=legacy)}
            )
            self.assertEqual(response.status_code, 302)
            nofo.refresh_from_db()
            self.assertEqual(nofo.agency, "Synthetic Agency")
            self.assertEqual(
                (nofo.theme, nofo.cover, nofo.before_you_begin),
                ("portrait-cdc-blue", "nofo--cover-page--medium", "sole_source"),
            )
        saved_state = (
            nofo.agency,
            nofo.title,
            nofo.sections.count(),
            Nofo.objects.count(),
        )
        with patch(
            "nofos.views.suggest_all_nofo_fields",
            side_effect=ValueError("synthetic failure"),
        ):
            response = self.client.post(url, {"nofo-import": self.upload()})
        self.assertEqual(response.status_code, 500)
        nofo.refresh_from_db()
        self.assertEqual(
            (nofo.agency, nofo.title, nofo.sections.count(), Nofo.objects.count()),
            saved_state,
        )

    def test_shared_consumers_keep_filename_titles_and_resolve_opdiv(self):
        for legacy in (True, False):
            for view_class, document_model, expected_title in (
                (ComposerImportView, ContentGuide, "shared-metadata.docx"),
                (CompareImportView, CompareDocument, "shared-metadata"),
            ):
                with self.subTest(legacy=legacy, consumer=view_class.__name__):
                    soup, sections = parse_fixture(legacy=legacy, opdiv="HRSA")
                    request = RequestFactory().post("/")
                    request.user = self.user
                    response = view_class().handle_nofo_create(
                        request, soup, sections, "shared-metadata.docx"
                    )
                    self.assertEqual(response.status_code, 302)
                    document = document_model.objects.get()
                    self.assertEqual(
                        (document.title, document.opdiv), (expected_title, "HRSA")
                    )
                    document.delete()

    def test_actual_shared_import_posts_retain_metadata_source_content(self):
        from compare.models import CompareSubsection
        from composer.models import ContentGuideSubsection

        self.user.is_composer_admin = True
        self.user.save(update_fields=["is_composer_admin"])

        for url_name, model in (
            ("composer:composer_import", ContentGuideSubsection),
            ("compare:compare_import", CompareSubsection),
        ):
            with self.subTest(consumer=url_name):
                response = self.client.post(
                    reverse(url_name), {"nofo-import": self.upload()}
                )
                self.assertEqual(response.status_code, 302)
                self.assertTrue(model.objects.filter(name="Metadata").exists())
                bodies = " ".join(model.objects.values_list("body", flat=True))
                self.assertIn("Metadata author: Example Office", bodies)
                self.assertIn("Appendix example, not metadata", bodies)

    def test_published_status_and_other_group_cannot_reimport(self):
        nofo = Nofo.objects.create(
            title="Saved",
            number="TEST-1096",
            opdiv="HHS",
            group="bloom",
            status="published",
        )
        section = Section.objects.create(nofo=nofo, name="Original", order=1)
        Subsection.objects.create(section=section, name="", body="Old body", order=1)
        url = reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk})
        response = self.client.post(url, {"nofo-import": self.upload()})
        self.assertEqual(response.status_code, 400)
        nofo.status = "draft"
        nofo.save()
        other = BloomUser.objects.create_user(
            email="other-group@example.com",
            password="synthetic-test",
            group="cdc",
            force_password_reset=False,
        )
        self.client.force_login(other)
        response = self.client.post(url, {"nofo-import": self.upload()})
        self.assertEqual(response.status_code, 403)
        nofo.refresh_from_db()
        self.assertEqual(
            (nofo.title, nofo.opdiv, nofo.sections.get().subsections.get().body),
            ("Saved", "HHS", "Old body"),
        )

    def test_viewing_existing_record_does_not_extract_metadata(self):
        nofo = Nofo.objects.create(
            title="Saved title",
            number="TEST-1096",
            opdiv="HHS",
            group="bloom",
            status="draft",
        )
        section = Section.objects.create(nofo=nofo, name="Metadata", order=1)
        Subsection.objects.create(
            section=section, name="", body="Agency: Not saved", order=1
        )
        self.client.get(reverse("nofos:nofo_edit", kwargs={"pk": nofo.pk}))
        nofo.refresh_from_db()
        self.assertEqual(nofo.agency, "")
