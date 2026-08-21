import os
from unittest.mock import patch

import markdown
from bs4 import BeautifulSoup
from constance.test import override_config
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, Section, Subsection
from nofos.nofo import (
    get_sections_from_soup,
    get_subsections_from_sections,
    merge_funding_details_label_value_paragraphs,
    parse_uploaded_file_as_html_string,
    process_nofo_html,
    replace_chars,
    replace_links,
    resolve_section_heading_level,
)
from nofos.nofo_markdown import md
from nofos.templatetags.replace_unicode_with_icon import replace_unicode_with_icon


class TestParseNofoFile(TestCase):
    def setUp(self):
        # Build absolute file paths to your fixtures
        self.html_fixture_path = os.path.join(
            settings.BASE_DIR, "nofos", "fixtures", "html", "nofo.html"
        )
        self.docx_fixture_path = os.path.join(
            settings.BASE_DIR, "nofos", "fixtures", "docx", "lists.docx"
        )

        self.docx_warning_fixture_path = os.path.join(
            settings.BASE_DIR,
            "nofos",
            "fixtures",
            "docx",
            "lists--mammoth-warning.docx",
        )

        self.application_checklist_indent_fixture_path = os.path.join(
            settings.BASE_DIR,
            "nofos",
            "fixtures",
            "docx",
            "application-checklist-indent.docx",
        )

    def test_no_file_raises_validation_error(self):
        """
        parse_nofo_file(None) should raise ValidationError because there's no file.
        """
        with self.assertRaises(ValidationError) as context:
            parse_uploaded_file_as_html_string(None)
        self.assertIn("Oops! No fos uploaded", str(context.exception))

    def test_invalid_content_type_raises_validation_error(self):
        """
        parse_nofo_file with an unsupported content type (e.g. 'image/png')
        should raise ValidationError.
        """
        fake_file = SimpleUploadedFile(
            "image.png", b"fake image content", content_type="image/png"
        )
        with self.assertRaises(ValidationError) as context:
            parse_uploaded_file_as_html_string(fake_file)
        self.assertIn("Please import a .docx or HTML file", str(context.exception))

    def test_html_file_returns_string(self):
        """
        parse_nofo_file with a valid HTML file should return a decoded string.
        """
        with open(self.html_fixture_path, "rb") as f:
            html_data = f.read()

        html_file = SimpleUploadedFile("nofo.html", html_data, content_type="text/html")

        result = parse_uploaded_file_as_html_string(html_file)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
        self.assertIn("<title>My Awesome NOFO</title>", result)

    def test_docx_file_returns_string(self):
        """
        parse_nofo_file with a valid .docx fixture should return an HTML string.
        """
        with open(self.docx_fixture_path, "rb") as f:
            docx_data = f.read()

        docx_file = SimpleUploadedFile(
            "lists.docx",
            docx_data,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        result = parse_uploaded_file_as_html_string(docx_file)
        self.assertIsInstance(result, str)
        self.assertIn("<h2>Step 1: Review the Opportunity</h2>", result)

    def test_indented_application_checklist_rows_survive_render_pipeline(self):
        with open(self.application_checklist_indent_fixture_path, "rb") as f:
            docx_data = f.read()

        docx_file = SimpleUploadedFile(
            "application-checklist-indent.docx",
            docx_data,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        with override_config(WORD_IMPORT_STRICT_MODE=True):
            imported_html = replace_chars(parse_uploaded_file_as_html_string(docx_file))
        imported_soup = BeautifulSoup(imported_html, "html.parser")
        imported_children = imported_soup.select("td p.application-list--left-indent")

        self.assertEqual(
            [paragraph.get_text(strip=True) for paragraph in imported_children],
            ["◻ Report on overlap", "◻ Indirect cost agreement"],
        )

        markdown_body = md(imported_html)
        rendered_html = markdown.markdown(markdown_body, extensions=["extra"])
        rendered_with_icons = replace_unicode_with_icon(rendered_html)
        rendered_soup = BeautifulSoup(rendered_with_icons, "html.parser")
        rendered_children = rendered_soup.select("td p.application-list--left-indent")

        self.assertEqual(len(rendered_children), 2)
        for paragraph in rendered_children:
            self.assertIn("usa-icon__line", paragraph.get("class", []))
            self.assertIsNotNone(
                paragraph.find("img", class_="usa-icon--check_box_outline_blank")
            )

    def test_docx_file_with_strict_mode_and_no_warnings(self):
        """
        If WORD_IMPORT_STRICT_MODE is True but there are no warnings,
        parsing should succeed without a ValidationError.
        """
        with open(self.docx_fixture_path, "rb") as f:
            docx_data = f.read()

        docx_file = SimpleUploadedFile(
            "lists.docx",
            docx_data,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        # Set WORD_IMPORT_STRICT_MODE to True
        with override_config(WORD_IMPORT_STRICT_MODE=True):
            result = parse_uploaded_file_as_html_string(docx_file)

        self.assertIsInstance(result, str)

    def test_docx_file_with_strict_mode_and_warnings(self):
        """
        If WORD_IMPORT_STRICT_MODE is True and there ARE warnings,
        parse_nofo_file should raise ValidationError.
        """
        with open(self.docx_warning_fixture_path, "rb") as f:
            docx_data = f.read()

        docx_file = SimpleUploadedFile(
            "lists--mammoth-warning.docx",
            docx_data,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        # Set WORD_IMPORT_STRICT_MODE to True
        with override_config(WORD_IMPORT_STRICT_MODE=True):
            with self.assertRaises(ValidationError) as context:
                parse_uploaded_file_as_html_string(docx_file)

            self.assertIn(
                "[\"<p>Mammoth warnings found. These styles are not recognized by our style map:</p><ul><li>Unrecognised paragraph style: Paul's undocumented style (Style ID: Paulsundocumentedstyle)</li><li>Unrecognised paragraph style: Paul's undocumented style 2 (Style ID: Paulsundocumentedstyle2)</li></ul>\"]",
                str(context.exception),
            )

    @patch("nofos.nofo.mammoth.convert_to_html")
    def test_docx_conversion_error_is_sanitized(self, convert_to_html):
        convert_to_html.side_effect = RuntimeError("private converter detail")
        docx_file = SimpleUploadedFile(
            "broken.docx",
            b"not important",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        with self.assertRaises(ValidationError) as context:
            parse_uploaded_file_as_html_string(docx_file)

        self.assertEqual(context.exception.error_list[0].code, "docx_conversion")
        self.assertIn("could not read this Word document", str(context.exception))
        self.assertNotIn("private converter detail", str(context.exception))


class TestFundingDetailsParagraphNormalization(TestCase):
    def test_merges_split_funding_detail_fields(self):
        soup = BeautifulSoup(
            """
            <h3>Funding details</h3>
            <p><strong>Application Types:</strong></p><p>New</p>
            <p>Expected total available funding in FY 2026:</p><p>$3,240,000</p>
            <p>Expected number and type of awards:</p>
            <p>1 CA (Cooperative Agreement)</p>
            <p>Funding range per award:</p><p>$0 - $3,240,000</p>
            <h3>Program description</h3>
            <p>Example label:</p><p>Keep this separate</p>
            """,
            "html.parser",
        )

        merge_funding_details_label_value_paragraphs(soup)

        self.assertEqual(
            [paragraph.get_text(" ", strip=True) for paragraph in soup.find_all("p")],
            [
                "Application Types: New",
                "Expected total available funding in FY 2026: $3,240,000",
                "Expected number and type of awards: 1 CA (Cooperative Agreement)",
                "Funding range per award: $0 - $3,240,000",
                "Example label:",
                "Keep this separate",
            ],
        )
        self.assertEqual(soup.find("strong").get_text(strip=True), "Application Types:")

    def test_supports_h4_heading_and_stops_at_next_higher_heading(self):
        soup = BeautifulSoup(
            """
            <h4> Funding Details </h4>
            <p>Funding range per award: </p><p> $10 - $20 </p>
            <h3>Next subsection</h3>
            <p>Outside label:</p><p>Outside value</p>
            """,
            "html.parser",
        )

        merge_funding_details_label_value_paragraphs(soup)

        paragraphs = [paragraph.get_text() for paragraph in soup.find_all("p")]
        self.assertEqual(
            paragraphs,
            ["Funding range per award: $10 - $20 ", "Outside label:", "Outside value"],
        )

    def test_leaves_inline_and_empty_values_unchanged(self):
        soup = BeautifulSoup(
            """
            <h3>Funding details</h3>
            <p>Application Types: New</p>
            <p>Funding range per award:</p><p> </p>
            <p>First unresolved label:</p><p>Second unresolved label:</p>
            """,
            "html.parser",
        )

        merge_funding_details_label_value_paragraphs(soup)

        self.assertEqual(len(soup.find_all("p")), 5)
        self.assertEqual(soup.find_all("p")[0].get_text(), "Application Types: New")

    def test_normalizes_real_docx_fixture_in_import_pipeline(self):
        fixture_path = os.path.join(
            settings.BASE_DIR,
            "nofos",
            "fixtures",
            "docx",
            "funding-details--split-label-values.docx",
        )
        with open(fixture_path, "rb") as fixture:
            uploaded_file = SimpleUploadedFile(
                "funding-details--split-label-values.docx",
                fixture.read(),
                content_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
            )

        imported_html = parse_uploaded_file_as_html_string(uploaded_file)
        soup = BeautifulSoup(imported_html, "html.parser")
        top_heading_level = resolve_section_heading_level(soup)
        soup, _ = process_nofo_html(soup, top_heading_level)

        funding_heading = soup.find(
            lambda tag: tag.name in {"h3", "h4"}
            and tag.get_text(strip=True) == "Funding details"
        )
        paragraphs = []
        current = funding_heading.find_next_sibling()
        while current is not None and current.name not in {"h1", "h2", "h3", "h4"}:
            if current.name == "p":
                paragraphs.append(current.get_text(" ", strip=True))
            current = current.find_next_sibling()

        self.assertEqual(
            paragraphs,
            [
                "Application Types: New",
                "Expected total available funding in FY 2026: $3,240,000",
                "Expected number and type of awards: 1 CA (Cooperative Agreement)",
                "Funding range per award: $0 - $3,240,000",
            ],
        )


class TestKeyCalloutDocxImport(TestCase):
    def parse_fixture(self, fixture_name):
        fixture_path = os.path.join(
            settings.BASE_DIR, "nofos", "fixtures", "docx", fixture_name
        )
        with open(fixture_path, "rb") as fixture:
            uploaded_file = SimpleUploadedFile(
                fixture_name,
                fixture.read(),
                content_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
            )

        file_content = parse_uploaded_file_as_html_string(uploaded_file)
        cleaned_content = replace_links(replace_chars(file_content))
        soup = BeautifulSoup(cleaned_content, "html.parser")
        top_heading_level = resolve_section_heading_level(soup)
        soup, _ = process_nofo_html(soup, top_heading_level)
        sections = get_sections_from_soup(soup, top_heading_level)
        sections = get_subsections_from_sections(sections, top_heading_level)
        return [
            subsection for section in sections for subsection in section["subsections"]
        ]

    def assert_key_callout_heading(self, subsection, name, is_callout_box=False):
        self.assertEqual(subsection["name"], name)
        self.assertEqual(subsection["tag"], "h4")
        self.assertEqual(subsection["is_callout_box"], is_callout_box)

    def test_h1_h3_outside_key_facts_is_normalized(self):
        subsections = self.parse_fixture("key-callout--h1-h3-outside.docx")
        key_facts = next(
            subsection
            for subsection in subsections
            if subsection["name"] == "Key facts"
        )

        self.assert_key_callout_heading(key_facts, "Key facts")
        key_facts_index = subsections.index(key_facts)
        self.assertTrue(subsections[key_facts_index + 1]["is_callout_box"])
        self.assertIn(
            "Application deadline",
            str(subsections[key_facts_index + 1]["body"]),
        )

    def test_h1_bold_paragraph_key_facts_is_promoted(self):
        subsections = self.parse_fixture("key-callout--h1-bold-outside.docx")
        key_facts = next(
            subsection
            for subsection in subsections
            if subsection["name"] == "Key facts"
        )

        self.assert_key_callout_heading(key_facts, "Key facts")
        self.assertTrue(subsections[subsections.index(key_facts) + 1]["is_callout_box"])

    def test_h1_plain_paragraph_key_facts_is_promoted(self):
        subsections = self.parse_fixture("key-callout--h1-plain-outside.docx")
        key_facts = next(
            subsection
            for subsection in subsections
            if subsection["name"] == "Key facts"
        )

        self.assert_key_callout_heading(key_facts, "Key facts")
        self.assertTrue(subsections[subsections.index(key_facts) + 1]["is_callout_box"])

    def test_h1_h4_inside_key_dates_is_normalized(self):
        subsections = self.parse_fixture("key-callout--h1-h4-inside.docx")
        key_dates = next(
            subsection
            for subsection in subsections
            if subsection["name"] == "Key dates"
        )

        self.assert_key_callout_heading(key_dates, "Key dates", is_callout_box=True)
        self.assertIn("Application deadline", str(key_dates["body"]))

    def test_h2_h4_inside_key_dates_remains_correct(self):
        subsections = self.parse_fixture("key-callout--h2-h4-inside.docx")
        key_dates = next(
            subsection
            for subsection in subsections
            if subsection["name"] == "Key dates"
        )

        self.assert_key_callout_heading(key_dates, "Key dates", is_callout_box=True)


class TestNofoImportOpdiv(TestCase):
    """
    Import OpDiv metadata from supported Word layouts and show an actionable
    error when the value is genuinely missing.
    """

    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="test@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client = Client()
        self.client.login(email="test@example.com", password="testpass123")

        self.docx_blank_opdiv_fixture_path = os.path.join(
            settings.BASE_DIR,
            "nofos",
            "fixtures",
            "docx",
            "lists--blank-opdiv.docx",
        )
        self.docx_opdiv_soft_break_fixture_path = os.path.join(
            settings.BASE_DIR,
            "nofos",
            "fixtures",
            "docx",
            "opdiv--soft-line-break.docx",
        )
        self.docx_opdiv_paragraph_break_fixture_path = os.path.join(
            settings.BASE_DIR,
            "nofos",
            "fixtures",
            "docx",
            "opdiv--paragraph-break.docx",
        )

    def _build_html_file_missing_opdiv(self):
        html_content = """
        <html>
        <head><title>Test NOFO</title></head>
        <body>
            <p>Opportunity name: Test NOFO</p>
            <p>Opportunity number: NOFO-ACF-001</p>
            <h1>Test Section 1</h1>
            <h2 data-order="10">Eligibility Information</h2>
            <p>Some eligibility content</p>
        </body>
        </html>
        """
        return SimpleUploadedFile(
            "test.html", html_content.encode("utf-8"), content_type="text/html"
        )

    def _build_html_file_with_ambiguous_opdiv(self):
        html_content = """
        <html>
        <head><title>Test NOFO</title></head>
        <body>
            <p>Opportunity name: Test NOFO</p>
            <p>Opportunity number: NOFO-ACF-001</p>
            <p>Opdiv:</p>
            <p>Administration for Children and Families</p>
            <h1>Test Section 1</h1>
            <h2 data-order="10">Eligibility Information</h2>
            <p>Some eligibility content</p>
        </body>
        </html>
        """
        return SimpleUploadedFile(
            "ambiguous-opdiv.html",
            html_content.encode("utf-8"),
            content_type="text/html",
        )

    def _build_docx_file(self, fixture_path):
        with open(fixture_path, "rb") as f:
            docx_data = f.read()

        return SimpleUploadedFile(
            os.path.basename(fixture_path),
            docx_data,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    def _assert_actionable_opdiv_error_page(self, content):
        # New heading and body copy
        self.assertIn("We couldn’t import this NOFO", content)
        self.assertIn(
            "couldn’t reliably read a value from the",
            content,
        )
        self.assertIn("may be missing or separated from the label", content)

        # Steps to fix
        self.assertIn("Open the Word document.", content)
        self.assertIn(
            "Put the agency’s operating division on the same line as", content
        )
        self.assertNotIn("field on page 1 of the Word document is blank", content)
        self.assertIn("Save the document, then select it again.", content)
        # The retry action returns directly to the import form.
        self.assertIn(f'href="{reverse("nofos:nofo_import")}"', content)
        self.assertIn("Try the import again", content)

        # Escalation paragraph uses the shared support channels.
        self.assertIn("Need help resolving this error?", content)
        self.assertIn("NOFO Builder Feedback Form", content)
        self.assertIn("https://forms.office.com/pages/responsepage.aspx", content)
        self.assertIn("simplerNOFOs@agile6.com", content)
        self.assertIn('target="_blank"', content)
        self.assertIn('rel="noopener noreferrer"', content)
        self.assertIn("IMPORT-OPDIV-BLANK", content)

        # No "Maybe go back to:" links/text (that's the generic 400 page's copy)
        self.assertNotIn("Maybe go back to:", content)

        # The raw validation error dict must not leak through
        self.assertNotIn("This field cannot be blank", content)
        self.assertNotIn("'opdiv':", content)

    def test_import_with_blank_opdiv_shows_actionable_error_page(self):
        """
        HTML upload where the "Opdiv:" label is missing entirely.
        """
        response = self.client.post(
            reverse("nofos:nofo_import"),
            {
                "nofo-import": self._build_html_file_missing_opdiv(),
                "csrfmiddlewaretoken": "dummy",
            },
        )

        self.assertEqual(response.status_code, 400)
        self._assert_actionable_opdiv_error_page(response.content.decode("utf-8"))

    def test_import_docx_with_blank_opdiv_field_shows_actionable_error_page(self):
        """
        Real .docx upload (via Mammoth conversion) where the "OpDiv:" label is
        present on the page but has no value after it — the real-world scenario
        from the originally reported bug.
        """
        response = self.client.post(
            reverse("nofos:nofo_import"),
            {
                "nofo-import": self._build_docx_file(
                    self.docx_blank_opdiv_fixture_path
                ),
                "csrfmiddlewaretoken": "dummy",
            },
        )

        self.assertEqual(response.status_code, 400)
        self._assert_actionable_opdiv_error_page(response.content.decode("utf-8"))

    def test_import_with_ambiguous_opdiv_shows_actionable_error_page(self):
        response = self.client.post(
            reverse("nofos:nofo_import"),
            {
                "nofo-import": self._build_html_file_with_ambiguous_opdiv(),
                "csrfmiddlewaretoken": "dummy",
            },
        )

        self.assertEqual(response.status_code, 400)
        self._assert_actionable_opdiv_error_page(response.content.decode("utf-8"))

    def test_import_docx_with_opdiv_after_soft_line_break_succeeds(self):
        response = self.client.post(
            reverse("nofos:nofo_import"),
            {
                "nofo-import": self._build_docx_file(
                    self.docx_opdiv_soft_break_fixture_path
                ),
                "csrfmiddlewaretoken": "dummy",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Nofo.objects.latest("created").opdiv,
            "Administration for Children and Families",
        )

    def test_import_docx_with_opdiv_in_following_paragraph_succeeds(self):
        response = self.client.post(
            reverse("nofos:nofo_import"),
            {
                "nofo-import": self._build_docx_file(
                    self.docx_opdiv_paragraph_break_fixture_path
                ),
                "csrfmiddlewaretoken": "dummy",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Nofo.objects.latest("created").opdiv,
            "Administration for Children and Families",
        )


class TestNofoImportMissingAltText(TestCase):
    """
    End-to-end: an imported <img> with no alt attribute should end up in the
    saved subsection body as raw HTML with alt="" (greppable/visible), not as
    markdown's ![]() syntax, which can't distinguish "alt was never set" from
    "alt is intentionally empty". See #814.
    """

    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="alt-text@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client = Client()
        self.client.login(email="alt-text@example.com", password="testpass123")

    def _build_html_file(self):
        html_content = """
        <html>
        <body>
            <p>Opportunity name: Alt Text Test NOFO</p>
            <p>Opportunity number: NOFO-ALT-001</p>
            <p>Opdiv: CDC</p>
            <h1>Test Section 1</h1>
            <h2 data-order="10">Eligibility Information</h2>
            <p>Some eligibility content, followed by a diagram:</p>
            <p><img src="diagram.png"></p>
            <p>End of subsection.</p>
        </body>
        </html>
        """
        return SimpleUploadedFile(
            "test.html", html_content.encode("utf-8"), content_type="text/html"
        )

    def test_missing_alt_img_saved_as_raw_html_not_markdown_syntax(self):
        response = self.client.post(
            reverse("nofos:nofo_import"),
            {"nofo-import": self._build_html_file(), "csrfmiddlewaretoken": "dummy"},
        )

        self.assertEqual(response.status_code, 302)

        subsection = Subsection.objects.get(
            section__nofo=Nofo.objects.latest("created"),
            name="Eligibility Information",
        )

        self.assertIn('<img alt="" src="diagram.png"/>', subsection.body)
        self.assertNotIn("![](diagram.png)", subsection.body)
        self.assertNotIn("data-nofo-missing-alt-text", subsection.body)


class TestBlockingImportErrorPages(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="errors@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client.login(email="errors@example.com", password="testpass123")
        self.import_url = reverse("nofos:nofo_import")
        self.docx_warning_fixture_path = os.path.join(
            settings.BASE_DIR,
            "nofos",
            "fixtures",
            "docx",
            "lists--mammoth-warning.docx",
        )
        self.docx_mistagged_heading_fixture_path = os.path.join(
            settings.BASE_DIR,
            "nofos",
            "fixtures",
            "docx",
            "mistagged-paragraph-heading.docx",
        )

    def test_strict_mode_warning_is_actionable_and_hides_converter_details(self):
        with open(self.docx_warning_fixture_path, "rb") as f:
            docx_file = SimpleUploadedFile(
                "lists--mammoth-warning.docx",
                f.read(),
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        with override_config(WORD_IMPORT_STRICT_MODE=True):
            response = self.client.post(self.import_url, {"nofo-import": docx_file})

        content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 422)
        self.assertIn("We couldn’t import this document", content)
        self.assertIn("IMPORT-STRICT-FORMATTING", content)
        self.assertIn(f'href="{self.import_url}"', content)
        self.assertIn("simplerNOFOs@agile6.com", content)
        self.assertNotIn("Mammoth", content)
        self.assertNotIn("Style ID", content)
        self.assertNotIn("Paulsundocumentedstyle", content)

    def test_long_section_heading_identifies_mistagged_text(self):
        affected_text = "A" * 251
        uploaded_file = SimpleUploadedFile(
            "long-section.html",
            (
                "<p>Opportunity name: Test NOFO</p>"
                "<p>Opdiv: CDC</p>"
                f"<h1>{affected_text}</h1>"
                "<h2>Valid subsection</h2><p>Body</p>"
            ).encode("utf-8"),
            content_type="text/html",
        )

        response = self.client.post(self.import_url, {"nofo-import": uploaded_file})

        content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 422)
        self.assertIn("IMPORT-HEADING-TOO-LONG", content)
        self.assertIn("Section heading 1", content)
        self.assertIn("Heading character limit", content)
        self.assertIn("251", content)
        self.assertIn(affected_text, content)
        self.assertNotIn("IMPORT-CREATE-INVALID", content)

    def test_long_subsection_heading_is_safely_escaped(self):
        affected_text = ("B" * 401) + "<script>alert('unsafe')</script>"
        uploaded_file = SimpleUploadedFile(
            "long-subsection.html",
            (
                "<p>Opportunity name: Test NOFO</p>"
                "<p>Opdiv: CDC</p>"
                "<h1>Valid section</h1>"
                f"<h2>{affected_text.replace('<', '&lt;').replace('>', '&gt;')}</h2>"
                "<p>Body</p>"
            ).encode("utf-8"),
            content_type="text/html",
        )

        response = self.client.post(self.import_url, {"nofo-import": uploaded_file})

        content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 422)
        self.assertIn("IMPORT-HEADING-TOO-LONG", content)
        self.assertIn("Subsection heading 1", content)
        self.assertIn("400", content)
        self.assertIn("&lt;script&gt;", content)
        self.assertNotIn("<script>", content)
        self.assertNotIn("IMPORT-CREATE-INVALID", content)

    def test_word_import_identifies_mistagged_paragraph_heading(self):
        with open(self.docx_mistagged_heading_fixture_path, "rb") as fixture:
            uploaded_file = SimpleUploadedFile(
                "mistagged-paragraph-heading.docx",
                fixture.read(),
                content_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
            )

        response = self.client.post(self.import_url, {"nofo-import": uploaded_file})

        content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 422)
        self.assertIn("IMPORT-HEADING-TOO-LONG", content)
        self.assertIn("Subsection heading 1", content)
        self.assertIn("448", content)
        self.assertIn(
            "This entire paragraph was accidentally assigned a heading style in Word.",
            content,
        )
        self.assertNotIn("IMPORT-CREATE-INVALID", content)
        self.assertEqual(Nofo.objects.count(), 0)

    def test_reimport_long_heading_preserves_current_nofo(self):
        affected_text = (
            "This entire paragraph was accidentally assigned a heading style in Word."
        )
        nofo = Nofo.objects.create(
            title="Existing NOFO",
            number="TEST-776",
            opdiv="CDC",
            group="bloom",
        )
        section = Section.objects.create(
            nofo=nofo,
            name="Existing section",
            html_id="existing-section",
            order=1,
        )
        subsection = Subsection.objects.create(
            section=section,
            name="Existing subsection",
            html_id="existing-subsection",
            order=1,
            tag="h3",
            body="Existing content must survive a rejected re-import.",
        )
        reimport_url = reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.id})
        with open(self.docx_mistagged_heading_fixture_path, "rb") as fixture:
            uploaded_file = SimpleUploadedFile(
                "mistagged-paragraph-heading.docx",
                fixture.read(),
                content_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
            )

        response = self.client.post(reimport_url, {"nofo-import": uploaded_file})

        content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 422)
        self.assertIn("IMPORT-HEADING-TOO-LONG", content)
        self.assertIn(affected_text, content)
        self.assertIn(f'href="{reimport_url}"', content)
        self.assertNotIn("REIMPORT-DOCUMENT-INVALID", content)

        nofo.refresh_from_db()
        self.assertEqual(Nofo.objects.count(), 1)
        self.assertEqual(nofo.sections.count(), 1)
        preserved_section = nofo.sections.get()
        self.assertEqual(preserved_section.id, section.id)
        self.assertEqual(preserved_section.name, "Existing section")
        self.assertEqual(preserved_section.subsections.count(), 1)
        preserved_subsection = preserved_section.subsections.get()
        self.assertEqual(preserved_subsection.id, subsection.id)
        self.assertEqual(
            preserved_subsection.body,
            "Existing content must survive a rejected re-import.",
        )

    @patch("nofos.views.log_exception")
    @patch("nofos.nofo.mammoth.convert_to_html")
    def test_docx_conversion_failure_uses_logged_safe_page(
        self, convert_to_html, log_error
    ):
        convert_to_html.side_effect = RuntimeError("private converter detail")
        docx_file = SimpleUploadedFile(
            "broken.docx",
            b"not important",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        response = self.client.post(self.import_url, {"nofo-import": docx_file})

        content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 422)
        self.assertIn("IMPORT-DOCX-CONVERSION", content)
        self.assertIn(f'href="{self.import_url}"', content)
        self.assertNotIn("private converter detail", content)
        log_error.assert_called_once()
        self.assertEqual(
            log_error.call_args.kwargs["context"],
            "BaseNofoImportView:ValidationError:IMPORT-DOCX-CONVERSION",
        )

    @patch("nofos.views.log_exception")
    def test_strict_formatting_code_is_logged(self, log_error):
        with open(self.docx_warning_fixture_path, "rb") as f:
            docx_file = SimpleUploadedFile(
                "lists--mammoth-warning.docx",
                f.read(),
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        with override_config(WORD_IMPORT_STRICT_MODE=True):
            response = self.client.post(self.import_url, {"nofo-import": docx_file})

        self.assertEqual(response.status_code, 422)
        log_error.assert_called_once()
        self.assertEqual(
            log_error.call_args.kwargs["context"],
            "BaseNofoImportView:ValidationError:IMPORT-STRICT-FORMATTING",
        )

    @patch("nofos.views.parse_uploaded_file_as_html_string")
    def test_unexpected_import_error_returns_sanitized_500(self, parse_file):
        parse_file.side_effect = RuntimeError("private implementation detail")
        uploaded_file = SimpleUploadedFile(
            "test.html", b"<h1>Test</h1>", content_type="text/html"
        )

        response = self.client.post(self.import_url, {"nofo-import": uploaded_file})

        content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 500)
        self.assertIn("We couldn’t finish importing this document", content)
        self.assertIn("IMPORT-UNEXPECTED", content)
        self.assertIn(f'href="{self.import_url}"', content)
        self.assertIn("simplerNOFOs@agile6.com", content)
        self.assertNotIn("private implementation detail", content)

    @patch("nofos.views.parse_uploaded_file_as_html_string")
    def test_blocked_reimport_uses_shared_page_and_returns_to_nofo(self, parse_file):
        parse_file.return_value = (
            "<p>Opportunity number: TEST-001</p>"
            "<h1>Section</h1><h2>Subsection</h2><p>Body</p>"
        )
        nofo = Nofo.objects.create(
            title="Published NOFO",
            number="TEST-001",
            opdiv="CDC",
            group="bloom",
            status="published",
        )
        reimport_url = reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.id})
        uploaded_file = SimpleUploadedFile(
            "test.html", b"placeholder", content_type="text/html"
        )

        response = self.client.post(reimport_url, {"nofo-import": uploaded_file})

        content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 400)
        self.assertIn("REIMPORT-STATUS-BLOCKED", content)
        self.assertIn(
            f'href="{reverse("nofos:nofo_edit", kwargs={"pk": nofo.id})}"',
            content,
        )


class TestNofoImportMixedHeadingHierarchy(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="heading-test@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client = Client()
        self.client.login(email="heading-test@example.com", password="testpass123")
        self.import_url = reverse("nofos:nofo_import")

    def test_before_you_begin_h2_is_removed_before_heading_level_is_resolved(self):
        html_content = """
        <h2>Before You Begin</h2>
        <p>Duplicate instructions generated by the source system.</p>
        <p>OpDiv: Administration for Children and Families</p>
        <p>Opportunity name: Before You Begin fixture</p>
        <p>Opportunity number: ACF-TEST-BYB</p>
        <h1>Step 1: Review the Opportunity</h1>
        <p>Important content that must remain.</p>
        """
        uploaded_file = SimpleUploadedFile(
            "before-you-begin.html",
            html_content.encode("utf-8"),
            content_type="text/html",
        )

        response = self.client.post(
            self.import_url,
            {"nofo-import": uploaded_file},
        )

        self.assertEqual(response.status_code, 302)
        nofo = Nofo.objects.get()
        self.assertEqual(nofo.opdiv, "Administration for Children and Families")
        self.assertEqual(
            list(nofo.sections.values_list("name", flat=True)),
            ["Step 1: Review the Opportunity"],
        )

    @patch("nofos.views.log_exception")
    def test_import_blocks_h2_sections_before_late_h1_appendix_on_shared_page(
        self, log_error
    ):
        html_content = """
        <p>OpDiv: Centers for Medicare &amp; Medicaid Services (CMS)</p>
        <p>Opportunity name: Mixed heading fixture</p>
        <p>Opportunity number: CMS-TEST-745</p>
        <h2>Step 1: Review the Opportunity</h2>
        <p>Important content that must not be silently dropped.</p>
        <h2>Step 2: Get Ready to Apply</h2>
        <h1>Appendix A: Award data</h1>
        <p>Appendix content.</p>
        """
        uploaded_file = SimpleUploadedFile(
            "mixed-headings.html",
            html_content.encode("utf-8"),
            content_type="text/html",
        )

        response = self.client.post(
            self.import_url,
            {"nofo-import": uploaded_file},
        )

        content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 422)
        self.assertIn("We couldn’t safely determine the document structure", content)
        self.assertIn("IMPORT-AMBIGUOUS-HEADINGS", content)
        self.assertIn("Heading 2 before its first Heading 1", content)
        self.assertIn("Step 1: Review the Opportunity", content)
        self.assertIn("Appendix A: Award data", content)
        self.assertIn("Apply one consistent heading level", content)
        self.assertIn(f'href="{self.import_url}"', content)
        self.assertIn("simplerNOFOs@agile6.com", content)
        self.assertEqual(Nofo.objects.count(), 0)
        log_error.assert_called_once()
        self.assertEqual(log_error.call_args.kwargs["level"], "warning")
        self.assertEqual(
            log_error.call_args.kwargs["context"],
            "BaseNofoImportView:ValidationError:IMPORT-AMBIGUOUS-HEADINGS",
        )
        self.assertEqual(log_error.call_args.kwargs["status"], 422)

    def test_table_h1_does_not_hide_h2_sections(self):
        html_content = """
        <p>OpDiv: Centers for Medicare &amp; Medicaid Services (CMS)</p>
        <p>Opportunity name: Table heading fixture</p>
        <p>Opportunity number: CMS-TEST-TABLE-H1</p>
        <h2>Step 1: Review the Opportunity</h2>
        <p>First section content.</p>
        <table>
          <tr><td><h1>Table label</h1></td></tr>
        </table>
        <h2>Step 2: Get Ready to Apply</h2>
        <p>Second section content.</p>
        """
        uploaded_file = SimpleUploadedFile(
            "table-heading.html",
            html_content.encode("utf-8"),
            content_type="text/html",
        )

        response = self.client.post(
            self.import_url,
            {"nofo-import": uploaded_file},
        )

        self.assertEqual(response.status_code, 302)
        nofo = Nofo.objects.get()
        self.assertEqual(
            list(nofo.sections.values_list("name", flat=True)),
            [
                "Step 1: Review the Opportunity",
                "Step 2: Get Ready to Apply",
            ],
        )
