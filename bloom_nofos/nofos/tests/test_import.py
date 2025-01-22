import os

from constance.test import override_config
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
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
