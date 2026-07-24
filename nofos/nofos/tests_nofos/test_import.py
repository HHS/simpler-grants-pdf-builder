import os
from unittest.mock import patch

from constance.test import override_config
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo
from nofos.nofo import parse_uploaded_file_as_html_string


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
        self.assertIn("Add the agency’s operating division after ‘Opdiv:’", content)
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
                "nofo-import": self._build_docx_file_blank_opdiv(),
                "csrfmiddlewaretoken": "dummy",
            },
        )

        self.assertEqual(response.status_code, 400)
        self._assert_actionable_opdiv_error_page(response.content.decode("utf-8"))


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

    def test_import_blocks_h2_sections_before_late_h1_appendix_on_shared_page(self):
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
