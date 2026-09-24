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
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
)

from nofos.pdf_format_recognition import (
    RecognitionPolicy,
    recognize_nofo,
)
from nofos.pdf_readability import (
    MAX_UPLOAD_BYTES,
    PdfReadabilityError,
    PdfSizeLimitUploadHandler,
    _analysis_slot,
    analyze_uploaded_pdf,
)
from nofos.pdf_readability_worker import (
    TAGGED_ADAPTER,
    _analyze_metrics,
    _safe_result,
    analyze,
)


def synthetic_text_pdf(contents=None, metadata=None):
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
    if contents is None:
        contents = (
            b"Synthetic Program Notice",
            b"The agency supports local programs. Applicants should submit a clear plan. "
            b"The plan should describe community needs and expected outcomes.",
        )
    for content in contents:
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
        )
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 72 700 Td (" + content + b") Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
    if metadata:
        writer.add_metadata(metadata)
    data = BytesIO()
    writer.write(data)
    return data.getvalue()


def synthetic_nofo_pdf():
    return synthetic_text_pdf(
        contents=(
            b"Opportunity number: HRSA-26-106  Assistance listing: 93.123",
            b"The agency supports local programs. Applicants should submit a clear plan.",
        )
    )


def synthetic_tagged_pdf(headings):
    """A one-page tagged PDF with genuine MCID-backed heading groups."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    elements = ArrayObject()
    content = []
    for index, heading in enumerate(headings):
        assert heading.isascii() and "(" not in heading and ")" not in heading
        elements.append(
            writer._add_object(
                DictionaryObject(
                    {
                        NameObject("/Type"): NameObject("/StructElem"),
                        NameObject("/S"): NameObject("/H1"),
                        NameObject("/Pg"): page.indirect_reference,
                        NameObject("/K"): NumberObject(index),
                    }
                )
            )
        )
        content.append(
            f"/H1 <</MCID {index}>> BDC BT /F1 12 Tf 72 {700-index*24} Td ({heading}) Tj ET EMC".encode()
        )
    root = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/StructTreeRoot"),
                NameObject("/K"): elements,
            }
        )
    )
    writer._root_object[NameObject("/StructTreeRoot")] = root
    stream = DecodedStreamObject()
    stream.set_data(b"\n".join(content))
    page[NameObject("/Contents")] = writer._add_object(stream)
    data = BytesIO()
    writer.write(data)
    return data.getvalue()


class PdfReadabilityTests(SimpleTestCase):
    def test_tagged_adapter_pin_matches_installed_package(self):
        from hhs_nofo_metrics.adapters.tagged_pdf import ADAPTER_VERSION

        self.assertEqual(TAGGED_ADAPTER, f"hhs-tagged-pdf-adapter@{ADAPTER_VERSION}")

    def test_recognition_accepts_two_distinct_loose_signals(self):
        cases = (
            (
                {"/Author": "Health Resources and Services Administration"},
                "Apply at https://www.grants.gov.",
                ("hhs_agency_metadata", "grants_gov"),
            ),
            (
                {},
                "Opportunity number: HHS-2026-ACL-AOA-\nPPNU-0003 "
                "Federal Assistance Listing Number 93.045",
                ("opportunity_number", "assistance_listing"),
            ),
            (
                {"/Description": "Funding opportunity no. TI-26-006"},
                "See Grants.gov for updates.",
                ("opportunity_number", "grants_gov"),
            ),
        )
        for metadata, text, expected in cases:
            with self.subTest(expected=expected):
                decision = recognize_nofo(metadata, text)
                self.assertEqual(decision.status, "supported")
                self.assertEqual(decision.signal_ids, expected)
                self.assertNotIn("HRSA", repr(decision))

    def test_recognition_does_not_double_count_or_accept_unlabeled_ids(self):
        decision = recognize_nofo(
            {"/Author": "NIH", "/Title": "NIH funding update"},
            "NIH research notice with reference ABC-26-123 and 93.123.",
        )
        self.assertEqual(decision.status, "unsupported")
        self.assertEqual(decision.signal_ids, ("hhs_agency_metadata",))

    def test_worker_accepts_recognized_untagged_pdf(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.pdf"
            path.write_bytes(synthetic_nofo_pdf())
            with patch(
                "hhs_nofo_metrics.inspect_adapter_support",
                return_value=[{"assessment": {"status": "unsupported"}}],
            ), patch(
                "nofos.pdf_readability_worker._analyze_metrics",
                return_value={"recognized": True},
            ) as metrics:
                self.assertEqual(
                    analyze(path, 150),
                    {"recognized": True},
                )
                metrics.assert_called_once()

    def test_real_tagged_pdf_path_with_loose_signals(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic-tagged.pdf"
            path.write_bytes(
                synthetic_tagged_pdf(
                    (
                        "Opportunity number: HRSA-26-106",
                        "Assistance listing: 93.123",
                        "Budget",
                    )
                )
            )
            report = analyze(path, 150)
        self.assertEqual(report["profile"], "tagged")
        self.assertEqual(report["pages_total"], 1)
        self.assertGreater(report["scope"]["recovered_word_count"], 0)

    def test_real_pdf_negative_and_unextractable_inputs(self):
        for contents, expected in (
            ((b"Unrelated annual report",), "format_unsupported"),
            ((b"",), "format_indeterminate"),
        ):
            with self.subTest(expected=expected):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "synthetic.pdf"
                    path.write_bytes(synthetic_text_pdf(contents=contents))
                    with self.assertRaises(ValueError) as caught:
                        analyze(path, 150)
                self.assertEqual(str(caught.exception), expected)

    def test_worker_fails_closed_with_invalid_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.pdf"
            path.write_bytes(synthetic_nofo_pdf())
            for policy in (
                RecognitionPolicy(minimum_signals=0),
                RecognitionPolicy(minimum_signals=5),
                RecognitionPolicy(pages_to_inspect=0),
            ):
                with self.subTest(policy=policy), self.assertRaises(
                    ValueError
                ) as caught:
                    analyze(path, 150, policy=policy)
                self.assertEqual(str(caught.exception), "format_unavailable")

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
        from hhs_nofo_metrics import SourceBundle

        report = _analyze_metrics(
            SourceBundle.from_pdf(synthetic_text_pdf()), "unsupported", 2
        )
        self.assertEqual(report["profile"], "generic")
        self.assertEqual(report["pages_total"], 2)
        self.assertEqual(report["reliability"], "low")
        self.assertIn("word_count", report["metrics"])
        self.assertNotIn("private-nofo", repr(report))
        self.assertNotIn("source", report)
        self.assertNotIn("analysis_id", report)
        self.assertEqual(report["metrics"]["sentences_per_paragraph"]["value"], 3.0)
        self.assertEqual(
            report["scope"],
            {
                "recovered_word_count": 23,
                "sentence_word_count": 20,
                "complete_sentence_count": 3,
                "excluded_word_count": 3,
                "excluded_word_percentage": 13.0,
            },
        )

    def test_worker_receives_no_web_secrets_and_still_extracts_text(self):
        original_run = subprocess.run
        child_environments = []

        def run_child(*args, **kwargs):
            child_environments.append(kwargs["env"])
            return original_run(*args, **kwargs)

        injected = {
            "AWS_SECRET_ACCESS_KEY": "synthetic-aws-secret",
            "DATABASE_URL": "synthetic-database-secret",
            "DJANGO_SECRET_KEY": "synthetic-django-secret",
            "PYTHONPATH": "/synthetic/unsafe/import/path",
        }
        with patch.dict(os.environ, injected), patch(
            "nofos.pdf_readability.subprocess.run", side_effect=run_child
        ):
            report = analyze_uploaded_pdf(self.upload(synthetic_nofo_pdf()))

        self.assertEqual(report["profile"], "generic")
        self.assertEqual(len(child_environments), 1)
        child_env = child_environments[0]
        for name in injected:
            self.assertNotIn(name, child_env)
        self.assertEqual(
            set(child_env),
            {"PATH", "PYTHONDONTWRITEBYTECODE", "TMPDIR", "TMP", "TEMP"},
        )
        self.assertEqual(child_env["TMPDIR"], child_env["TMP"])
        self.assertEqual(child_env["TMPDIR"], child_env["TEMP"])

    def test_scope_counts_reject_invalid_or_inconsistent_values(self):
        import hhs_nofo_metrics as metrics

        result = metrics.analyze(
            metrics.SourceBundle.from_pdf(synthetic_text_pdf()),
            profile="hhs-nofo-fy27-generic-pdf-estimate@0.4.0",
        )
        payload = result.to_dict()
        payload["metrics"]["word_count"]["value"] = 4
        payload["metrics"]["words_per_sentence"]["components"]["word_count"] = 8
        payload["metrics"]["words_per_sentence"]["components"]["sentence_count"] = True
        report = _safe_result(SimpleNamespace(to_dict=lambda: payload), "generic", 2)
        self.assertEqual(report["scope"]["recovered_word_count"], 4)
        self.assertEqual(report["scope"]["sentence_word_count"], 8)
        self.assertIsNone(report["scope"]["complete_sentence_count"])
        self.assertIsNone(report["scope"]["excluded_word_count"])
        self.assertIsNone(report["scope"]["excluded_word_percentage"])

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
            (self._blank_pdf(), "format_indeterminate"),
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
                analyze_uploaded_pdf(self.upload(synthetic_nofo_pdf()))
            self.assertEqual(caught.exception.code, "busy")
        report = analyze_uploaded_pdf(self.upload(synthetic_nofo_pdf()))
        self.assertEqual(report["profile"], "generic")

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
