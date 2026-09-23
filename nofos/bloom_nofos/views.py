import math
import os
import unicodedata

from constance import config
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_http_methods

from nofos.pdf_readability import (
    MAX_UPLOAD_BYTES,
    PdfReadabilityError,
    PdfSizeLimitUploadHandler,
    analyze_uploaded_pdf,
)

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
    return cleaned[:180] or "your PDF"


def _metric_rows(report):
    metrics = report.get("metrics") or {}
    rows = []
    for metric_id, label, explanation in PDF_METRIC_PRESENTATION:
        metric = metrics.get(metric_id) or {}
        value = metric.get("value")
        if (
            value is None
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            formatted = "Not available"
        elif metric_id == "word_count":
            formatted = f"{value:,.0f}"
        elif metric_id == "passive_sentence_percentage":
            formatted = f"{value:,.1f}%"
        else:
            formatted = f"{value:,.1f}"
        reliability = metric.get("reliability") or report.get("reliability")
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


@never_cache
@require_http_methods(["GET", "POST"])
@csrf_exempt
def pdf_readability(request):
    """Public, deliberately unlinked entry point for one ephemeral PDF report."""
    if not config.HHS_NOFO_PDF_METRICS_PILOT_ENABLED:
        response = render(request, "pdf_readability_unavailable.html", status=503)
        response["Cache-Control"] = "no-store"
        return response

    if request.method == "POST":
        # Must be installed before CSRF middleware reads multipart request.POST.
        request.upload_handlers.insert(0, PdfSizeLimitUploadHandler(request))
    return _pdf_readability_form(request)


@csrf_protect
def _pdf_readability_form(request):
    context = {"max_upload_mb": MAX_UPLOAD_BYTES // (1024 * 1024)}
    status = 200
    retry_after = None
    if request.method == "POST":
        uploads = request.FILES.getlist("pdf")
        if getattr(request, "pdf_upload_too_large", False):
            context["error"] = (
                f"This PDF is too large. Choose a file under {context['max_upload_mb']} MB."
            )
            status = 413
        elif len(uploads) != 1 or len(request.FILES) != 1:
            context["error"] = "Choose one PDF file to analyze."
            status = 400
        else:
            upload = uploads[0]
            try:
                report = analyze_uploaded_pdf(upload)
            except PdfReadabilityError as error:
                context["error"] = error.message
                status = error.http_status
                if error.code == "busy":
                    retry_after = "15"
            else:
                context.update(
                    {
                        "report": report,
                        "metric_rows": _metric_rows(report),
                        "filename": _safe_upload_name(upload.name),
                        "analysis_date": timezone.localdate(),
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
