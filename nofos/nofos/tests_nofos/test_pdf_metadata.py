from django.test import SimpleTestCase

from nofos.pdf_metadata import (
    is_missing_pdf_metadata_value,
    normalize_pdf_metadata_value,
)


class PdfMetadataPolicyTests(SimpleTestCase):
    def test_empty_values_are_normalized_to_empty(self):
        for value in (None, "", "  \n\t"):
            with self.subTest(value=value):
                self.assertEqual(normalize_pdf_metadata_value(value), "")
                self.assertTrue(is_missing_pdf_metadata_value(value))

    def test_whole_field_curly_brace_placeholder_is_normalized_to_empty(self):
        for value in (
            "{Leave blank. Coach will insert.}",
            "  {Leave blank. Coach will insert.}  ",
        ):
            with self.subTest(value=value):
                self.assertEqual(normalize_pdf_metadata_value(value), "")
                self.assertTrue(is_missing_pdf_metadata_value(value))

    def test_real_metadata_is_preserved(self):
        for value in (
            "Administration for Children and Families",
            "Research {Phase 2}",
            "{HHS} grant opportunities",
        ):
            with self.subTest(value=value):
                self.assertEqual(normalize_pdf_metadata_value(value), value)
                self.assertFalse(is_missing_pdf_metadata_value(value))
