from bloom_nofos.import_errors import (
    DOCUMENT_STRUCTURE_RECOVERY_STEPS,
    IMPORT_ERROR_CATALOG,
)
from django.core.exceptions import ValidationError
from django.shortcuts import render

__all__ = [
    "DOCUMENT_STRUCTURE_RECOVERY_STEPS",
    "AmbiguousHeadingHierarchyError",
    "MistaggedHeadingError",
    "StrictFormattingError",
    "render_blocking_import_error",
    "render_import_error",
    "render_import_server_error",
    "render_mistagged_heading_error",
]


class MistaggedHeadingError(ValidationError):
    """A heading is too long and is likely paragraph text with a heading style."""

    code = "mistagged_heading"

    def __init__(self, *, heading_kind, heading_order, heading_text, max_length):
        self.heading_kind = heading_kind
        self.heading_order = heading_order
        self.heading_text = heading_text
        self.max_length = max_length
        super().__init__(
            (
                f"{heading_kind.title()} heading {heading_order} exceeds the "
                f"{max_length}-character limit. This often means a paragraph "
                "was incorrectly styled as a heading."
            ),
            code=self.code,
        )


class StrictFormattingError(ValidationError):
    """
    Strict import mode found Word styles that aren't in our style map.

    Carries the style warnings as data so the error page can list them as
    details, rather than folding them into the message string.
    """

    code = "strict_formatting"

    def __init__(self, warnings):
        self.warnings = list(warnings)
        super().__init__(
            "These styles are not recognized by our style map: {}".format(
                "; ".join(self.warnings)
            ),
            code=self.code,
        )


class AmbiguousHeadingHierarchyError(ValidationError):
    """
    A Heading 2 appears before the document's first Heading 1, so the level
    that marks a main section can't be determined without silently dropping
    content. Carries both headings so the error page can show them.
    """

    code = "ambiguous_heading_hierarchy"

    def __init__(self, *, h2_text, h1_text):
        self.h2_text = h2_text
        self.h1_text = h1_text
        super().__init__(
            (
                "The document uses Heading 2 before its first Heading 1. "
                f'NOFO Builder would skip content beginning with Heading 2 "{h2_text}" '
                f'and start at Heading 1 "{h1_text}".'
            ),
            code=self.code,
        )


def render_blocking_import_error(
    request,
    *,
    title,
    summary,
    error_code,
    status=400,
    recovery_steps=None,
    retry_url=None,
    retry_label="Try the import again",
    error_details=None,
):
    """Render a safe, actionable error page for a blocked document import."""
    return render(
        request,
        "import_error.html",
        status=status,
        context={
            "error_title": title,
            "error_summary": summary,
            "error_code": error_code,
            "recovery_steps": recovery_steps or [],
            "retry_url": retry_url,
            "retry_label": retry_label,
            "error_details": error_details or [],
        },
    )


def render_import_error(
    request,
    error_code,
    *,
    retry_url=None,
    retry_label="Try the import again",
    error_details=None,
    summary_context=None,
):
    """
    Render the error page for a catalogued import error code.

    Copy comes from IMPORT_ERROR_CATALOG so there is one place to read and
    change it. `error_details` carries the per-failure specifics (the offending
    heading, the unrecognized styles); `summary_context` fills placeholders in
    the catalog's summary, for the rare entry that needs one.
    """
    entry = IMPORT_ERROR_CATALOG[error_code]
    summary = entry["summary"]
    if summary_context:
        summary = summary.format(**summary_context)

    return render_blocking_import_error(
        request,
        title=entry["title"],
        summary=summary,
        error_code=error_code,
        status=entry["status"],
        recovery_steps=list(entry["recovery_steps"]),
        retry_url=retry_url,
        retry_label=retry_label,
        error_details=error_details,
    )


def render_mistagged_heading_error(
    request,
    error,
    *,
    retry_url=None,
    retry_label="Try the import again",
):
    """Render a safe, specific response for a likely mistagged paragraph."""
    detected_as = f"{error.heading_kind.title()} heading"
    if error.heading_order not in (None, ""):
        detected_as = f"{detected_as} {error.heading_order}"

    return render_import_error(
        request,
        "IMPORT-HEADING-TOO-LONG",
        error_details=[
            {"label": "Detected as", "value": detected_as},
            {"label": "Heading character limit", "value": str(error.max_length)},
            {"label": "Characters found", "value": str(len(error.heading_text))},
            {"label": "Affected text", "value": error.heading_text},
        ],
        retry_url=retry_url,
        retry_label=retry_label,
    )


def render_import_server_error(request, *, retry_url=None):
    """Return a sanitized 500 response for an unexpected import failure."""
    return render_import_error(
        request,
        "IMPORT-UNEXPECTED",
        retry_url=retry_url,
    )
