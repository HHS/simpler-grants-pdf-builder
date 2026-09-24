"""Bounded, non-persisting entry point for the anonymous PDF pilot."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

from django.core.files.uploadhandler import FileUploadHandler, StopUpload
from django.db import connection

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_PAGES = 150
TIMEOUT_SECONDS = 15
_ADVISORY_LOCK_ID = 0x50444652454144  # "PDFREAD", distinct from app data locks.
_LOCAL_LOCK_PATH = Path(tempfile.gettempdir()) / "builder-pdf-readability.lock"

_ERRORS = {
    "invalid_pdf": (
        "We could not read this PDF. Check that it is a valid PDF and try again.",
        400,
    ),
    "too_large": ("This PDF is too large. Choose a PDF smaller than 15 MB.", 413),
    "too_many_pages": (
        "This PDF has too many pages. The pilot supports up to 150 pages.",
        400,
    ),
    "encrypted": (
        "Password-protected PDFs are not supported. Upload an unlocked copy.",
        400,
    ),
    "no_text": (
        "This PDF has no extractable text. Scanned PDFs need OCR before analysis.",
        400,
    ),
    "format_unsupported": (
        "This PDF does not match a supported pilot format. Check that you used an approved HHS FY27 template or NOFO development tool, and contact your agency's grants policy office for help.",
        400,
    ),
    "format_indeterminate": (
        "We could not confirm this PDF is in a supported pilot format. Check that you used an approved HHS FY27 template or NOFO development tool, and contact your agency's grants policy office for help.",
        400,
    ),
    "format_unavailable": (
        "Format recognition is not configured for this pilot yet. No readability report was calculated. Please try again after the pilot opens.",
        503,
    ),
    "timeout": (
        "This PDF took too long to analyze. Try a shorter PDF or try again later.",
        503,
    ),
    "busy": ("The analyzer is busy. Please try again in a moment.", 429),
    "unavailable": (
        "PDF analysis is temporarily unavailable. Please try again later.",
        503,
    ),
}


class PdfReadabilityError(Exception):
    """A typed, user-safe failure; never contains parser text or document data."""

    def __init__(self, code: str):
        if code not in _ERRORS:
            code = "unavailable"
        self.code = code
        self.message, self.http_status = _ERRORS[code]
        super().__init__(self.message)


class PdfSizeLimitUploadHandler(FileUploadHandler):
    """Stop receiving the request once a single PDF exceeds the pilot limit."""

    def __init__(self, request):
        super().__init__(request)
        self._received = 0

    def receive_data_chunk(self, raw_data, start):
        self._received += len(raw_data)
        if self._received > MAX_UPLOAD_BYTES:
            self.request.pdf_upload_too_large = True
            raise StopUpload(connection_reset=False)
        return raw_data

    def file_complete(self, file_size):
        return None


@contextmanager
def _analysis_slot():
    """One global active analysis on PostgreSQL, without a request-history row."""
    if connection.vendor == "postgresql":
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_try_advisory_lock(%s)", [_ADVISORY_LOCK_ID])
                acquired = cursor.fetchone()[0]
        except Exception:
            raise PdfReadabilityError("unavailable") from None
        if not acquired:
            raise PdfReadabilityError("busy")
        try:
            yield
        finally:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_unlock(%s)", [_ADVISORY_LOCK_ID])
            except Exception:
                # Closing the owning connection releases its session locks.
                connection.close()
                raise PdfReadabilityError("unavailable") from None
    else:
        # File locking keeps SQLite development/test workers consistent too.
        import fcntl

        try:
            descriptor = os.open(_LOCAL_LOCK_PATH, os.O_CREAT | os.O_RDWR, 0o600)
        except OSError:
            raise PdfReadabilityError("unavailable") from None
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise PdfReadabilityError("busy") from None
            try:
                yield
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _analyze_uploaded_pdf(upload) -> dict:
    if upload is None or not hasattr(upload, "chunks"):
        raise PdfReadabilityError("invalid_pdf")
    if isinstance(upload.size, int) and upload.size > MAX_UPLOAD_BYTES:
        raise PdfReadabilityError("too_large")

    with _analysis_slot():
        with tempfile.TemporaryDirectory(prefix="pdf-readability-") as directory:
            pdf_path = Path(directory) / "input.pdf"
            byte_count = 0
            try:
                with pdf_path.open("xb") as output:
                    os.chmod(pdf_path, 0o600)
                    for chunk in upload.chunks():
                        byte_count += len(chunk)
                        if byte_count > MAX_UPLOAD_BYTES:
                            raise PdfReadabilityError("too_large")
                        output.write(chunk)
                if byte_count == 0:
                    raise PdfReadabilityError("invalid_pdf")
                command = [
                    sys.executable,
                    "-m",
                    "nofos.pdf_readability_worker",
                    str(pdf_path),
                    str(MAX_PAGES),
                ]
                try:
                    process = subprocess.run(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        timeout=TIMEOUT_SECONDS,
                        check=False,
                        cwd=Path(__file__).resolve().parents[1],
                        # The PDF parser must not inherit web-process credentials
                        # or Python startup hooks from the application environment.
                        env={
                            "PATH": os.defpath,
                            "PYTHONDONTWRITEBYTECODE": "1",
                            "TMPDIR": directory,
                            "TMP": directory,
                            "TEMP": directory,
                        },
                    )
                except subprocess.TimeoutExpired as exc:
                    raise PdfReadabilityError("timeout") from None
                except OSError as exc:
                    raise PdfReadabilityError("unavailable") from None
                if process.returncode != 0 or len(process.stdout) > 64 * 1024:
                    raise PdfReadabilityError("unavailable")
                try:
                    envelope = json.loads(process.stdout)
                except (ValueError, UnicodeDecodeError):
                    raise PdfReadabilityError("unavailable") from None
                if not isinstance(envelope, dict):
                    raise PdfReadabilityError("unavailable")
                if not envelope.get("ok"):
                    raise PdfReadabilityError(envelope.get("code"))
                report = envelope.get("report")
                if not isinstance(report, dict) or not isinstance(
                    report.get("metrics"), dict
                ):
                    raise PdfReadabilityError("unavailable")
                return report
            except PdfReadabilityError:
                raise
            except Exception:
                # Do not propagate arbitrary parser/upload errors into Django's
                # traceback logging middleware.
                raise PdfReadabilityError("unavailable") from None


def analyze_uploaded_pdf(upload) -> dict:
    """Analyze one Django UploadedFile and return only safe, displayable fields."""
    try:
        return _analyze_uploaded_pdf(upload)
    finally:
        if upload is not None and hasattr(upload, "close"):
            try:
                upload.close()
            except Exception:
                # Django's request cleanup will also run; do not turn a safe
                # analysis outcome into a content-bearing exception.
                pass
