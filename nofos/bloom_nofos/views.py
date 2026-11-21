import hashlib
import logging
import os
import time
import unicodedata
from pathlib import Path

from constance import config
from django.conf import settings
from django.core.files.uploadhandler import TemporaryFileUploadHandler
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_http_methods, require_POST

from nofos.pdf_readability import (
    PdfReadabilityError,
    PdfSizeLimitUploadHandler,
    analyze_uploaded_pdf,
)
from nofos.pdf_readability_metrics import record_attempt, retention_days
from nofos.readability_scratch import CheckerDiskUploadHandler, request_workspace
from nofos.readability_upload_limits import MIB, PDF_UPLOAD_BYTES, WORD_UPLOAD_BYTES
from nofos.readability_word_export import (
    CHECKER_SALT,
    checker_report_token,
    download_report,
    format_report_value,
)

logger = logging.getLogger("django.request.pdf_readability")

PDF_METRIC_PRESENTATION = (
    ("word_count", "Word count", "Estimated number of words recovered from the PDF."),
    (
        "words_per_sentence",
        "Words per sentence",
        "Average length of measured sentences.",
    ),
    (
        "sentences_per_paragraph",
        "Sentences per paragraph",
        "Average length of reconstructed paragraphs, where available.",
    ),
    (
        "flesch_kincaid_grade_level",
        "Flesch-Kincaid Grade Level",
        "An approximate U.S. school grade level for the measured text.",
    ),
    (
        "passive_sentence_percentage",
        "Passive sentences",
        "Estimated share of measured sentences identified as passive.",
    ),
)


def _safe_upload_name(name):
    # Browsers normally send a basename, but do not trust the client path or
    # control characters when displaying or printing the report.
    basename = os.path.basename(str(name).replace("\\", "/"))
    cleaned = "".join(
        character
        for character in basename
        if not unicodedata.category(character).startswith("C")
    ).strip()
    return cleaned[:180] or "your document"


def _metric_rows(report):
    metrics = report.get("metrics") or {}
    rows = []
    for metric_id, label, explanation in PDF_METRIC_PRESENTATION:
        if metric_id == "word_count" and report.get("profile") == "word":
            explanation = (
                "Estimated number of words recovered from the Word conversion."
            )
        metric = metrics.get(metric_id) or {}
        formatted = format_report_value(metric_id, metric.get("value"))
        # A metric without evidence must not inherit another metric's rating.
        # Generic PDF extraction retains its explicit low-confidence policy.
        reliability = metric.get("reliability")
        if report.get("profile") == "generic":
            reliability = "low"
        rows.append(
            {
                "label": label,
                "explanation": explanation,
                "value": formatted,
                "status": (
                    "Estimated" if formatted != "Not available" else "Unavailable"
                ),
                "reliability": (
                    reliability
                    if reliability in {"high", "moderate", "low"}
                    else "unknown"
                ),
            }
        )
    return rows


@csrf_exempt
def readability_redirect(request, route_name):
    """Keep shared links and pending uploads usable after the tool rename."""
    return redirect(route_name, permanent=True, preserve_request=True)


def checker_access(request):
    """Return whether this request may use the checker, and its usage label.

    Uses only the session-backed user and Constance switches, so callers can
    decide before anything reads or parses the request body.
    """
    signed_in = request.user.is_authenticated
    source = "authenticated" if signed_in else "public"
    enabled = config.HHS_NOFO_PDF_METRICS_PILOT_ENABLED or (
        signed_in and config.HHS_NOFO_AUTHENTICATED_PDF_METRICS_PILOT_ENABLED
    )
    return enabled, source


@never_cache
@require_http_methods(["GET", "POST"])
@csrf_exempt
def pdf_readability(request):
    """Deliberately unlinked entry point for one ephemeral readability report.

    The public switch opens it to everyone. The signed-in switch keeps it open
    to signed-in users while the public switch is off.
    """
    enabled, source = checker_access(request)
    return _pdf_readability_workflow(request, enabled, source)


@never_cache
@require_POST
def pdf_readability_word_export(request):
    enabled, _ = checker_access(request)
    if not enabled:
        return HttpResponse("The readability checker is unavailable.", status=403)
    return download_report(request, salt=CHECKER_SALT)


@csrf_exempt
def retired_checker_redirect(request):
    """The signed-in checker moved to the single public URL.

    Never forward a pending upload: a POST from a page left open across the
    change is answered without reading its body and lands on an empty form.
    """
    return redirect("pdf_readability", permanent=True)


def _pdf_readability_workflow(request, enabled, source):
    started = time.monotonic()
    if not enabled:
        # Disabled is an intentional access state, not a service failure.
        # Return before CSRF/form handling can parse an uploaded document.
        status = 403 if request.method == "POST" else 200
        response = render(request, "pdf_readability_unavailable.html", status=status)
        response["Cache-Control"] = "no-store"
        if request.method == "POST":
            _record_pdf_attempt(source, "disabled", response.status_code, started)
        return response

    request.pdf_readability_source = source
    try:
        if request.method == "POST":
            # Install both handlers before CSRF reads multipart request.POST.
            with request_workspace() as workspace:
                request.readability_workspace = workspace
                request.upload_handlers = [
                    PdfSizeLimitUploadHandler(request),
                    *(
                        (
                            CheckerDiskUploadHandler(request, workspace)
                            if isinstance(handler, TemporaryFileUploadHandler)
                            else handler
                        )
                        for handler in request.upload_handlers
                    ),
                ]
                response = _pdf_readability_form(request)
        else:
            response = _pdf_readability_form(request)
    except Exception:
        # Include unexpected formatting/rendering failures without relying on
        # the same template or exposing uploaded content in a debug response.
        if request.method == "POST":
            request.pdf_readability_outcome = "internal_error"
        logger.warning("PDF readability request failed unexpectedly.")
        response = HttpResponse(
            "Document analysis failed unexpectedly. Please try again later.",
            status=500,
            content_type="text/plain",
        )
    if request.method == "POST" and hasattr(request, "pdf_readability_outcome"):
        _record_pdf_attempt(
            source,
            request.pdf_readability_outcome,
            response.status_code,
            started,
            file_category=getattr(request, "pdf_readability_file_category", "unknown"),
        )
    response["Cache-Control"] = "no-store"
    return response


def _record_pdf_attempt(source, outcome, status, started, file_category="unknown"):
    record_attempt(outcome, status, started, source=source, file_category=file_category)


@csrf_protect
def _pdf_readability_form(request):
    pdf_size = f"{PDF_UPLOAD_BYTES // MIB} MiB"
    word_size = f"{WORD_UPLOAD_BYTES // MIB} MiB"
    size_hint = f"One PDF file up to {pdf_size} or Word (.docx) file up to {word_size}."
    size_error = f"This file is too large. {size_hint}"
    context = {
        "file_label": "Choose a PDF or Word document",
        "file_accept": (
            ".pdf,.docx,application/pdf,"
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        "outcome_retention_days": retention_days(request.pdf_readability_source),
        "outcome_recording_enabled": (
            settings.AUTHENTICATED_PDF_READABILITY_ATTEMPT_RECORDING_ENABLED
            if request.pdf_readability_source == "authenticated"
            else settings.PDF_READABILITY_ATTEMPT_RECORDING_ENABLED
        ),
        "upload_hint": (
            f"{size_hint} "
            "Scanned PDFs need optical character recognition (OCR) "
            "to make their text selectable before uploading."
        ),
    }
    status = 200
    retry_after = None
    if request.method == "POST":
        uploads = request.FILES.getlist("pdf")
        # Classify only one completed upload in the expected field. This is its
        # attempted format, not validation of its contents. Never retain its name.
        if (
            len(uploads) == 1
            and len(request.FILES) == 1
            and not getattr(request, "pdf_upload_too_large", False)
        ):
            suffix = Path(str(uploads[0].name)).suffix.lower()
            request.pdf_readability_file_category = {
                ".pdf": "pdf",
                ".docx": "docx",
            }.get(suffix, "unknown")
        if getattr(request, "pdf_upload_too_large", False):
            request.pdf_readability_outcome = "too_large"
            context["error"] = size_error
            status = 413
        elif len(uploads) != 1 or len(request.FILES) != 1:
            request.pdf_readability_outcome = "invalid_pdf"
            context["error"] = "Choose one PDF or Word (.docx) file to analyze."
            status = 400
        else:
            upload = uploads[0]
            try:
                from nofos.word_comparisons import (
                    PERMISSION,
                    WordResultsForm,
                    enabled,
                    stage_run,
                )

                comparison_allowed = (
                    enabled()
                    and request.user.has_perm(PERMISSION)
                    and str(upload.name).lower().endswith(".docx")
                )
                fingerprint = None
                if comparison_allowed:
                    digest = hashlib.sha256()
                    for chunk in upload.chunks():
                        digest.update(chunk)
                    fingerprint = digest.hexdigest()
                    upload.seek(0)
                report = analyze_uploaded_pdf(
                    upload, workspace=request.readability_workspace
                )
            except PdfReadabilityError as error:
                request.pdf_readability_outcome = error.code
                context["error"] = (
                    size_error if error.code == "too_large" else error.message
                )
                status = error.http_status
                if error.code == "busy":
                    retry_after = "15"
            except Exception:
                # Parser/application failures must not expose document content,
                # identifiers, arbitrary exception messages or tracebacks.
                request.pdf_readability_outcome = "internal_error"
                context["error"] = (
                    "Document analysis failed unexpectedly. Please try again later."
                )
                status = 500
                logger.warning("PDF readability analysis failed unexpectedly.")
            else:
                request.pdf_readability_outcome = "success"
                # Keep detected identifiers out of the page data and comparison handoff.
                opportunity_number = report.pop("opportunity_number", None)
                assistance_listing_number = report.pop(
                    "assistance_listing_number", None
                )
                if comparison_allowed and report.get("profile") == "word":
                    context["comparison_form"] = WordResultsForm()
                    context["comparison_run"] = stage_run(
                        request, report, _safe_upload_name(upload.name), fingerprint
                    )
                context.update(
                    {
                        "report": report,
                        "metric_rows": _metric_rows(report),
                        "word_export_report": checker_report_token(
                            request,
                            report,
                            assistance_listing_number=assistance_listing_number,
                            opportunity_number=opportunity_number,
                        ),
                        "filename": _safe_upload_name(upload.name),
                        "analysis_date": timezone.localdate(),
                        "source_word": report.get("profile") == "word",
                    }
                )
    response = render(request, "pdf_readability.html", context, status=status)
    response["Cache-Control"] = "no-store"
    if retry_after:
        response["Retry-After"] = retry_after
    return response


def index(request):
    # Redirect logged-in users to the NOFO index page
    if request.user.is_authenticated:
        return redirect("nofos:nofo_index")

    return render(request, "index.html")


def page_not_found(request, exception=None):
    return render(request, "404.html", status=404)


def server_error(request, exception=None):
    return render(request, "500.html", status=500)


# Note: commenting this out because it is handled by middleware. Explanation in the commit message.
# def bad_request(request, exception=None):
#     return render(request, "400.html", status=400)
