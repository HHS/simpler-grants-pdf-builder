"""Export the displayed readability results without carrying the source document."""

import math

from bloom_nofos.utils import (
    generate_html_docx_download_response,
    is_grabzit_word_export_enabled,
)
from constance import config
from django.core import signing
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.cache import add_never_cache_headers

from .readability_format import format_metric_number

CLEARANCE_METRICS = (
    ("word_count", "Word count"),
    ("words_per_sentence", "Words per sentence"),
    ("flesch_kincaid_grade_level", "Flesch-Kincaid Grade Level"),
    ("passive_sentence_percentage", "Passive sentences"),
)
DRAFTING_METRICS = (("sentences_per_paragraph", "Sentences per paragraph"),)
SCOPE_NOTES = {
    "word": (
        "Word count uses recovered Word text after skipping recognized covers, "
        "tables of contents, and template instructions. Other draft material may count."
    ),
    "generic": (
        "Word count uses text recovered from the PDF page layout. Some text may be "
        "missed or read out of order."
    ),
    "pdf": (
        "Word count uses text recovered using the PDF’s structure tags. Some text "
        "may be missed or read out of order."
    ),
    "builder": "Word count includes the NOFO text measured by NOFO Builder.",
}
CHECKER_SALT = "readability-word-export.checker"


def builder_salt(request, nofo):
    return f"readability-word-export.builder.{request.user.pk}.{nofo.pk}"


def format_report_value(metric_id, value):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        return "Not available"
    if metric_id == "word_count":
        return f"{value:,.0f}"
    formatted = format_metric_number(value)
    return f"{formatted}%" if metric_id == "passive_sentence_percentage" else formatted


def word_export_enabled(request):
    return (
        config.HHS_NOFO_READABILITY_WORD_EXPORT_ENABLED
        and is_grabzit_word_export_enabled(request.get_host())
    )


def report_token(request, payload, *, scope, salt):
    if not word_export_enabled(request):
        return ""
    metrics = payload.get("metrics") or {}
    # Keep only the five formatted values and a fixed scope key. Package payloads
    # can include source metadata and diagnostic text.
    values = {
        metric_id: format_report_value(
            metric_id, (metrics.get(metric_id) or {}).get("value")
        )
        for metric_id, _ in CLEARANCE_METRICS + DRAFTING_METRICS
    }
    if scope == "builder":
        components = (metrics.get("words_per_sentence") or {}).get("components") or {}
        values["sentences_per_paragraph"] = format_report_value(
            "sentences_per_paragraph", components.get("sentences_per_paragraph")
        )
    return signing.dumps({"values": values, "scope": scope}, salt=salt)


def checker_report_token(request, report):
    profile = report.get("profile")
    scope = profile if profile in {"word", "generic"} else "pdf"
    return report_token(request, report, scope=scope, salt=CHECKER_SALT)


def add_builder_report_header(response, request, nofo, payload):
    token = report_token(
        request, payload, scope="builder", salt=builder_salt(request, nofo)
    )
    if token:
        response["X-Readability-Word-Report"] = token


def download_report(request, *, salt, nofo=None):
    if not word_export_enabled(request):
        response = HttpResponse(
            "Word export is not available in this environment.", status=503
        )
        add_never_cache_headers(response)
        return response

    try:
        report = signing.loads(request.POST.get("report", ""), salt=salt, max_age=3600)
    except signing.BadSignature:
        response = HttpResponse(
            "These results are no longer available for download. "
            "Check readability again and retry the download.",
            status=400,
        )
    else:
        values = report["values"]
        html = render_to_string(
            "readability_word_report.html",
            {
                "clearance_rows": [
                    (label, values[key]) for key, label in CLEARANCE_METRICS
                ],
                "drafting_rows": [
                    (label, values[key]) for key, label in DRAFTING_METRICS
                ],
                "scope": SCOPE_NOTES[report["scope"]],
                "title": nofo.title if nofo else "",
                "number": nofo.number if nofo else "",
            },
        )
        response = generate_html_docx_download_response(
            request=request, html=html, filename_base="readability-metrics"
        )
    add_never_cache_headers(response)
    return response
