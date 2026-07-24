from django.shortcuts import render

DOCUMENT_STRUCTURE_RECOVERY_STEPS = (
    "Review the document’s required metadata and heading structure.",
    "Save the document, then select it again.",
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
        },
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
