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
        "tables of contents, template instructions, and Builder metadata. Other draft material may count. "
        "Text in headers, footers, text boxes, and images may be missed."
    ),
    "generic": (
        "Word count uses text recovered from the PDF page layout. Some text may be "
        "missed or read out of order. Draft instructions and placeholders may count."
    ),
    "pdf": (
        "Word count uses text recovered using the PDF’s structure tags. Some text "
        "may be missed or read out of order."
    ),
    "builder": "Word count includes the NOFO text measured by NOFO Builder.",
}
WORD_EXCLUSIONS = ("cover_total", "table_of_contents", "instruction", "metadata")
SCOPE_COUNTS = (
    "recovered_word_count",
    "sentence_word_count",
    "complete_sentence_count",
    "excluded_word_count",
)
CHECKER_SALT = "readability-word-export.checker"
# Fixed recognition codes from pdf_format_recognition, in display order.
NOFO_SIGNAL_LABELS = {
    "hhs_agency_metadata": "an HHS agency name",
    "hhs_agency_page_text": "an HHS agency name",
    "opportunity_number": "an opportunity number",
    "assistance_listing": "an Assistance Listing number",
    "grants_gov": "a Grants.gov reference",
    "hhs_nofo_template_context": "HHS NOFO template wording",
}
TEMPLATE_PARTS = (
    ("cover_total", "a cover page"),
    ("table_of_contents", "a table of contents"),
    ("instruction", "template instructions"),
)


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


def report_token(request, payload, *, scope, salt, extra=None):
    if not word_export_enabled(request):
        return ""
    metrics = payload.get("metrics") or {}
    # Package payloads can include source metadata and diagnostic text.
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
    report = {"values": values, "scope": scope, **(extra or {})}
    if scope != "builder":
        report["details"] = checker_scope_details(payload, scope)
    report["nofo_check"] = nofo_check(payload, scope)
    return signing.dumps(report, salt=salt)


def join_labels(labels):
    labels = list(dict.fromkeys(labels))
    if len(labels) < 3:
        return " and ".join(labels)
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


def nofo_check(payload, scope):
    """Fixed-text summary of what the tool verified about the document format.

    Only fixed codes and counts feed this; no document text is used.
    """
    if scope == "builder":
        return {
            "recognized": "Yes",
            "recognized_note": "This NOFO was created in NOFO Builder.",
            "structure": "Yes",
            "structure_note": (
                "NOFO Builder measured the NOFO’s own sections and subsections."
            ),
        }
    signals = payload.get("nofo_signals")
    labels = [
        NOFO_SIGNAL_LABELS[code]
        for code in (signals if isinstance(signals, list) else [])
        if code in NOFO_SIGNAL_LABELS
    ]
    check = {
        # Only uploads the checker recognized as an HHS NOFO receive a report.
        "recognized": "Yes",
        "recognized_note": (
            f"The checker found {join_labels(labels)} near the beginning."
            if labels
            else "The checker found basic HHS NOFO details near the beginning."
        ),
    }
    if scope == "word":
        exclusions = payload.get("word_exclusions") or {}
        found = [
            label
            for key, label in TEMPLATE_PARTS
            if type(exclusions.get(key)) is int and exclusions[key] > 0
        ]
        if found:
            check["structure"] = "Yes"
            check["structure_note"] = (
                f"The checker recognized {join_labels(found)} from the HHS NOFO template."
            )
            return check
        check["structure_note"] = (
            "The checker did not recognize a NOFO template cover page, table of "
            "contents, or template instructions. This does not mean the document "
            "is not a NOFO."
        )
    else:
        check["structure_note"] = (
            "The checker does not compare a PDF’s layout or sections with the "
            "NOFO template. This does not mean the document is not a NOFO."
        )
    check["structure"] = "Couldn’t verify"
    return check


def scope_counts(source, keys):
    return {
        key: source[key]
        for key in keys
        if type(source.get(key)) is int and source[key] >= 0
    }


def checker_scope_details(payload, scope):
    details = scope_counts(payload.get("scope") or {}, SCOPE_COUNTS)
    if scope == "word":
        excluded = scope_counts(payload.get("word_exclusions") or {}, WORD_EXCLUSIONS)
        details["no_exclusions"] = len(excluded) == len(WORD_EXCLUSIONS) and not any(
            excluded.values()
        )
    else:
        details.update(
            scope_counts(payload, ("pages_analyzed", "pages_with_text", "pages_total"))
        )
    return details


def checker_report_token(request, report, *, filename="", opportunity_number=None):
    """Signed-in users get the document details the Builder report shows.

    Signed-out reports omit identifiers and explain that nothing was saved.
    """
    profile = report.get("profile")
    scope = profile if profile in {"word", "generic"} else "pdf"
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        extra = {"document": filename or "", "number": opportunity_number or ""}
    else:
        extra = {"not_saved_note": True}
    return report_token(request, report, scope=scope, salt=CHECKER_SALT, extra=extra)


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
                "details": report.get("details", {}),
                "nofo_check": report.get("nofo_check"),
                "not_saved_note": report.get("not_saved_note", False),
                "document": report.get("document", ""),
                "title": nofo.title if nofo else "",
                "number": nofo.number if nofo else report.get("number", ""),
            },
        )
        response = generate_html_docx_download_response(
            request=request, html=html, filename_base="readability-metrics"
        )
    add_never_cache_headers(response)
    return response
