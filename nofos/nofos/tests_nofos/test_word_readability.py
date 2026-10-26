"""Synthetic DOCX tests for the existing ephemeral analysis workflow."""

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from nofos.pdf_readability import PdfReadabilityError, analyze_uploaded_pdf
from nofos.pdf_readability_worker import analyze_word
from nofos.word_readability import DOCX_CONTENT_TYPE, word_html


def synthetic_docx(text=None, *, content_type=DOCX_CONTENT_TYPE, extra=None):
    text = (
        text
        if text is not None
        else (
            "Opportunity number: HRSA-26-106. Assistance listing: 93.123. "
            "The agency supports local programs. Applicants should submit a clear plan. "
            "The plan should describe community needs and expected outcomes."
        )
    )
    from xml.sax.saxutils import escape

    parts = {
        "[Content_Types].xml": (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            f'<Override PartName="/word/document.xml" ContentType="{content_type}"/></Types>'
        ),
        "_rels/.rels": (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            "</Relationships>"
        ),
        "word/document.xml": (
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body><w:p><w:r><w:t>{escape(text)}</w:t></w:r></w:p></w:body></w:document>"
        ),
        **(extra or {}),
    }
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    return output.getvalue()


def structured_docx():
    """Headings, paragraphs, a real numbered-list definition, table and note."""
    namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    relationships = "http://schemas.openxmlformats.org/package/2006/relationships"
    relation_type = (
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
    )
    return synthetic_docx(
        extra={
            "word/document.xml": f"""<w:document xmlns:w="{namespace}"><w:body>
        <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Opportunity number: HRSA-26-106</w:t></w:r></w:p>
        <w:p><w:r><w:t>Assistance listing: 93.123. Applicants should read this notice.</w:t></w:r></w:p>
        <w:p><w:r><w:t>The agency supports local programs. The plan describes community needs.</w:t></w:r></w:p>
        <w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="42"/></w:numPr></w:pPr><w:r><w:t>Submit a clear plan.</w:t></w:r></w:p>
        <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Criterion</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Points</w:t></w:r></w:p></w:tc></w:tr>
        <w:tr><w:tc><w:p><w:r><w:t>Impact</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>10</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
        <w:p><w:r><w:t>Read the supporting note.</w:t><w:footnoteReference w:id="1"/></w:r></w:p>
        </w:body></w:document>""",
            "word/styles.xml": f'<w:styles xmlns:w="{namespace}"><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style></w:styles>',
            "word/numbering.xml": f'<w:numbering xmlns:w="{namespace}"><w:abstractNum w:abstractNumId="1"><w:lvl w:ilvl="0"><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/></w:lvl></w:abstractNum><w:num w:numId="42"><w:abstractNumId w:val="1"/></w:num></w:numbering>',
            "word/footnotes.xml": f'<w:footnotes xmlns:w="{namespace}"><w:footnote w:id="1"><w:p><w:r><w:t>This is a synthetic supporting note.</w:t></w:r></w:p></w:footnote></w:footnotes>',
            "word/_rels/document.xml.rels": '<Relationships xmlns="'
            + relationships
            + '">'
            + "".join(
                f'<Relationship Id="{kind}" Type="{relation_type}{kind}" Target="{kind}.xml"/>'
                for kind in ("styles", "numbering", "footnotes")
            )
            + "</Relationships>",
        }
    )


class WordReadabilityTests(SimpleTestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "input.docx"
        lock = patch(
            "nofos.pdf_readability._LOCAL_LOCK_PATH", Path(directory.name) / "lock"
        )
        lock.start()
        self.addCleanup(lock.stop)

    def test_real_word_worker_returns_metrics_without_pdf_pages_or_source_text(self):
        upload = SimpleUploadedFile(
            "synthetic.docx", synthetic_docx(), content_type="application/octet-stream"
        )
        report = analyze_uploaded_pdf(upload)
        self.assertTrue(upload.closed)
        self.assertEqual(report["profile"], "word")
        self.assertIsNone(report["reliability"])
        for metric in report["metrics"].values():
            self.assertIsNone(metric["reliability"])
        self.assertGreater(report["metrics"]["word_count"]["value"], 10)
        self.assertNotIn("pages_total", report)
        self.assertNotIn("pages_analyzed", report)
        self.assertNotIn("HRSA-26-106", str(report))
        self.assertNotIn("Applicants should", str(report))
        self.assertIn("Template instructions", str(report["warnings"]))

    def test_templates_need_compound_hhs_nofo_context_and_distinct_signal(self):
        from nofos.pdf_format_recognition import recognize_nofo, recognize_word_nofo

        text = (
            "HHS Notice of Funding Opportunity. Opportunity number: [number]. "
            "Assistance listing: [listing]. Apply at Grants.gov. "
            "Applicants should submit a clear plan."
        )
        self.path.write_bytes(synthetic_docx(text))
        self.assertGreater(analyze_word(self.path)["metrics"]["word_count"]["value"], 0)
        # PDFs now accept an agency in page text plus Grants.gov. Word keeps
        # its existing compound agency/title rule rather than counting both.
        pdf_decision = recognize_nofo({}, text)
        self.assertEqual(pdf_decision.status, "supported")
        self.assertEqual(
            pdf_decision.signal_ids, ("hhs_agency_page_text", "grants_gov")
        )
        self.assertEqual(
            recognize_word_nofo(text).signal_ids,
            ("grants_gov", "hhs_nofo_template_context"),
        )
        self.assertEqual(
            recognize_word_nofo(
                "HHS-wide NOFO Master Template. See Grants.gov."
            ).status,
            "supported",
        )
        for missing in ("HHS", "Notice of Funding Opportunity", "Grants.gov"):
            candidate = text.replace(missing, "")
            self.assertEqual(recognize_word_nofo(candidate).status, "unsupported")
        for candidate in (
            "A personal letter. Grants.gov Grants.gov.",
            "HHS mentions Grants.gov in a technology report.",
            "Notice of funding opportunity from a private company. Grants.gov.",
        ):
            self.assertEqual(recognize_word_nofo(candidate).status, "unsupported")

    def test_reliability_projection_preserves_supplied_ratings_and_missing_evidence(
        self,
    ):
        from types import SimpleNamespace

        import hhs_nofo_metrics as metrics

        from nofos.pdf_readability_worker import _safe_result

        result = metrics.analyze(
            metrics.SourceBundle.from_html(
                b"<p>The agency supports local programs.</p>"
            ),
            profile="hhs-nofo-fy27-html@0.4.0",
        ).to_dict()
        result["coverage"].update(pages_extracted=1, pages_with_text=1)
        wrapped = SimpleNamespace(to_dict=lambda: result)
        self.assertIsNone(_safe_result(wrapped, "tagged", 1)["reliability"])
        self.assertEqual(_safe_result(wrapped, "generic", 1)["reliability"], "low")
        for level in ("high", "moderate", "low"):
            result["metrics"]["word_count"]["reliability"] = {"level": level}
            report = _safe_result(wrapped, "tagged", 1)
            self.assertEqual(report["reliability"], level)
            self.assertEqual(report["metrics"]["word_count"]["reliability"], level)
            self.assertIsNone(report["metrics"]["words_per_sentence"]["reliability"])

    def test_wrong_type_corrupt_macro_empty_and_non_nofo_are_safe(self):
        cases = (
            (b"not a zip PRIVATE", "invalid_word"),
            (
                synthetic_docx(
                    content_type="application/vnd.ms-word.document.macroEnabled.main+xml"
                ),
                "invalid_word",
            ),
            (synthetic_docx(extra={"word/vbaProject.bin": "PRIVATE"}), "invalid_word"),
            (synthetic_docx(""), "word_no_text"),
            (
                synthetic_docx("A personal letter unrelated to grants."),
                "word_format_unsupported",
            ),
        )
        for data, code in cases:
            with self.subTest(code=code):
                self.path.write_bytes(data)
                with self.assertRaises(ValueError) as caught:
                    analyze_word(self.path)
                self.assertEqual(str(caught.exception), code)

    def test_structured_word_preserves_blocks_and_reuses_html_metric_values(self):
        import hhs_nofo_metrics as metrics
        from bs4 import BeautifulSoup

        self.path.write_bytes(structured_docx())
        html, _ = word_html(self.path)
        soup = BeautifulSoup(html, "html.parser")
        for tag in ("h1", "p", "ul", "li", "table", "sup"):
            self.assertIsNotNone(soup.find(tag), tag)
        self.assertIn("synthetic supporting note", soup.get_text())
        expected = metrics.analyze(
            metrics.SourceBundle.from_html(html.encode()),
            profile="hhs-nofo-fy27-html@0.5.0",
        ).to_dict()
        report = analyze_word(self.path)
        for metric_id in report["metrics"]:
            if metric_id == "sentences_per_paragraph":
                continue
            self.assertEqual(
                report["metrics"][metric_id]["value"],
                expected["metrics"][metric_id]["value"],
                metric_id,
            )

    def test_word_uses_corrected_passive_method_without_changing_other_metrics(self):
        import hhs_nofo_metrics as metrics

        self.path.write_bytes(
            synthetic_docx(
                "Opportunity number: HRSA-26-106. Assistance listing: 93.123. "
                "Applications aren't accepted after Friday. "
                "The application wasn't reviewed by the agency. "
                "Applications aren't evaluated by the agency. "
                "The program is in need of additional staff. "
                "The applicant is indeed eligible."
            )
        )
        html, _ = word_html(self.path)
        source = metrics.SourceBundle.from_html(html.encode())
        old = metrics.analyze(source, profile="hhs-nofo-fy27-html@0.4.0")
        corrected = metrics.analyze(source, profile="hhs-nofo-fy27-html@0.5.0")
        before = old.metrics["passive_sentence_percentage"]
        after = corrected.metrics["passive_sentence_percentage"]
        self.assertEqual(before.components["passive_sentence_count"], 2)
        self.assertEqual(after.components["passive_sentence_count"], 3)
        self.assertEqual(
            before.components["sentence_count"], after.components["sentence_count"]
        )
        self.assertEqual(after.method.version, "0.4.0-provisional")
        report = analyze_word(self.path)
        self.assertEqual(report["version"], "0.6.0")
        self.assertEqual(
            report["metrics"]["passive_sentence_percentage"]["value"], after.value
        )
        for metric_id in old.metrics:
            if metric_id != "passive_sentence_percentage":
                self.assertEqual(
                    old.metrics[metric_id].to_dict(),
                    corrected.metrics[metric_id].to_dict(),
                )

    def test_expanded_limit_is_checked_before_conversion(self):
        self.path.write_bytes(synthetic_docx())
        with patch("nofos.word_readability.MAX_EXPANDED_BYTES", 20), patch(
            "mammoth.convert_to_html"
        ) as convert:
            with self.assertRaisesRegex(ValueError, "word_expanded_limit"):
                word_html(self.path)
        convert.assert_not_called()

    def test_entry_limit_and_duplicate_names_are_rejected(self):
        self.path.write_bytes(synthetic_docx())
        with patch("nofos.word_readability.MAX_ZIP_ENTRIES", 1):
            with self.assertRaisesRegex(ValueError, "word_expanded_limit"):
                word_html(self.path)
        with ZipFile(self.path, "a") as archive:
            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr("word/document.xml", "duplicate")
        with self.assertRaisesRegex(ValueError, "invalid_word"):
            word_html(self.path)

    def test_dtd_is_rejected_before_conversion(self):
        self.path.write_bytes(
            synthetic_docx(
                extra={
                    "word/comments.xml": '<!DOCTYPE x [<!ENTITY leak "PRIVATE">]><x>&leak;</x>'
                }
            )
        )
        with patch("mammoth.convert_to_html") as convert:
            with self.assertRaisesRegex(ValueError, "invalid_word"):
                word_html(self.path)
        convert.assert_not_called()

    def test_relationships_cannot_select_unvalidated_parts_or_hide_dtd(self):
        for part in ("alternate.DATA", "alternate.XML", "styles.DATA"):
            with self.subTest(part=part):
                self.path.write_bytes(
                    synthetic_docx(
                        extra={
                            f"word/{part}": '<!DOCTYPE x [<!ENTITY leak "PRIVATE">]><x>&leak;</x>'
                        }
                    )
                )
                with patch("mammoth.convert_to_html") as convert:
                    with self.assertRaisesRegex(ValueError, "invalid_word"):
                        word_html(self.path)
                convert.assert_not_called()
        relationships = (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/alternate.DATA"/>'
            "</Relationships>"
        )
        self.path.write_bytes(
            synthetic_docx(
                extra={"_rels/.rels": relationships, "word/alternate.DATA": "<x/>"}
            )
        )
        with self.assertRaisesRegex(ValueError, "invalid_word"):
            word_html(self.path)

    def test_converter_external_access_and_embedded_styles_disabled(self):
        self.path.write_bytes(synthetic_docx())
        import mammoth

        original = mammoth.convert_to_html
        with patch("mammoth.convert_to_html", wraps=original) as convert:
            word_html(self.path)
        self.assertIs(convert.call_args.kwargs["external_file_access"], False)
        self.assertIs(convert.call_args.kwargs["include_embedded_style_map"], False)

    def test_unsupported_extension_closes_upload_without_worker(self):
        for name in ("old.doc", "macro.docm", "script.html"):
            upload = SimpleUploadedFile(name, b"PRIVATE")
            with patch("nofos.pdf_readability.subprocess.run") as worker:
                with self.assertRaises(PdfReadabilityError) as caught:
                    analyze_uploaded_pdf(upload)
            self.assertEqual(caught.exception.code, "unsupported_file")
            self.assertTrue(upload.closed)
            worker.assert_not_called()

    def test_word_timeout_removes_temporary_input(self):
        import subprocess

        paths = []

        def timeout(command, **kwargs):
            paths.append(Path(command[3]))
            raise subprocess.TimeoutExpired(command, 15)

        with patch("nofos.pdf_readability.subprocess.run", side_effect=timeout):
            with self.assertRaises(PdfReadabilityError) as caught:
                analyze_uploaded_pdf(
                    SimpleUploadedFile("synthetic.docx", synthetic_docx())
                )
        self.assertEqual(caught.exception.code, "timeout")
        self.assertTrue(paths)
        self.assertFalse(paths[0].exists())
