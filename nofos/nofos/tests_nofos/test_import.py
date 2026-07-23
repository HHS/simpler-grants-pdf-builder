import os

import markdown
from bs4 import BeautifulSoup
from constance.test import override_config
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.nofo import parse_uploaded_file_as_html_string, replace_chars
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
            self.assertIsNotNone(paragraph.find("img", alt="Checkbox"))

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


class TestNofoImportBlankOpdivError(TestCase):
    """
    Importing a NOFO whose Word doc has a blank "Opdiv:" field should show a
    dedicated, actionable error page instead of a raw Django validation dict.
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

    def _build_docx_file_blank_opdiv(self):
        # Real .docx fixture (converted via Mammoth) where the "OpDiv:" label
        # is present on the page but has no value after it, matching the
        # originally reported bug (as opposed to the label being absent
        # entirely, which is what the synthetic HTML fixture above tests).
        with open(self.docx_blank_opdiv_fixture_path, "rb") as f:
            docx_data = f.read()

        return SimpleUploadedFile(
            "lists--blank-opdiv.docx",
            docx_data,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    def _assert_actionable_opdiv_error_page(self, content):
        # New heading and body copy
        self.assertIn("We couldn’t import this NOFO", content)
        self.assertIn(
            "is blank. NOFO Builder needs this field filled in before it can import the document.",
            content,
        )

        # Steps to fix
        self.assertIn("Open the Word document.", content)
        self.assertIn("Add a value after ‘Opdiv:’", content)
        self.assertIn("Save the document.", content)
        # Step 4 links "Import it again." back to the homepage
        self.assertIn(f'<a href="{reverse("index")}">Import it again.</a>', content)

        # Escalation paragraph — feedback form link opens in a new tab
        self.assertIn("Still need help?", content)
        self.assertIn("NOFO Builder Feedback Form", content)
        self.assertIn("https://forms.office.com/pages/responsepage.aspx", content)
        self.assertIn('target="_blank"', content)
        self.assertIn('rel="noopener noreferrer"', content)

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
        from the original bug report.
        """
        response = self.client.post(
            reverse("nofos:nofo_import"),
            {
                "nofo-import": self._build_docx_file_blank_opdiv(),
                "csrfmiddlewaretoken": "dummy",
            },
        )

        self.assertEqual(response.status_code, 400)
        self._assert_actionable_opdiv_error_page(response.content.decode("utf-8"))
