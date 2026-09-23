"""Synthetic-only tests for the anonymous PDF processing boundary."""

import os
import subprocess
import sys
import tempfile
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from nofos.pdf_readability import (
    MAX_UPLOAD_BYTES,
    PdfReadabilityError,
    PdfSizeLimitUploadHandler,
    _analysis_slot,
    analyze_uploaded_pdf,
)
from nofos.pdf_readability_worker import _safe_result


def synthetic_text_pdf():
    """A small, non-sensitive PDF useful for signed-out browser checks too."""
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    for content in (
        b"Synthetic Program Notice",
        b"The agency supports local programs. Applicants should submit a clear plan. "
        b"The plan should describe community needs and expected outcomes.",
    ):
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
        )
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 72 700 Td (" + content + b") Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
    data = BytesIO()
    writer.write(data)
    return data.getvalue()


class PdfReadabilityTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        directory = tempfile.TemporaryDirectory(prefix="pdf-readability-test-lock-")
        self.addCleanup(directory.cleanup)
        self.lock_path = Path(directory.name) / "slot.lock"
        lock_patch = patch("nofos.pdf_readability._LOCAL_LOCK_PATH", self.lock_path)
        lock_patch.start()
        self.addCleanup(lock_patch.stop)

    def upload(self, contents):
        return SimpleUploadedFile(
            "private-nofo.pdf", contents, content_type="application/pdf"
        )

    def test_synthetic_pdf_report_has_safe_fields_only(self):
        report = analyze_uploaded_pdf(self.upload(synthetic_text_pdf()))
        self.assertEqual(report["profile"], "generic")
        self.assertEqual(report["pages_total"], 2)
        self.assertEqual(report["reliability"], "low")
        self.assertIn("word_count", report["metrics"])
        self.assertNotIn("private-nofo", repr(report))
        self.assertNotIn("source", report)
        self.assertNotIn("analysis_id", report)
        self.assertEqual(report["metrics"]["sentences_per_paragraph"]["value"], 3.0)

    def test_known_package_warning_is_sanitized(self):
        import hhs_nofo_metrics as metrics

        result = metrics.analyze(
            metrics.SourceBundle.from_pdf(synthetic_text_pdf()),
            profile="hhs-nofo-fy27-generic-pdf-estimate@0.4.0",
        )
        payload = result.to_dict()
        payload["warnings"].append(
            {
                "code": "unterminated_semantic_fragments_excluded",
                "message": "PRIVATE DOCUMENT CONTENT",
            }
        )
        report = _safe_result(SimpleNamespace(to_dict=lambda: payload), "generic", 2)
        self.assertIn(
            "Some sentence fragments were excluded from sentence-based measures.",
            report["warnings"],
        )
        self.assertNotIn("PRIVATE", repr(report))

    def test_non_pdf_is_a_safe_error(self):
        with self.assertRaises(PdfReadabilityError) as caught:
            analyze_uploaded_pdf(self.upload(b"private text, not a PDF"))
        self.assertEqual(caught.exception.code, "invalid_pdf")
        self.assertNotIn("private", str(caught.exception))

    def test_empty_file_and_scanned_pdf(self):
        for contents, expected in (
            (b"", "invalid_pdf"),
            (self._blank_pdf(), "no_text"),
        ):
            with self.subTest(expected=expected):
                with self.assertRaises(PdfReadabilityError) as caught:
                    analyze_uploaded_pdf(self.upload(contents))
                self.assertEqual(caught.exception.code, expected)

    def test_encrypted_pdf(self):
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.encrypt("secret")
        output = BytesIO()
        writer.write(output)
        with self.assertRaises(PdfReadabilityError) as caught:
            analyze_uploaded_pdf(self.upload(output.getvalue()))
        self.assertEqual(caught.exception.code, "encrypted")

    def test_too_many_pages(self):
        writer = PdfWriter()
        for _ in range(151):
            writer.add_blank_page(width=612, height=792)
        output = BytesIO()
        writer.write(output)
        with self.assertRaises(PdfReadabilityError) as caught:
            analyze_uploaded_pdf(self.upload(output.getvalue()))
        self.assertEqual(caught.exception.code, "too_many_pages")

    def test_file_slot_prevents_second_analysis_and_releases(self):
        with _analysis_slot():
            with self.assertRaises(PdfReadabilityError) as caught:
                analyze_uploaded_pdf(self.upload(synthetic_text_pdf()))
            self.assertEqual(caught.exception.code, "busy")
        report = analyze_uploaded_pdf(self.upload(synthetic_text_pdf()))
        self.assertEqual(report["pages_total"], 2)

    def test_file_slot_contends_across_processes(self):
        child_code = (
            "import django; django.setup(); "
            "import nofos.pdf_readability as p; "
            f"p._LOCAL_LOCK_PATH = __import__('pathlib').Path({str(self.lock_path)!r}); "
            "from nofos.pdf_readability import _analysis_slot, PdfReadabilityError; "
            "\ntry:\n with _analysis_slot(): print('acquired')"
            "\nexcept PdfReadabilityError as e: print(e.code)"
        )
        with _analysis_slot():
            result = subprocess.run(
                [sys.executable, "-c", child_code],
                cwd=Path(__file__).resolve().parents[2],
                env={**os.environ, "DJANGO_SETTINGS_MODULE": "bloom_nofos.settings"},
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
        self.assertEqual(result.stdout.strip().splitlines()[-1], "busy")

    def test_size_check_occurs_before_parsing(self):
        upload = self.upload(b"x")
        upload.size = MAX_UPLOAD_BYTES + 1
        with self.assertRaises(PdfReadabilityError) as caught:
            analyze_uploaded_pdf(upload)
        self.assertEqual(caught.exception.code, "too_large")

    def test_timeout_is_safe_and_tempfile_is_removed(self):
        paths = []
        nested_paths = []

        def timeout(command, **kwargs):
            paths.append(command[3])
            nested = (
                __import__("pathlib").Path(kwargs["env"]["TMPDIR"]) / "materialized.pdf"
            )
            nested.write_bytes(b"PRIVATE PDF CONTENT")
            nested_paths.append(nested)
            raise __import__("subprocess").TimeoutExpired(command, 15)

        with patch("nofos.pdf_readability.subprocess.run", side_effect=timeout):
            with self.assertRaises(PdfReadabilityError) as caught:
                analyze_uploaded_pdf(self.upload(synthetic_text_pdf()))
        self.assertEqual(caught.exception.code, "timeout")
        self.assertFalse(__import__("pathlib").Path(paths[0]).exists())
        self.assertFalse(nested_paths[0].exists())

    def test_child_crash_is_safe_and_tempfile_is_removed(self):
        paths = []

        def crashed(command, **kwargs):
            paths.append(command[3])
            return __import__("subprocess").CompletedProcess(
                command, 1, b"SECRET SOURCE"
            )

        with patch("nofos.pdf_readability.subprocess.run", side_effect=crashed):
            with self.assertRaises(PdfReadabilityError) as caught:
                analyze_uploaded_pdf(self.upload(synthetic_text_pdf()))
        self.assertEqual(caught.exception.code, "unavailable")
        self.assertNotIn("SECRET", str(caught.exception))
        self.assertFalse(__import__("pathlib").Path(paths[0]).exists())

    def test_upload_handler_stops_at_limit(self):
        request = type("Request", (), {"META": {}})()
        handler = PdfSizeLimitUploadHandler(request)
        handler._received = MAX_UPLOAD_BYTES
        with self.assertRaises(
            __import__(
                "django.core.files.uploadhandler", fromlist=["StopUpload"]
            ).StopUpload
        ):
            handler.receive_data_chunk(b"x", 0)
        self.assertTrue(request.pdf_upload_too_large)

    @staticmethod
    def _blank_pdf():
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        output = BytesIO()
        writer.write(output)
        return output.getvalue()
