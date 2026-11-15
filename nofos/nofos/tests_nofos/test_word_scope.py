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
    def test_complex_toc_field_excludes_entries_but_keeps_plain_lookalike(self):
        field_start = (
            '<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r>'
            "<w:r><w:instrText> TOC </w:instrText></w:r>"
            '<w:r><w:fldChar w:fldCharType="separate"/></w:r></w:p>'
        )
        field_end = '<w:p><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>'
        body = (
            paragraph("HRSA notice of funding opportunity on Grants.gov.")
            + paragraph("Opportunity number: HRSA-27-123")
            + field_start
            + paragraph("Eligibility 3")
            + field_end
            + paragraph("Eligibility 3")
            + paragraph("Applicants should file the form.")
        )
        with TemporaryDirectory() as scratch:
            path = Path(scratch) / "synthetic.docx"
            path.write_bytes(docx(body).read())
            report = analyze_word(path)
        self.assertEqual(report["word_exclusions"]["table_of_contents"], 2)
        self.assertEqual(report["metrics"]["word_count"]["value"], 17)

    def test_section_break_keeps_opening_applicant_prose(self):
        opening = paragraph("Eligible applicants must serve rural communities.").replace(
            "</w:pPr>", "<w:sectPr/></w:pPr>", 1
        )
        body = (
            paragraph("Step 1: Review the opportunity", "Heading1")
            + paragraph("HRSA notice of funding opportunity on Grants.gov.")
            + paragraph("Opportunity number: HRSA-27-123")
        )
        with TemporaryDirectory() as scratch:
            baseline_path = Path(scratch) / "baseline.docx"
            applicant_path = Path(scratch) / "applicant.docx"
            baseline_path.write_bytes(docx(body).read())
            applicant_path.write_bytes(docx(opening + body).read())
            baseline = analyze_word(baseline_path)
            report = analyze_word(applicant_path)
        self.assertEqual(report["word_exclusions"]["cover_total"], 0)
        self.assertEqual(
            report["metrics"]["word_count"]["value"],
            baseline["metrics"]["word_count"]["value"] + 6,
        )

    def test_plain_cover_section_and_before_you_begin_metadata_are_excluded(self):
        # Synthetic GrantSolutions-style layout: plain cover lines, a section
        # break, a contents label and entries, then generated metadata.
        cover = (
            paragraph("Notice of Funding Opportunity")
            + paragraph("Application due 01/01/2099")
            + paragraph("Example Bureau")
            + paragraph("Opportunity Number: HRSA-99-999").replace(
                "</w:pPr>", "<w:sectPr/></w:pPr>", 1
            )
        )
        contents = (
            paragraph("Table of Contents", "MainHeading")
            + paragraph("Before You Begin 2", "TOC2")
            + paragraph("Eligibility 4", "TOC2")
        )
        metadata = paragraph("Metadata author: Example agency") + paragraph(
            "Metadata keywords: Example; Test"
        )

        def body(include_cover, include_metadata):
            return (
                (cover if include_cover else "")
                + contents
                + paragraph("Before You Begin", "Heading2")
                + paragraph("OpDiv: Example")
                + paragraph("Opportunity number: HRSA-99-999")
                + (metadata if include_metadata else "")
                + paragraph("Step 1: Review the opportunity", "Heading1")
                + paragraph("HRSA notice of funding opportunity on Grants.gov.")
                + paragraph("Applicants should file the form.")
            )

        with TemporaryDirectory() as scratch:
            full_path = Path(scratch) / "full.docx"
            bare_path = Path(scratch) / "bare.docx"
            full_path.write_bytes(docx(body(True, True)).read())
            bare_path.write_bytes(docx(body(False, False)).read())
            report = analyze_word(full_path)
            bare = analyze_word(bare_path)
        exclusions = report["word_exclusions"]
        self.assertGreater(exclusions["cover_position"], 0)
        self.assertEqual(exclusions["cover_total"], exclusions["cover_position"])
        self.assertGreater(exclusions["metadata"], 0)
        self.assertEqual(bare["word_exclusions"]["cover_total"], 0)
        self.assertEqual(bare["word_exclusions"]["metadata"], 0)
        # Excluding the cover and metadata leaves the same Word Count as a
        # copy without them.
        self.assertEqual(
            report["metrics"]["word_count"]["value"],
            bare["metrics"]["word_count"]["value"],
        )
        self.assertNotIn("Example Bureau", str(report))

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
