from django.test import TestCase
from .utils import strip_file_suffix


class StripFileSuffixTests(TestCase):
    def test_standard_extension(self):
        self.assertEqual(
            strip_file_suffix("Document_123_2025.08.01.docx"), "Document_123_2025.08.01"
        )

    def test_multiple_dots(self):
        self.assertEqual(strip_file_suffix("Report.final.v2.pdf"), "Report.final.v2")

    def test_no_extension(self):
        self.assertEqual(strip_file_suffix("no_extension_file"), "no_extension_file")

    def test_hidden_file(self):
        self.assertEqual(strip_file_suffix(".env"), ".env")  # Not a suffix in this case

    def test_trailing_dot(self):
        self.assertEqual(strip_file_suffix("filename."), "filename")

    def test_double_extension(self):
        self.assertEqual(strip_file_suffix("archive.tar.gz"), "archive.tar")

    def test_uppercase_extension(self):
        self.assertEqual(strip_file_suffix("UPPERCASE.DOCX"), "UPPERCASE")
