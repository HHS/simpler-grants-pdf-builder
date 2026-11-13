import re
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from django.test import SimpleTestCase

from nofos.pdf_readability_worker import WORD_PROFILE, analyze_word
from nofos.tests_nofos.test_editable_introduction import fy27_docx
from nofos.tests_nofos.test_word_instruction_boxes import alternate, docx, paragraph


class WordScopeConversionTests(SimpleTestCase):
    def test_position_only_cover_is_distinguished_from_unrecognized_opening(self):
        for following_style, expected in (("Heading1", 2), ("Normal", 0)):
            with self.subTest(style=following_style), TemporaryDirectory() as scratch:
                opening = paragraph("Example cover").replace(
                    "</w:pPr>", "<w:sectPr/></w:pPr>", 1
                )
                body = (
                    opening
                    + paragraph("Step 1: Review the opportunity", following_style)
                    + paragraph("HRSA notice of funding opportunity on Grants.gov.")
                    + paragraph("Opportunity number: HRSA-27-123")
                )
                path = Path(scratch) / "synthetic.docx"
                path.write_bytes(docx(body).read())
                self.assertEqual(
                    analyze_word(path)["word_exclusions"]["cover_position"], expected
                )

    def test_only_verified_instruction_boxes_are_excluded(self):
        body = (
            paragraph("HRSA notice of funding opportunity on Grants.gov.")
            + paragraph("Opportunity number: HRSA-27-123")
            + paragraph("Step 1: Review the opportunity", "Heading1")
            + f"<w:p><w:r>{alternate('Writer guidance box.')}</w:r></w:p>"
            + paragraph("Applicants should file the form.")
        )
        with TemporaryDirectory() as scratch:
            path = Path(scratch) / "synthetic.docx"
            path.write_bytes(docx(body).read())
            report = analyze_word(path)
        self.assertEqual(report["word_exclusions"]["instruction"], 8)
        self.assertNotIn("Writer guidance box", str(report))

    def test_recognized_word_regions_survive_conversion_as_exclusions(self):
        def paragraph(text, style=""):
            prop = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
            return f"<w:p>{prop}<w:r><w:t>{text}</w:t></w:r></w:p>"

        def gallery(name, content):
            return (
                "<w:sdt><w:sdtPr><w:docPartObj>"
                f'<w:docPartGallery w:val="{name}"/>'
                "</w:docPartObj></w:sdtPr><w:sdtContent>"
                f"{content}</w:sdtContent></w:sdt>"
            )

        prefix = (
            gallery("Cover Pages", paragraph("Test cover"))
            + gallery("Table of Contents", paragraph("Eligibility 3"))
            + "<w:tbl><w:tr><w:tc>"
            + paragraph("Instructions for NOFO writers")
            + paragraph("Write a summary.")
            + "</w:tc></w:tr></w:tbl>"
            + paragraph("HRSA funding opportunity from Grants.gov.")
        ).encode()
        with TemporaryDirectory() as scratch:
            path = Path(scratch) / "synthetic.docx"
            with ZipFile(BytesIO(fy27_docx())) as original:
                with ZipFile(path, "w", ZIP_DEFLATED) as target:
                    for name in original.namelist():
                        data = original.read(name)
                        if name == "word/document.xml":
                            data, count = re.subn(
                                rb"<w:body\b[^>]*>",
                                lambda match: match[0] + prefix,
                                data,
                                count=1,
                            )
                            self.assertEqual(count, 1)
                        target.writestr(name, data)
            report = analyze_word(path)
        self.assertEqual(report["profile_id"], WORD_PROFILE)
        self.assertEqual(
            report["word_exclusions"],
            {
                "cover": 2,
                "cover_total": 2,
                "cover_position": 0,
                "table_of_contents": 2,
                "instruction": 7,
                "metadata": 0,
            },
        )
        self.assertNotIn("Write a summary", str(report))
