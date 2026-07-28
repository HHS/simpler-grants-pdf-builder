from django.core.exceptions import ValidationError
from django.shortcuts import render

DOCUMENT_STRUCTURE_RECOVERY_STEPS = (
    "Review the document’s required metadata and heading structure.",
    "Save the document, then select it again.",
)


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

    return render_blocking_import_error(
        request,
        title="We found text that may have the wrong heading style",
        summary=(
            "The document contains heading text that is too long. This usually "
            "means a paragraph was formatted as a heading by mistake."
        ),
        error_code="IMPORT-HEADING-TOO-LONG",
        status=422,
        error_details=[
            {"label": "Detected as", "value": detected_as},
            {
                "label": "Heading character limit",
                "value": str(error.max_length),
            },
            {
                "label": "Characters found",
                "value": str(len(error.heading_text)),
            },
            {"label": "Affected text", "value": error.heading_text},
        ],
        recovery_steps=[
            "Open the document in Word and find the affected text shown above.",
            (
                "If it is paragraph text, change its style to Normal. If it is "
                "a heading, shorten it or apply the correct heading style."
            ),
            "Save the document, then select it again.",
        ],
        retry_url=retry_url,
        retry_label=retry_label,
    )


def render_import_server_error(request, *, retry_url=None):
    """Return a sanitized 500 response for an unexpected import failure."""
    return render_blocking_import_error(
        request,
        title="We couldn’t finish importing this document",
        summary=(
            "Something went wrong in NOFO Builder. The document was not imported."
        ),
        error_code="IMPORT-UNEXPECTED",
        status=500,
        recovery_steps=[
            "Try the import again.",
            "If the problem continues, use the help options below and include the error code.",
        ],
        retry_url=retry_url,
    )
